#!/usr/bin/env python3
"""
Validate directory ratings against the live CQC website.

Scrapes CQC provider pages and compares ratings, inspection dates,
and key question ratings against our directory data. Reports stale
or incorrect records.

Usage:
    python3 validate_ratings.py                    # Sample 50 random active providers
    python3 validate_ratings.py --sample 200       # Sample 200
    python3 validate_ratings.py --location-id 1-4921179091  # Check specific provider
    python3 validate_ratings.py --rated-only        # Only check providers with published ratings
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os
import requests

INPUT_DIRECTORY = "directory_providers.csv"
OUTPUT_VALIDATION = "validation_report.json"
OUTPUT_VALIDATION_TXT = "validation_summary.txt"

CQC_PROFILE_URL = "https://api.service.cqc.org.uk/public/v1/locations/{location_id}"


def fetch_cqc_live(location_id: str, api_key: str | None = None, timeout: int = 15) -> dict[str, Any] | None:
    """Fetch current data from CQC public API for a specific location."""
    url = CQC_PROFILE_URL.format(location_id=location_id)
    headers = {
        "Accept": "application/json",
        "User-Agent": "CareGist-Validator/1.0",
    }
    if api_key:
        headers["Ocp-Apim-Subscription-Key"] = api_key
        headers["Subscription-Key"] = api_key
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 404:
            return {"_status": "NOT_FOUND", "locationId": location_id}
        if resp.status_code != 200:
            return {"_status": f"HTTP_{resp.status_code}", "locationId": location_id}
        return resp.json()
    except Exception as exc:
        return {"_status": f"ERROR_{type(exc).__name__}", "locationId": location_id}


def extract_live_rating(data: dict[str, Any]) -> dict[str, Any]:
    """Extract rating info from live CQC API response."""
    if data.get("_status"):
        return {
            "status": data["_status"],
            "overall_rating": None,
            "rating_safe": None,
            "rating_effective": None,
            "rating_caring": None,
            "rating_responsive": None,
            "rating_well_led": None,
            "report_date": None,
            "last_inspection_date": None,
            "registration_status": None,
            "name": None,
        }

    # Overall rating
    overall = None
    current_ratings = data.get("currentRatings", {})
    if isinstance(current_ratings, dict):
        overall_block = current_ratings.get("overall", {})
        if isinstance(overall_block, dict):
            overall = overall_block.get("rating")

    # Key question ratings
    kq = {}
    if isinstance(overall_block, dict):
        kq_list = overall_block.get("keyQuestionRatings", [])
        if isinstance(kq_list, list):
            for item in kq_list:
                if isinstance(item, dict):
                    name = str(item.get("name", "")).strip().lower().replace("-", "_").replace(" ", "_")
                    rating = str(item.get("rating", "")).strip()
                    if name and rating:
                        kq[name] = rating

    # Dates
    report_date = None
    if isinstance(current_ratings, dict):
        report_date = current_ratings.get("reportDate")
        if not report_date and isinstance(overall_block, dict):
            report_date = overall_block.get("reportDate")

    last_inspection = data.get("lastInspection", {})
    inspection_date = None
    if isinstance(last_inspection, dict):
        inspection_date = last_inspection.get("date")

    return {
        "status": "OK",
        "overall_rating": overall,
        "rating_safe": kq.get("safe"),
        "rating_effective": kq.get("effective"),
        "rating_caring": kq.get("caring"),
        "rating_responsive": kq.get("responsive"),
        "rating_well_led": kq.get("well_led"),
        "report_date": report_date,
        "last_inspection_date": inspection_date,
        "registration_status": data.get("registrationStatus"),
        "name": data.get("name"),
    }


def compare_record(directory_row: dict[str, str], live: dict[str, Any]) -> dict[str, Any]:
    """Compare a directory record against live CQC data."""
    discrepancies: list[dict[str, Any]] = []
    location_id = directory_row.get("id", "")

    if live["status"] != "OK":
        return {
            "location_id": location_id,
            "name": directory_row.get("name", ""),
            "live_status": live["status"],
            "discrepancies": [{"field": "_fetch", "issue": live["status"]}],
            "stale": True,
        }

    # Overall rating
    dir_rating = directory_row.get("overall_rating", "").strip()
    live_rating = (live["overall_rating"] or "").strip()
    rating_match = dir_rating.lower() == live_rating.lower() if (dir_rating and live_rating) else None
    if rating_match is False:
        discrepancies.append({
            "field": "overall_rating",
            "directory": dir_rating,
            "live_cqc": live_rating,
            "issue": "RATING_MISMATCH",
        })

    # Key question ratings
    for dimension in ["safe", "effective", "caring", "responsive", "well_led"]:
        dir_val = directory_row.get(f"rating_{dimension}", "").strip()
        live_val = (live.get(f"rating_{dimension}") or "").strip()
        if dir_val and live_val and dir_val.lower() != live_val.lower():
            discrepancies.append({
                "field": f"rating_{dimension}",
                "directory": dir_val,
                "live_cqc": live_val,
                "issue": "KEY_QUESTION_MISMATCH",
            })
        elif not dir_val and live_val:
            discrepancies.append({
                "field": f"rating_{dimension}",
                "directory": "(empty)",
                "live_cqc": live_val,
                "issue": "MISSING_IN_DIRECTORY",
            })

    # Inspection date (visit date in directory vs visit date from CQC)
    dir_inspection = directory_row.get("last_inspection_date", "").strip()
    live_inspection = (live["last_inspection_date"] or "").strip()
    if dir_inspection and live_inspection and dir_inspection != live_inspection:
        discrepancies.append({
            "field": "last_inspection_date",
            "directory": dir_inspection,
            "live_cqc": live_inspection,
            "issue": "INSPECTION_DATE_MISMATCH",
        })
    elif not dir_inspection and live_inspection:
        discrepancies.append({
            "field": "last_inspection_date",
            "directory": "(empty)",
            "live_cqc": live_inspection,
            "issue": "MISSING_INSPECTION_DATE",
        })

    # Registration status
    live_reg = (live["registration_status"] or "").strip()
    dir_status = directory_row.get("status", "").strip()
    if live_reg.lower() == "deregistered" and dir_status == "ACTIVE":
        discrepancies.append({
            "field": "registration_status",
            "directory": dir_status,
            "live_cqc": live_reg,
            "issue": "DEREGISTERED_BUT_ACTIVE_IN_DIRECTORY",
        })

    # Name change
    live_name = (live["name"] or "").strip()
    dir_name = directory_row.get("name", "").strip()
    if live_name and dir_name and live_name.lower() != dir_name.lower():
        discrepancies.append({
            "field": "name",
            "directory": dir_name,
            "live_cqc": live_name,
            "issue": "NAME_CHANGED",
        })

    return {
        "location_id": location_id,
        "name": dir_name,
        "live_name": live_name,
        "live_status": "OK",
        "discrepancies": discrepancies,
        "stale": len(discrepancies) > 0,
        "overall_rating_match": rating_match,
        "directory_rating": dir_rating,
        "live_rating": live_rating,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate directory ratings against live CQC data")
    parser.add_argument("--input", default=INPUT_DIRECTORY, help="Directory CSV to validate")
    parser.add_argument("--sample", type=int, default=50, help="Number of random providers to check")
    parser.add_argument("--location-id", help="Check a specific location ID")
    parser.add_argument("--rated-only", action="store_true", help="Only check providers with published ratings")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep between API calls")
    parser.add_argument("--output-json", default=OUTPUT_VALIDATION, help="Validation report JSON")
    parser.add_argument("--output-txt", default=OUTPUT_VALIDATION_TXT, help="Validation summary text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    # Load directory records
    with input_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        all_rows = list(reader)

    if args.location_id:
        rows = [r for r in all_rows if r.get("id") == args.location_id]
        if not rows:
            print(f"Location ID {args.location_id} not found in directory")
            return 1
    else:
        candidates = all_rows
        if args.rated_only:
            skip = {"unknown", "not yet inspected", ""}
            candidates = [r for r in candidates if r.get("overall_rating", "").strip().lower() not in skip]
        rows = random.sample(candidates, min(args.sample, len(candidates)))

    api_key = os.getenv("CQC_SUBSCRIPTION_KEY") or os.getenv("CQC_API_KEY")
    if not api_key:
        # Try loading from .env
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("CQC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
    if not api_key:
        print("Warning: No CQC API key found. Set CQC_API_KEY in .env or environment.")

    print(f"Validating {len(rows)} records against live CQC API...")

    results: list[dict[str, Any]] = []
    stale_count = 0
    rating_mismatches = 0
    fetch_errors = 0

    for i, row in enumerate(rows):
        location_id = row.get("id", "")
        if not location_id:
            continue

        live_data = fetch_cqc_live(location_id, api_key=api_key)
        if live_data is None:
            fetch_errors += 1
            continue

        live_info = extract_live_rating(live_data)
        comparison = compare_record(row, live_info)
        results.append(comparison)

        if comparison["stale"]:
            stale_count += 1
        if comparison.get("overall_rating_match") is False:
            rating_mismatches += 1

        if comparison["discrepancies"]:
            name = row.get("name", "")[:40]
            for d in comparison["discrepancies"]:
                print(f"  [{d['issue']}] {name}: {d['field']} = dir:{d.get('directory','')} vs cqc:{d.get('live_cqc','')}")

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(rows)} checked, {stale_count} stale so far")

        time.sleep(args.sleep)

    # Summary
    total_checked = len(results)
    fresh = total_checked - stale_count
    staleness_pct = round(stale_count / total_checked * 100, 1) if total_checked else 0

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report = {
        "generated_at": generated,
        "total_checked": total_checked,
        "fresh_count": fresh,
        "stale_count": stale_count,
        "staleness_pct": staleness_pct,
        "rating_mismatches": rating_mismatches,
        "fetch_errors": fetch_errors,
        "discrepancy_breakdown": {},
        "results": results,
    }

    # Count discrepancy types
    issue_counts: dict[str, int] = {}
    for r in results:
        for d in r.get("discrepancies", []):
            issue = d.get("issue", "UNKNOWN")
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    report["discrepancy_breakdown"] = issue_counts

    # Write JSON
    json_path = Path(args.output_json).resolve()
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)

    # Write text summary
    lines = [
        "=== CQC RATING VALIDATION REPORT ===",
        f"Generated: {generated}",
        f"Directory file: {input_path.name}",
        "",
        f"Records checked:     {total_checked}",
        f"Fresh (matching):    {fresh} ({round(fresh/total_checked*100,1) if total_checked else 0}%)",
        f"Stale (mismatched):  {stale_count} ({staleness_pct}%)",
        f"Rating mismatches:   {rating_mismatches}",
        f"Fetch errors:        {fetch_errors}",
        "",
        "DISCREPANCY BREAKDOWN:",
    ]
    for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {issue}: {count}")

    if stale_count > 0:
        lines.append("")
        lines.append("STALE RECORDS:")
        for r in results:
            if r["stale"]:
                lines.append(f"  {r['location_id']} | {r.get('name','')[:40]}")
                for d in r["discrepancies"]:
                    lines.append(f"    {d['field']}: directory=[{d.get('directory','')}] live=[{d.get('live_cqc','')}]")

    txt_path = Path(args.output_txt).resolve()
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print("")
    print("=== VALIDATION COMPLETE ===")
    print(f"Checked: {total_checked}")
    print(f"Fresh: {fresh} ({round(fresh/total_checked*100,1) if total_checked else 0}%)")
    print(f"Stale: {stale_count} ({staleness_pct}%)")
    print(f"Rating mismatches: {rating_mismatches}")
    print(f"Report: {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
