#!/usr/bin/env python3
"""Generate P4 competitor scans (PDF + CSV) for review. Read-only.

Refuses unless COMPETITOR_SCAN_ENABLED=true. Reads care_providers through a
READ ONLY transaction and a CQC location export from disk; makes no network
calls beyond the database.

    COMPETITOR_SCAN_ENABLED=true REPORT_DATABASE_URL=... python3 -m tools.generate_competitor_scan \\
        --export .tmp/cqc-export-20261020-final/_locations_detail.ndjson \\
        --export-retrieved 2026-10-20 --file-edition-date 2026-10-02 \\
        --scan "BS6 6BH:5:care_home" --out artifacts/report-readiness/2026-10-24/step4
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

from api.queries.competitor_scan import (
    COMPETITORS_WITHIN_RADIUS,
    ORIGIN_FROM_DIRECTORY,
    ORIGIN_FROM_POSTCODE_CACHE,
)
from api.services.competitor_scan import (
    SERVICE_TYPES,
    build_competitor_scan,
    ensure_enabled,
    render_scan_pdf,
    scan_to_csv,
    validate_inputs,
)
from tools.report_sources import iter_export, parse_day, report_database_url


async def _fetch(conn, postcode: str, radius: float, service_type: str):
    row = await conn.fetchrow(ORIGIN_FROM_POSTCODE_CACHE, postcode)
    method = "postcode_cache"
    if row is None or row["latitude"] is None:
        row = await conn.fetchrow(ORIGIN_FROM_DIRECTORY, postcode)
        method = f"centroid of {row['n']} directory location(s) at this postcode" if row and row["n"] else None
    if not method:
        raise SystemExit(f"cannot locate {postcode} without an external lookup")
    lat, lon = float(row["latitude"]), float(row["longitude"])
    pattern = SERVICE_TYPES[service_type][0]
    rows = await conn.fetch(COMPETITORS_WITHIN_RADIUS, lon, lat, radius, pattern)
    return (lat, lon), method, [dict(r) for r in rows]


async def _run(args) -> int:
    ensure_enabled()
    scans = []
    for spec in args.scan:
        pc, radius, stype = spec.split(":")
        scans.append(validate_inputs(pc, float(radius), stype))
    export_rows = list(iter_export(args.export))
    window_end = max(parse_day(r.get("registrationDate")) or parse_day("1900-01-01") for r in export_rows)
    conn = await asyncpg.connect(report_database_url())
    try:
        async with conn.transaction(readonly=True):
            read_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            fetched = [(s, *(await _fetch(conn, *s))) for s in scans]
    finally:
        await conn.close()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for (pc, radius, stype), origin, method, rows in fetched:
        scan = build_competitor_scan(
            postcode=pc, radius_km=radius, service_type=stype, origin=origin, origin_method=method,
            directory_rows=rows, export_rows=export_rows, export_window_end=window_end,
            file_edition_date=parse_day(args.file_edition_date),
            data_as_at={
                "CareGist directory read": read_at[:10],
                "CQC API location export retrieved": args.export_retrieved,
                "CQC ratings file edition": args.file_edition_date,
            },
        )
        stem = f"competitor_scan_{pc.replace(' ', '')}_{stype}_{radius:g}km"
        (args.out / f"{stem}.pdf").write_bytes(render_scan_pdf(scan))
        (args.out / f"{stem}.csv").write_text(scan_to_csv(scan))
        manifest.append({
            "postcode": pc, "radius_km": radius, "service_type": stype, "origin": origin,
            "origin_method": method, "services": len(scan.competitors), "rating_counts": scan.rating_counts,
            "registrations_12m": len(scan.movement.registrations),
            "confirmed_closures_12m": len(scan.movement.confirmed_closures),
            "other_endings_12m": scan.movement.other_endings, "files": [f"{stem}.pdf", f"{stem}.csv"],
            "directory_read_at": read_at,
        })
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", type=Path, required=True)
    ap.add_argument("--export-retrieved", required=True)
    ap.add_argument("--file-edition-date", required=True)
    ap.add_argument("--scan", action="append", required=True, help="POSTCODE:RADIUS_KM:SERVICE_TYPE")
    ap.add_argument("--out", type=Path, required=True)
    return asyncio.run(_run(ap.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
