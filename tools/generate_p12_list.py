#!/usr/bin/env python3
"""Generate the P12 list for one region and reconcile it to SQL. Read-only.

Refuses unless P12_LIST_ENABLED=true. Well-led evidence comes from a CQC
location export (keyQuestionRatings) and CQC's ratings file (Well-led rows).

    P12_LIST_ENABLED=true REPORT_DATABASE_URL=... python3 -m tools.generate_p12_list \\
        --region "North West" \\
        --export .tmp/cqc-export-20261020-final/_locations_detail.ndjson \\
        --ratings-ods artifacts/rating-audit/2026-10-22/source/ratings.ods \\
        --file-edition-date 2026-10-02 --out artifacts/report-readiness/2026-10-24/step5
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

from api.queries.p12_list import P12_BASE_COUNTS_BY_REGION, P12_BASE_POPULATION
from api.services.p12_list import (
    DOMAIN,
    FileDomainRating,
    build_p12_list,
    ensure_enabled,
    p12_to_csv,
)
from tools.report_sources import (
    export_current_rating,
    iter_export,
    load_ratings_file,
    parse_day,
    report_database_url,
    sha256_file,
)


async def _read(region: str):
    conn = await asyncpg.connect(report_database_url())
    try:
        async with conn.transaction(readonly=True):
            read_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            base = [dict(r) for r in await conn.fetch(P12_BASE_POPULATION, region)]
            counts = [dict(r) for r in await conn.fetch(P12_BASE_COUNTS_BY_REGION)]
    finally:
        await conn.close()
    return read_at, base, counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", required=True)
    ap.add_argument("--export", type=Path, required=True)
    ap.add_argument("--ratings-ods", type=Path, required=True)
    ap.add_argument("--file-edition-date", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    ensure_enabled()

    read_at, base, counts = asyncio.run(_read(args.region))
    ids = {r["id"] for r in base}
    api = {}
    for row in iter_export(args.export):
        if row.get("locationId") in ids:
            api[row["locationId"]] = export_current_rating(row, DOMAIN)
    file_ratings, ambiguous = load_ratings_file(args.ratings_ods, (DOMAIN,))
    file_well_led = {
        lid: FileDomainRating(v[DOMAIN].rating, v[DOMAIN].publication_date, v[DOMAIN].inherited)
        for lid, v in file_ratings.items() if lid in ids and DOMAIN in v
    }
    sha = sha256_file(args.ratings_ods)
    result = build_p12_list(
        region=args.region, base_rows=base, api_well_led=api, file_well_led=file_well_led,
        file_edition_date=parse_day(args.file_edition_date), file_sha256=sha,
    )
    sql_base = next((c for c in counts if c["region"] == args.region), None)
    reconciliation = {
        "region": args.region,
        "directory_read_at": read_at,
        "sql_base_count": sql_base["base_count"] if sql_base else 0,
        "sql_stored_well_led_below_good": sql_base["stored_well_led_below_good"] if sql_base else 0,
        "list_rows": len(result.rows),
        "buckets": result.reconciliation,
        "bucket_total": sum(result.reconciliation.values()),
        "reconciles": sum(result.reconciliation.values()) == (sql_base["base_count"] if sql_base else 0)
        and result.reconciliation.get("listed", 0) == len(result.rows),
        "base_with_api_well_led": sum(1 for v in api.values() if v[0]),
        "base_with_file_well_led": len(file_well_led),
        "ratings_file_ambiguous_well_led_skipped": sum(1 for lid, d in ambiguous if lid in ids),
        "ratings_file_sha256": sha,
        "ratings_file_edition_date": args.file_edition_date,
        "cqc_export": str(args.export),
        "sql_base_counts_all_regions": counts,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    stem = "p12_" + args.region.lower().replace(" ", "_").replace("&", "and")
    (args.out / f"{stem}.csv").write_text(p12_to_csv(result))
    (args.out / f"{stem}_reconciliation.json").write_text(json.dumps(reconciliation, indent=1, default=str))
    print(json.dumps({k: v for k, v in reconciliation.items() if k != "sql_base_counts_all_regions"}, indent=1, default=str))
    return 0 if reconciliation["reconciles"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
