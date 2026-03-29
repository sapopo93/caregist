#!/usr/bin/env python3
"""Run quality audit on cleaned CQC data and produce reports."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from cqc_common import normalize_whitespace

INPUT_CLEANED = "cleaned_cqc.csv"
INPUT_RAW_COMBINED = "raw_combined.csv"
INPUT_INACTIVE = "inactive_providers.csv"
INPUT_DUPLICATES = "duplicates_removed.csv"
INPUT_FAILED_IDS = "failed_ids.txt"

OUTPUT_REPORT_JSON = "quality_report.json"
OUTPUT_SUMMARY_TXT = "quality_summary.txt"

AUDIT_FIELDS = [
    "name",
    "postalCode",
    "postalAddressTownCity",
    "region",
    "localAuthority",
    "mainPhoneNumber",
    "website",
    "latitude",
    "longitude",
    "overallRating",
    "lastInspectionDate",
    "reportDate",
    "regulatedActivities",
    "serviceTypes",
    "specialisms",
    "numberOfBeds",
    "ownershipType",
    "registrationDate",
]

RATING_ORDER = ["Outstanding", "Good", "Requires Improvement", "Inadequate", "Not Yet Inspected"]


def is_populated(value: Any) -> bool:
    text = normalize_whitespace(value)
    return bool(text and text.upper() != "NULL")


def has_issue(value: Any, issue_text: str) -> bool:
    return normalize_whitespace(value) == issue_text


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        count = 0
        for line in fh:
            if line.strip() and not line.startswith("providerId"):
                count += 1
        return count


def bed_applicable(row: pd.Series) -> bool:
    haystack = " ".join(
        [
            normalize_whitespace(row.get("type", "")),
            normalize_whitespace(row.get("serviceTypes", "")),
        ]
    ).lower()
    return any(token in haystack for token in ["care home", "nursing", "residential"])


def valid_coord(row: pd.Series) -> bool:
    if has_issue(row.get("coords_issue"), "INVALID_COORDS"):
        return False
    if has_issue(row.get("coords_issue"), "MISSING_COORDS"):
        return False
    return is_populated(row.get("latitude")) and is_populated(row.get("longitude"))


def score_row(row: pd.Series) -> int:
    score = 0

    if is_populated(row.get("name")) and not is_populated(row.get("name_issue")):
        score += 10

    if is_populated(row.get("postalCode")) and not has_issue(row.get("postalCode_issue"), "INVALID_POSTCODE"):
        score += 10

    if is_populated(row.get("mainPhoneNumber")) and not has_issue(row.get("mainPhoneNumber_issue"), "INVALID_PHONE"):
        score += 8

    if is_populated(row.get("website")) and not has_issue(row.get("website_issue"), "INVALID_URL"):
        score += 7

    if valid_coord(row):
        score += 8

    if is_populated(row.get("overallRating")):
        score += 10

    if is_populated(row.get("lastInspectionDate")):
        score += 8

    if is_populated(row.get("serviceTypes")):
        score += 10

    if is_populated(row.get("specialisms")):
        score += 7

    if is_populated(row.get("regulatedActivities")):
        score += 8

    beds_present = is_populated(row.get("numberOfBeds"))
    if bed_applicable(row):
        if beds_present:
            score += 5
    else:
        score += 5

    if is_populated(row.get("localAuthority")):
        score += 5

    if is_populated(row.get("region")):
        score += 4

    return int(score)


def score_to_tier(score: int) -> str:
    """Data completeness tier — NOT a quality rating. CQC ratings are separate."""
    if score >= 85:
        return "COMPLETE"
    if score >= 60:
        return "GOOD"
    if score >= 40:
        return "PARTIAL"
    return "SPARSE"


def invalid_count_for_field(df: pd.DataFrame, field: str) -> int:
    if field == "postalCode":
        return int((df.get("postalCode_issue", "") == "INVALID_POSTCODE").sum())
    if field == "mainPhoneNumber":
        return int((df.get("mainPhoneNumber_issue", "") == "INVALID_PHONE").sum())
    if field == "website":
        return int((df.get("website_issue", "") == "INVALID_URL").sum())
    if field in ("latitude", "longitude"):
        return int((df.get("coords_issue", "") == "INVALID_COORDS").sum())
    if field in ("registrationDate", "lastInspectionDate", "reportDate"):
        return int((df.get("date_issue", "") == "SUSPECT_DATE").sum())
    if field == "name":
        return int((df.get("name_issue", "") == "INVALID_NAME_CHARS").sum())
    return 0


def pct(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100, 2)


def top_counts_to_lines(series: pd.Series, top_n: int = 10) -> list[str]:
    lines = []
    for idx, val in series.head(top_n).items():
        lines.append(f"  {idx}: {int(val)}")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quality audit for cleaned CQC data")
    parser.add_argument("--input", default=INPUT_CLEANED, help="Input cleaned CSV")
    parser.add_argument("--raw", default=INPUT_RAW_COMBINED, help="Input raw combined CSV")
    parser.add_argument("--inactive", default=INPUT_INACTIVE, help="Inactive records CSV")
    parser.add_argument("--duplicates", default=INPUT_DUPLICATES, help="Duplicates removed CSV")
    parser.add_argument("--failed-ids", default=INPUT_FAILED_IDS, help="Failed IDs/pages log")
    parser.add_argument("--report-json", default=OUTPUT_REPORT_JSON, help="Output quality report JSON")
    parser.add_argument("--summary", default=OUTPUT_SUMMARY_TXT, help="Output human-readable summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input).resolve()
    raw_path = Path(args.raw).resolve()
    inactive_path = Path(args.inactive).resolve()
    duplicates_path = Path(args.duplicates).resolve()
    failed_ids_path = Path(args.failed_ids).resolve()

    report_json_path = Path(args.report_json).resolve()
    summary_path = Path(args.summary).resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)

    total_active = len(df)
    total_records_extracted = count_lines(raw_path)
    total_inactive = count_lines(inactive_path)
    duplicates_removed = count_lines(duplicates_path)

    if total_active == 0:
        df["qualityScore"] = []
        df["qualityTier"] = []
    else:
        df["qualityScore"] = df.apply(score_row, axis=1)
        df["qualityTier"] = df["qualityScore"].apply(score_to_tier)

    # Persist scoring columns back into cleaned dataset
    df.to_csv(input_path, index=False)

    completeness: dict[str, dict[str, Any]] = {}
    for field in AUDIT_FIELDS:
        if field not in df.columns:
            df[field] = ""
        populated = int(df[field].map(is_populated).sum())
        invalid = invalid_count_for_field(df, field)
        completeness[field] = {
            "total_records": int(total_active),
            "populated": populated,
            "completeness_pct": pct(populated, total_active),
            "invalid_count": invalid,
        }

    tier_counts = {
        tier: int((df.get("qualityTier", "") == tier).sum())
        for tier in ["COMPLETE", "GOOD", "PARTIAL", "SPARSE"]
    }

    invalid_postcodes = int((df.get("postalCode_issue", "") == "INVALID_POSTCODE").sum())
    invalid_phones = int((df.get("mainPhoneNumber_issue", "") == "INVALID_PHONE").sum())
    invalid_coords = int((df.get("coords_issue", "") == "INVALID_COORDS").sum())
    invalid_urls = int((df.get("website_issue", "") == "INVALID_URL").sum())
    suspect_addresses = int((df.get("address_issue", "") == "SUSPECT_ADDRESS").sum())
    failed_api_calls = count_lines(failed_ids_path)

    ratings = df.get("overallRating", pd.Series([], dtype=str)).fillna("")
    rating_counts = ratings.value_counts()

    region_counts = (
        df.get("region", pd.Series([], dtype=str))
        .fillna("")
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
    )

    service_counts = (
        df.get("serviceTypes", pd.Series([], dtype=str))
        .fillna("")
        .str.split("|")
        .explode()
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
    )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report_payload = {
        "generated_at": generated,
        "total_records": int(total_active),
        "field_completeness": completeness,
        "quality_tiers": {
            "COMPLETE": {"count": tier_counts["COMPLETE"], "pct": pct(tier_counts["COMPLETE"], total_active)},
            "GOOD": {"count": tier_counts["GOOD"], "pct": pct(tier_counts["GOOD"], total_active)},
            "PARTIAL": {"count": tier_counts["PARTIAL"], "pct": pct(tier_counts["PARTIAL"], total_active)},
            "SPARSE": {
                "count": tier_counts["SPARSE"],
                "pct": pct(tier_counts["SPARSE"], total_active),
            },
        },
        "issues": {
            "invalid_postcodes": invalid_postcodes,
            "invalid_phones": invalid_phones,
            "invalid_coordinates": invalid_coords,
            "invalid_urls": invalid_urls,
            "suspect_addresses": suspect_addresses,
            "duplicates_removed": duplicates_removed,
            "failed_api_calls": failed_api_calls,
        },
    }

    with report_json_path.open("w", encoding="utf-8") as fh:
        json.dump(report_payload, fh, indent=2, ensure_ascii=True)

    lines: list[str] = []
    lines.append("=== CQC DIRECTORY DATA QUALITY REPORT ===")
    lines.append(f"Generated: {generated}")
    lines.append("")
    lines.append(f"TOTAL RECORDS EXTRACTED:     {total_records_extracted}")
    lines.append(f"ACTIVE (directory-ready):    {total_active}")
    lines.append(f"INACTIVE (excluded):         {total_inactive}")
    lines.append("")
    lines.append("DATA COMPLETENESS TIERS (not CQC ratings):")
    lines.append(f"  COMPLETE (85-100):         {tier_counts['COMPLETE']} ({pct(tier_counts['COMPLETE'], total_active)}%)")
    lines.append(f"  GOOD (60-84):              {tier_counts['GOOD']} ({pct(tier_counts['GOOD'], total_active)}%)")
    lines.append(f"  PARTIAL (40-59):           {tier_counts['PARTIAL']} ({pct(tier_counts['PARTIAL'], total_active)}%)")
    lines.append(
        f"  SPARSE (<40):              {tier_counts['SPARSE']} ({pct(tier_counts['SPARSE'], total_active)}%)"
    )
    lines.append("")
    lines.append("FIELD COMPLETENESS:")
    lines.append(f"  name:                      {completeness['name']['completeness_pct']}%")
    lines.append(
        f"  postcode (valid):          {round(100 - pct(invalid_postcodes, total_active), 2) if total_active else 0.0}%"
    )
    lines.append(
        f"  phone (valid):             {round(100 - pct(invalid_phones, total_active), 2) if total_active else 0.0}%"
    )
    lines.append(f"  website:                   {completeness['website']['completeness_pct']}%")
    lines.append(
        f"  coordinates (valid):       {round(100 - pct(invalid_coords, total_active), 2) if total_active else 0.0}%"
    )
    lines.append(f"  overall rating:            {completeness['overallRating']['completeness_pct']}%")
    lines.append(f"  service types:             {completeness['serviceTypes']['completeness_pct']}%")
    lines.append(f"  specialisms:               {completeness['specialisms']['completeness_pct']}%")
    lines.append("")
    lines.append("ISSUES FOUND:")
    lines.append(f"  Invalid postcodes:         {invalid_postcodes}")
    lines.append(f"  Invalid phones:            {invalid_phones}")
    lines.append(f"  Invalid coordinates:       {invalid_coords}")
    lines.append(f"  Invalid URLs:              {invalid_urls}")
    lines.append(f"  Suspect addresses:         {suspect_addresses}")
    lines.append(f"  Duplicate records removed: {duplicates_removed}")
    lines.append(f"  Failed API calls:          {failed_api_calls}")
    lines.append("")
    lines.append("RATINGS DISTRIBUTION:")

    for rating in RATING_ORDER:
        count = int(rating_counts.get(rating, 0))
        lines.append(f"  {rating}: {' ' * max(1, 26 - len(rating))}{count} ({pct(count, total_active)}%)")

    # Add any unexpected ratings to avoid silent omissions.
    for rating, count in rating_counts.items():
        if rating in RATING_ORDER or not normalize_whitespace(rating):
            continue
        lines.append(f"  {rating}: {int(count)} ({pct(int(count), total_active)}%)")

    lines.append("")
    lines.append("TOP 10 REGIONS BY PROVIDER COUNT:")
    lines.extend(top_counts_to_lines(region_counts, top_n=10) or ["  (none)"])
    lines.append("")
    lines.append("TOP 10 SERVICE TYPES:")
    lines.extend(top_counts_to_lines(service_counts, top_n=10) or ["  (none)"])
    lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")

    print("Quality audit complete")
    print(f"Records audited: {total_active}")
    print(f"COMPLETE: {tier_counts['COMPLETE']}, GOOD: {tier_counts['GOOD']}, PARTIAL: {tier_counts['PARTIAL']}, SPARSE: {tier_counts['SPARSE']}")
    print(f"Report JSON: {report_json_path}")
    print(f"Summary TXT: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
