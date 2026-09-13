"""Signal-velocity analysis for CareGist Radar pilot (read-only, 2026-09-02).

Uses the verified 2026-08-04 CQC ODS edition via the SAME pipeline as the
shipped digest generator (LibreOffice headless ODS->CSV + canonical columns),
then counts, per English region and per local authority, the events that fall
in the digest 7-day window (2026-07-29 .. 2026-08-04):

  - new_registration : Location HSCA start date in window, not dormant,
                       with provider id/name (same rule as digest generator)
  - rating_published : Publication Date in window with a rating value

Output: JSON evidence artifact + printed tables. No writes to the staged
product files; no sends, no spend, no production changes.
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from generate_radar_fresh_ods_digest import (  # noqa: E402
    COL_DORMANT,
    COL_HSCA_START,
    COL_LATEST_RATING,
    COL_LOCAL_AUTHORITY,
    COL_LOCATION_ID,
    COL_LOCATION_NAME,
    COL_PROVIDER_ID,
    COL_PROVIDER_NAME,
    COL_RATING_PUBLISHED,
    COL_REGION,
    EDITION_DATE,
    _clean,
    _parse_date,
    ods_to_csv,
    parse_csv,
)

ODS = ROOT / "artifacts" / "radar-live" / "2026-08-04_HSCA_Active_Locations.ods"
WINDOW_START = EDITION_DATE - timedelta(days=6)
WINDOW_END = EDITION_DATE

ENGLISH_REGIONS = {
    "East Midlands",
    "East of England",
    "London",
    "North East",
    "North West",
    "South East",
    "South West",
    "West Midlands",
    "Yorkshire and The Humber",
}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cg-vel-") as tmp:
        csv_path = ods_to_csv(ODS, Path(tmp))
        header, data = parse_csv(csv_path)

        by_region = defaultdict(lambda: {"new_registration": 0, "rating_published": 0, "rows": 0})
        by_la = defaultdict(lambda: {"new_registration": 0, "rating_published": 0, "rows": 0, "region": ""})
        total_rows = len(data)
        non_english_rows = 0

        for row in data:
            if len(row) < COL_PROVIDER_NAME + 1:
                continue
            region = _clean(row[COL_REGION])
            la = _clean(row[COL_LOCAL_AUTHORITY])
            if not la:
                continue
            if region not in ENGLISH_REGIONS:
                non_english_rows += 1
                continue

            bucket_r = by_region[region]
            bucket_l = by_la[la]
            bucket_r["rows"] += 1
            bucket_l["rows"] += 1
            bucket_l["region"] = region

            location_id = _clean(row[COL_LOCATION_ID])
            location_name = _clean(row[COL_LOCATION_NAME])
            provider_id = _clean(row[COL_PROVIDER_ID])
            provider_name = _clean(row[COL_PROVIDER_NAME])
            dormant = _clean(row[COL_DORMANT]).upper()

            has_identity = bool(location_id and location_name and provider_id and provider_name)
            if has_identity:
                reg_date = _parse_date(row[COL_HSCA_START])
                if (
                    not dormant.startswith("Y")
                    and reg_date is not None
                    and WINDOW_START <= reg_date <= WINDOW_END
                ):
                    bucket_r["new_registration"] += 1
                    bucket_l["new_registration"] += 1

                pub_date = _parse_date(row[COL_RATING_PUBLISHED])
                rating = _clean(row[COL_LATEST_RATING])
                if pub_date is not None and WINDOW_START <= pub_date <= WINDOW_END and rating:
                    bucket_r["rating_published"] += 1
                    bucket_l["rating_published"] += 1

        # Report region table (English regions with any content first).
        region_rows = sorted(
            by_region.items(),
            key=lambda kv: (kv[1]["new_registration"] + kv[1]["rating_published"]),
            reverse=True,
        )
        print("=" * 78)
        print(f"EDITION {EDITION_DATE} WINDOW {WINDOW_START}..{WINDOW_END}")
        print(f"total rows: {total_rows:,} | non-English LA rows excluded: {non_english_rows:,}")
        print("=" * 78)
        print(f"{'Region':<24}{'Rows':>9}{'NewReg':>9}{'Ratings':>9}{'Total':>8}")
        for region, b in region_rows:
            tot = b["new_registration"] + b["rating_published"]
            print(f"{region:<24}{b['rows']:>9,}{b['new_registration']:>9,}{b['rating_published']:>9,}{tot:>8,}")

        # LA table: the 20 most content-rich LAs.
        la_rows = sorted(
            by_la.items(),
            key=lambda kv: (kv[1]["new_registration"] + kv[1]["rating_published"]),
            reverse=True,
        )
        print()
        print("TOP 20 LOCAL AUTHORITIES BY EVENT COUNT")
        print(f"{'Local Authority':<32}{'Rows':>8}{'NewReg':>8}{'Ratings':>9}{'Total':>8}")
        for la, b in la_rows[:20]:
            tot = b["new_registration"] + b["rating_published"]
            print(f"{la:<32}{b['rows']:>8,}{b['new_registration']:>8,}{b['rating_published']:>9,}{tot:>8,}")

        # Empty LAs: those with rows but zero events in window.
        empty_las = [la for la, b in la_rows if b["new_registration"] + b["rating_published"] == 0]
        with_events = [la for la, b in la_rows if b["new_registration"] + b["rating_published"] > 0]
        print()
        print(f"LAs with rows but ZERO events in window: {len(empty_las):,} of {len(la_rows):,}")
        print(f"LAs with at least one event in window: {len(with_events):,}")

        payload = {
            "edition_date": EDITION_DATE.isoformat(),
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
            "source_file": ODS.name,
            "total_rows": total_rows,
            "non_english_la_rows_excluded": non_english_rows,
            "regions": {r: b for r, b in region_rows},
            "local_authorities": {la: b for la, b in la_rows},
            "la_count_total": len(la_rows),
            "la_count_zero_events": len(empty_las),
            "la_count_with_events": len(with_events),
        }
        out = ROOT / "artifacts" / "radar-live" / "2026-09-02-signal-velocity-edition-2026-08-04.json"
        out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print()
        print(f"evidence json: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
