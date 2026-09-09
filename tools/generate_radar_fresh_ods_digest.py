"""Compile the CareGist Radar fresh weekly territory digest from the public CQC register.

Source: CQC "Care directory with filters" monthly ODS
  - Official page: https://www.cqc.org.uk/about-us/transparency/using-cqc-data
  - File: 2026-08-04_HSCA_Active_Locations.ods (edition dated 04 August 2026)

Pipeline:
  1. Convert the ODS data sheet to CSV with LibreOffice headless (authoritative
     cell expansion; regex ODS parsing was found unreliable on this file).
  2. Load rows; locate the header; map canonical columns.
  3. Filter to the target local authority (default: Gloucestershire).
  4. Build events in the latest seven-day window anchored to the edition date
     (window = edition_date-6 .. edition_date):
       - new_registration: Location HSCA start date falls in the window and the
         row is not dormant and has a provider id/name.
       - rating_published: Publication Date falls in the window (the ODS carries
         the latest rating and its publication date; there is no history in this
         file, so the honest event is "rating published", not "rating changed").
  5. Write markdown digest + JSON sidecar with full provenance.

Truthfulness: the digest reflects the public CQC register edition of 04 Aug 2026.
It is NOT a live API call and must not be presented as such.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

# --------------------------------------------------------------------------- #
# Sources and destinations
# --------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ODS = ROOT / "artifacts" / "radar-live" / "2026-08-04_HSCA_Active_Locations.ods"
EDITION_DATE = date(2026, 8, 4)  # file edition date, per CQC page and filename
DEFAULT_TERRITORY = "Gloucestershire"
DEFAULT_OUT_MD = ROOT / "artifacts" / "radar-live" / "2026-08-04-fresh-weekly-digest-gloucestershire.md"
DEFAULT_OUT_JSON = ROOT / "artifacts" / "radar-live" / "2026-08-04-fresh-weekly-digest-gloucestershire.json"

CQC_DATA_PAGE = "https://www.cqc.org.uk/about-us/transparency/using-cqc-data"

# Canonical column indexes (verified against LibreOffice CSV header export).
COL_LOCATION_ID = 0
COL_HSCA_START = 1
COL_DORMANT = 2
COL_LOCATION_NAME = 4
COL_LATEST_RATING = 13
COL_RATING_PUBLISHED = 14
COL_REGION = 16
COL_LOCAL_AUTHORITY = 18
COL_POSTCODE = 27
COL_PROVIDER_ID = 37
COL_PROVIDER_NAME = 38


@dataclass
class DigestEvent:
    event_type: str
    territory: str
    local_authority: str
    region: str
    provider_id: str
    provider_name: str
    location_id: str
    location_name: str
    postcode: str
    effective_date: str  # ISO
    new_value: dict


# --------------------------------------------------------------------------- #
# ODS -> CSV conversion via LibreOffice
# --------------------------------------------------------------------------- #

def ods_to_csv(ods_path: Path, tmp_dir: Path) -> Path:
    """Convert the ODS data sheet to CSV using LibreOffice headless."""
    out = tmp_dir / "ods-csv"
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,true,false,false,-1",
        "--outdir",
        str(out),
        str(ods_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"soffice failed: {res.stderr[:500]}")
    candidates = sorted(out.glob("*.csv"), key=lambda p: p.stat().st_size, reverse=True)
    if not candidates:
        raise RuntimeError("no CSV produced")
    # The real data sheet is the largest exported CSV (43.6MB); the
    # "Dual_Registration_Locations" (142KB) and "README" (6KB) sheets must
    # never be selected in its place.
    return candidates[0]


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def parse_csv(csv_path: Path) -> tuple[list[str], list[list[str]]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise RuntimeError("empty CSV")
    header = rows[0]
    data = rows[1:]
    return header, data


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _clean(value: str | None) -> str:
    return (value or "").strip()


def build_events(data: list[list[str]], territory: str, window_start: date, window_end: date) -> tuple[list[DigestEvent], int]:
    events: list[DigestEvent] = []
    skipped = 0
    for row in data:
        if len(row) < COL_PROVIDER_NAME + 1:
            skipped += 1
            continue
        local_authority = _clean(row[COL_LOCAL_AUTHORITY])
        if local_authority.lower() != territory.lower():
            skipped += 1
            continue

        location_id = _clean(row[COL_LOCATION_ID])
        location_name = _clean(row[COL_LOCATION_NAME])
        provider_id = _clean(row[COL_PROVIDER_ID])
        provider_name = _clean(row[COL_PROVIDER_NAME])
        region = _clean(row[COL_REGION])
        postcode = _clean(row[COL_POSTCODE])
        dormant = _clean(row[COL_DORMANT]).upper()

        if not location_id or not location_name or not provider_id or not provider_name:
            skipped += 1
            continue

        reg_date = _parse_date(row[COL_HSCA_START]) if len(row) > COL_HSCA_START else None
        if (
            not dormant.startswith("Y")
            and reg_date is not None
            and window_start <= reg_date <= window_end
        ):
            events.append(
                DigestEvent(
                    event_type="new_registration",
                    territory=territory,
                    local_authority=local_authority,
                    region=region,
                    provider_id=provider_id,
                    provider_name=provider_name,
                    location_id=location_id,
                    location_name=location_name,
                    postcode=postcode,
                    effective_date=reg_date.isoformat(),
                    new_value={"registrationDate": reg_date.isoformat()},
                )
            )

        pub_date = _parse_date(row[COL_RATING_PUBLISHED]) if len(row) > COL_RATING_PUBLISHED else None
        rating = _clean(row[COL_LATEST_RATING]) if len(row) > COL_LATEST_RATING else ""
        if pub_date is not None and window_start <= pub_date <= window_end and rating:
            events.append(
                DigestEvent(
                    event_type="rating_published",
                    territory=territory,
                    local_authority=local_authority,
                    region=region,
                    provider_id=provider_id,
                    provider_name=provider_name,
                    location_id=location_id,
                    location_name=location_name,
                    postcode=postcode,
                    effective_date=pub_date.isoformat(),
                    new_value={"rating": rating, "publicationDate": pub_date.isoformat()},
                )
            )

    events.sort(
        key=lambda e: (
            e.effective_date,
            e.provider_name,
            e.location_id,
            e.event_type,
            e.location_name,
        )
    )
    return events, skipped


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def render_markdown(
    *,
    edition_date: date,
    window_start: date,
    window_end: date,
    territory: str,
    total_rows: int,
    territory_rows: int,
    events: list[DigestEvent],
    source_csv: Path,
    ods_path: Path,
) -> str:
    regs = [e for e in events if e.event_type == "new_registration"]
    ratings = [e for e in events if e.event_type == "rating_published"]

    lines: list[str] = []
    lines.append(f"# CareGist Radar: weekly digest for {territory}")
    lines.append("")
    lines.append("## Where the data comes from")
    lines.append("")
    lines.append(f"- **Source**: CQC public register, \"Care directory with filters\" monthly file.")
    lines.append(f"- **Edition date**: {edition_date.isoformat()} (file: {ods_path.name}).")
    lines.append(f"- **Official page**: {CQC_DATA_PAGE}")
    lines.append(f"- **Window**: {window_start.isoformat()} to {window_end.isoformat()} inclusive (latest seven days of the edition).")
    lines.append(f"- **Territory**: {territory} (local authority).")
    lines.append(f"- **Register size**: {total_rows:,} rows; {territory_rows:,} rows in {territory}.")
    lines.append("- **Status**: compiled from the published register edition; not a live API call.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- New registrations: **{len(regs)}**")
    lines.append(f"- Ratings published: **{len(ratings)}**")
    lines.append("")

    if regs:
        lines.append("## New registrations")
        lines.append("")
        lines.append("| Provider | Location | Postcode | Registered |")
        lines.append("|---|---|---|---|")
        for e in regs:
            lines.append(f"| {e.provider_name} | {e.location_name} | {e.postcode} | {e.effective_date} |")
        lines.append("")
    else:
        lines.append("## New registrations")
        lines.append("")
        lines.append("None in this window.")
        lines.append("")

    if ratings:
        lines.append("## Ratings published")
        lines.append("")
        lines.append("| Provider | Location | Rating | Published |")
        lines.append("|---|---|---|---|")
        for e in ratings:
            lines.append(f"| {e.provider_name} | {e.location_name} | {e.new_value.get('rating','')} | {e.effective_date} |")
        lines.append("")
    else:
        lines.append("## Ratings published")
        lines.append("")
        lines.append("None in this window.")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- The register file carries only the latest rating and its publication date, not the full history. The honest event is \"rating published\", not \"rating changed\".")
    lines.append("- Counts are exact for the parsed register file; empty or misformed rows are excluded.")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    ods_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ODS
    territory = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TERRITORY
    out_md = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUT_MD
    out_json = Path(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_OUT_JSON

    if not ods_path.exists():
        print(f"error: ODS not found: {ods_path}", file=sys.stderr)
        return 1

    window_end = EDITION_DATE
    window_start = window_end - timedelta(days=6)

    with tempfile.TemporaryDirectory(prefix="cg-ods-") as tmp:
        tmp_dir = Path(tmp)
        csv_path = ods_to_csv(ods_path, tmp_dir)
        header, data = parse_csv(csv_path)
        events, skipped = build_events(data, territory, window_start, window_end)

        territory_rows = sum(
            1
            for row in data
            if len(row) > COL_LOCAL_AUTHORITY
            and _clean(row[COL_LOCAL_AUTHORITY]).lower() == territory.lower()
        )

        md = render_markdown(
            edition_date=EDITION_DATE,
            window_start=window_start,
            window_end=window_end,
            territory=territory,
            total_rows=len(data),
            territory_rows=territory_rows,
            events=events,
            source_csv=csv_path,
            ods_path=ods_path,
        )
        out_md.write_text(md, encoding="utf-8")

        payload = {
            "provenance": {
                "source_page": CQC_DATA_PAGE,
                "source_file": ods_path.name,
                "edition_date": EDITION_DATE.isoformat(),
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "territory": territory,
                "conversion": "LibreOffice headless ODS->CSV",
                "parsed_rows": len(data),
                "territory_rows": territory_rows,
                "skipped_rows": skipped,
            },
            "events": [asdict(e) for e in events],
        }
        out_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(
        f"OK territory={territory} window={window_start}..{window_end} "
        f"rows={len(data)} territory_rows={territory_rows} "
        f"new_registration={sum(1 for e in events if e.event_type=='new_registration')} "
        f"rating_published={sum(1 for e in events if e.event_type=='rating_published')} "
        f"skipped={skipped}"
    )
    print(f"md  : {out_md}")
    print(f"json: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
