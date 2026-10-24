#!/usr/bin/env python3
"""Stratified accuracy sample: CareGist ratings/status vs CQC (read-only).

Draws 100 ACTIVE CareGist locations across six strata and compares CareGist's
served rating, rating date and status with CQC's API (a full location-detail
export) and CQC's published ratings file. Writes a per-location CSV plus a
summary of discrepancies and root causes.

Strata (each location is assigned to the first that applies, in this order):
  conflict_2026_10_22  the seven exception IDs from artifacts/rating-audit/2026-10-22
  deregistration       CareGist ACTIVE, CQC export says Deregistered
  downgrade            CQC's two latest published overall ratings step down
  re_registration      CQC links an HSCA predecessor location
  file_only            CareGist API rating blank, ratings file has one
  unrated              no published rating on either channel

Selection is seeded (md5 of seed + id) and frozen before any comparison.
No network calls, no writes:

    DATABASE_URL=... python3 -m tools.rating_accuracy_sample \\
        --export .tmp/cqc-export-20261020-final/_locations_detail.ndjson \\
        --ratings-ods artifacts/rating-audit/2026-10-22/source/ratings.ods \\
        --out artifacts/report-readiness/2026-10-24/step1a
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from api.services.rating_resolver import (
    SOURCE_API,
    SOURCE_FILE,
    RatingEvidence,
    canonical_rating,
    resolve_rating,
)
from tools.generate_radar_territory_sample import _rating_sequence
from tools.report_sources import (
    export_current_rating,
    iter_export,
    load_ratings_file,
    parse_day,
    readonly_connection,
    sha256_file,
)

CONFLICT_IDS_2026_10_22 = (
    "1-152721284", "1-19886383752", "1-22160036426", "1-390976877", "1-552527797",
    "1-16491295796", "1-125730630",
)
STRATA = ("conflict_2026_10_22", "deregistration", "downgrade", "re_registration", "file_only", "unrated")
ALLOCATION = {"deregistration": 19, "downgrade": 19, "re_registration": 19, "file_only": 18, "unrated": 18}
SAMPLE_SIZE = 100
_RANK = {"Inadequate": 1, "Requires improvement": 2, "Good": 3, "Outstanding": 4}

DB_SQL = """
SELECT id, name, status, registration_date, overall_rating, last_published_rating_date,
       file_overall_rating, file_overall_rating_date, file_rating_source_sha256, updated_at
FROM care_providers
WHERE UPPER(status) = 'ACTIVE'
"""
QUARANTINE_SQL = (
    "SELECT location_id FROM reconciliation_quarantined_locations WHERE resolved_at IS NULL"
)


def _order_key(seed: str, location_id: str) -> tuple[str, str]:
    return hashlib.md5(f"{seed}:{location_id}".encode()).hexdigest(), location_id


def _export_facts(row: dict) -> dict:
    rating, report_date = export_current_rating(row)
    published = [(d, canonical_rating(r)) for d, r in _rating_sequence(row) if canonical_rating(r)]
    downgrade = len(published) >= 2 and _RANK[published[-1][1]] < _RANK[published[-2][1]]
    predecessors = [
        r.get("relatedLocationId") for r in row.get("relationships") or []
        if r.get("type") == "HSCA Predecessor"
    ]
    return {
        "status": row.get("registrationStatus"),
        "deregistration_date": row.get("deregistrationDate"),
        "dormancy": row.get("dormancy"),
        "rating_raw": rating,
        "rating": canonical_rating(rating),
        "report_date": report_date,
        "registration_date": parse_day(row.get("registrationDate")),
        "downgrade": downgrade,
        "previous_rating": published[-2][1] if len(published) >= 2 else None,
        "predecessors": [p for p in predecessors if p],
    }


def assign_stratum(db: dict, exp: dict | None, file_overall) -> str | None:
    if db["id"] in CONFLICT_IDS_2026_10_22:
        return "conflict_2026_10_22"
    if exp is None:
        return None
    if exp["status"] == "Deregistered":
        return "deregistration"
    if exp["downgrade"]:
        return "downgrade"
    if exp["predecessors"]:
        return "re_registration"
    api = canonical_rating(db["overall_rating"])
    if not api and (db["file_overall_rating"] or file_overall):
        return "file_only"
    if not api and not db["file_overall_rating"] and not file_overall and not exp["rating"]:
        return "unrated"
    return None


def select_sample(pools: dict[str, list[str]], seed: str) -> dict[str, list[str]]:
    chosen = {"conflict_2026_10_22": sorted(pools.get("conflict_2026_10_22", []))}
    for stratum, n in ALLOCATION.items():
        ordered = sorted(pools.get(stratum, []), key=lambda i: _order_key(seed, i))
        chosen[stratum] = ordered[:n]
    return chosen


def compare(db: dict, exp: dict | None, file_r, quarantined: set[str], file_edition: date | None) -> dict:
    cg_api = canonical_rating(db["overall_rating"])
    cg_date = db["last_published_rating_date"]
    cqc_rating = exp["rating"] if exp else None
    cqc_date = exp["report_date"] if exp else None
    status_match = bool(exp) and exp["status"] == "Registered"
    rating_match = cg_api == cqc_rating
    date_match = (cg_date == cqc_date) if (cg_api or cqc_rating) else True

    # Resolved rating from CareGist's stored evidence vs from CQC's evidence.
    cg_ev = [RatingEvidence(source=SOURCE_API, value=cg_api, publication_date=cg_date, raw_value=db["overall_rating"])]
    if db["file_overall_rating"]:
        cg_ev.append(RatingEvidence(source=SOURCE_FILE, value=canonical_rating(db["file_overall_rating"]),
                                    publication_date=db["file_overall_rating_date"],
                                    inherited_flag=file_r.inherited if file_r else None,
                                    source_sha256=db["file_rating_source_sha256"], edition_date=file_edition))
    cqc_ev = [RatingEvidence(source=SOURCE_API, value=cqc_rating, publication_date=cqc_date)]
    if file_r:
        cqc_ev.append(RatingEvidence(source=SOURCE_FILE, value=file_r.rating, publication_date=file_r.publication_date,
                                     inherited_flag=file_r.inherited, edition_date=file_edition))
    reg = db["registration_date"]
    cg_resolved = resolve_rating(cg_ev, registration_date=reg)
    cqc_resolved = resolve_rating(cqc_ev, registration_date=exp["registration_date"] if exp else reg)
    served = cg_api or canonical_rating(db["file_overall_rating"])  # deployed API-first/file-fallback

    causes: list[tuple[str, str]] = []
    if exp is None:
        causes.append(("not_in_cqc_export", "location absent from the CQC export"))
    elif not status_match:
        if db["id"] in quarantined:
            causes.append(("status_quarantined", "CQC deregistered; CareGist keeps ACTIVE under operator quarantine"))
        else:
            causes.append((
                "status_deregistration_unreconciled",
                f"CQC deregistered {exp['deregistration_date'] or '(no date)'}; CareGist still ACTIVE",
            ))
    if exp is not None and not rating_match and (cg_api or cqc_rating):
        if cqc_date and cg_date and cqc_date > cg_date:
            causes.append(("rating_export_newer", "CQC export carries a newer report than CareGist's stored API value"))
        elif cqc_date and cg_date and cg_date > cqc_date:
            causes.append(("rating_caregist_newer", "CareGist stored value newer than the export (updated after export)"))
        elif not cg_api:
            causes.append(("rating_caregist_blank", "CQC export has a rating CareGist stores blank"))
        elif not cqc_rating:
            causes.append(("rating_export_none", f"CareGist keeps {cg_api}; export publishes {exp['rating_raw'] or 'none'}"))
        else:
            causes.append(("rating_differs_same_report", "values differ on the same or an undated report"))
    elif exp is not None and not date_match:
        causes.append(("date_differs", "same rating, different report date"))
    if file_r and cg_api and file_r.rating != cg_api and file_r.publication_date and cg_date \
            and file_r.publication_date > cg_date:
        causes.append(("precedence_api_over_newer_file", "older API value displayed over a newer ratings-file value"))
    if served and cqc_resolved.displayable and served != cqc_resolved.value:
        causes.append(("served_differs_from_resolved", f"served {served}; resolved CQC rating {cqc_resolved.value}"))
    if served and cqc_resolved.status == "unresolved":
        causes.append(("served_value_unresolved", f"served {served}; CQC evidence conflicts (resolver: unresolved)"))
    if cg_resolved.status != cqc_resolved.status or cg_resolved.value != cqc_resolved.value:
        causes.append(("resolver_disagrees", "CareGist evidence and CQC evidence resolve differently"))

    return {
        "caregist_status": db["status"],
        "caregist_api_rating": cg_api or "",
        "caregist_api_rating_date": cg_date.isoformat() if cg_date else "",
        "caregist_file_rating": db["file_overall_rating"] or "",
        "caregist_file_rating_date": db["file_overall_rating_date"].isoformat() if db["file_overall_rating_date"] else "",
        "caregist_served_rating": served or "",
        "cqc_status": exp["status"] if exp else "",
        "cqc_deregistration_date": (exp or {}).get("deregistration_date") or "",
        "cqc_dormancy": (exp or {}).get("dormancy") or "",
        "cqc_api_rating": (exp["rating_raw"] or "") if exp else "",
        "cqc_api_rating_date": cqc_date.isoformat() if cqc_date else "",
        "cqc_file_rating": file_r.rating if file_r else "",
        "cqc_file_rating_date": file_r.publication_date.isoformat() if file_r and file_r.publication_date else "",
        "cqc_file_inherited": "" if not file_r or file_r.inherited is None else ("Y" if file_r.inherited else "N"),
        "caregist_resolved_status": cg_resolved.status,
        "caregist_resolved_rating": cg_resolved.value if cg_resolved.displayable else "",
        "cqc_resolved_status": cqc_resolved.status,
        "cqc_resolved_rating": cqc_resolved.value if cqc_resolved.displayable else "",
        "status_match": status_match,
        "rating_match": rating_match,
        "date_match": date_match,
        "discrepancy": bool(causes),
        "root_cause_codes": " ".join(code for code, _ in causes),
        "root_causes": " | ".join(detail for _, detail in causes),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", type=Path, required=True)
    ap.add_argument("--ratings-ods", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", default="caregist-report-readiness-2026-10-24")
    ap.add_argument("--file-edition-date", default="2026-10-02")
    args = ap.parse_args(argv)
    file_edition = parse_day(args.file_edition_date)
    args.out.mkdir(parents=True, exist_ok=True)

    conn = readonly_connection()
    with conn.cursor() as cur:
        cur.execute(DB_SQL)
        cols = [c.name for c in cur.description]
        db_rows = {r[0]: dict(zip(cols, r, strict=True)) for r in cur.fetchall()}
        cur.execute(QUARANTINE_SQL)
        quarantined = {r[0] for r in cur.fetchall()}
    snapshot_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    exports = {}
    for row in iter_export(args.export):
        lid = row.get("locationId")
        if lid in db_rows:
            exports[lid] = _export_facts(row)
    file_ratings, ambiguous = load_ratings_file(args.ratings_ods, ("Overall",))

    pools: dict[str, list[str]] = {s: [] for s in STRATA}
    for lid, db in db_rows.items():
        stratum = assign_stratum(db, exports.get(lid), (file_ratings.get(lid) or {}).get("Overall"))
        if stratum:
            pools[stratum].append(lid)
    chosen = select_sample(pools, args.seed)
    (args.out / "sample.json").write_text(json.dumps(
        {"seed": args.seed, "pool_sizes": {k: len(v) for k, v in pools.items()}, "sample": chosen},
        indent=1, sort_keys=True))

    out_rows = []
    for stratum in STRATA:
        for lid in chosen[stratum]:
            db = db_rows[lid]
            file_r = (file_ratings.get(lid) or {}).get("Overall")
            result = compare(db, exports.get(lid), file_r, quarantined, file_edition)
            out_rows.append({"location_id": lid, "name": db["name"], "stratum": stratum,
                             "cqc_url": f"https://www.cqc.org.uk/location/{lid}", **result})

    with (args.out / "accuracy_sample.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    by_stratum = {}
    for s in STRATA:
        rows = [r for r in out_rows if r["stratum"] == s]
        by_stratum[s] = {
            "n": len(rows),
            "pool": len(pools[s]),
            "status_match": sum(r["status_match"] for r in rows),
            "rating_match": sum(r["rating_match"] for r in rows),
            "date_match": sum(r["date_match"] for r in rows),
            "with_discrepancy": sum(r["discrepancy"] for r in rows),
        }
    cause_counts = Counter(code for r in out_rows for code in r["root_cause_codes"].split())
    summary = {
        "generated_at": snapshot_at,
        "database_snapshot_read_at": snapshot_at,
        "cqc_export": str(args.export),
        "cqc_export_sha256": sha256_file(args.export),
        "ratings_file": str(args.ratings_ods),
        "ratings_file_sha256": sha256_file(args.ratings_ods),
        "ratings_file_edition_date": args.file_edition_date,
        "ratings_file_ambiguous_skipped": len(ambiguous),
        "sample_size": len(out_rows),
        "by_stratum": by_stratum,
        "root_cause_counts": dict(cause_counts.most_common()),
        "totals": {
            "status_match": sum(r["status_match"] for r in out_rows),
            "rating_match": sum(r["rating_match"] for r in out_rows),
            "date_match": sum(r["date_match"] for r in out_rows),
            "with_discrepancy": sum(r["discrepancy"] for r in out_rows),
            "served_differs_from_resolved_cqc": cause_counts["served_differs_from_resolved"],
            "served_value_unresolved": cause_counts["served_value_unresolved"],
        },
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str))
    print(json.dumps(summary["totals"]), json.dumps(by_stratum))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
