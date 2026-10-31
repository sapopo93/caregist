"""Build one Weekly Digest pilot issue (GBP 150, four issues) for an agreed region.

Business Terms v2.2: each digest reports new registrations and newly published
ratings in the agreed England region, taken from CQC's published register, with
the source edition date and the observation window stated. Delivered by email
and PDF.

Sources, kept separate and named in every output:
  - New registrations: production ``trusted_event_ledger`` (read-only), the same
    evidence the new-registration feed serves.
  - Newly published ratings: a CQC API location-detail export
    (``extract_cqc.py`` -> ``_locations_detail.ndjson``). A location counts when
    its current overall rating's report date falls in the window. The export is
    the authoritative publication date; the database records changes, not
    publication dates. CQC published very few ratings from September 2026, so
    this section is often empty.

The export must have been retrieved on or after the window's last day, or the
ratings section could silently miss publications; the tool refuses that case.

Usage:
  DATABASE_URL=... .venv/bin/python -m tools.build_weekly_digest_pilot \\
    --region "North West" --week-ending 2026-10-19 --issue 1 \\
    --customer "Buyer Ltd" \\
    --locations-source .tmp/cqc-export-20261020/_locations_detail.ndjson \\
    --source-retrieved-at 2026-10-20T07:30:00+00:00 \\
    --out-dir .tmp/digests/buyer-ltd
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from api.services.pdf_writer import PdfBuilder

REGIONS = (
    "East",
    "East Midlands",
    "London",
    "North East",
    "North West",
    "South East",
    "South West",
    "West Midlands",
    "Yorkshire & Humberside",
)
WINDOW_DAYS = 7

_NEW_REGISTRATIONS_SQL = """
SELECT
  cp.id AS location_id,
  cp.name,
  cp.town,
  cp.postcode,
  cp.local_authority,
  cp.service_types,
  tel.effective_date,
  tel.observed_at
FROM trusted_event_ledger tel
JOIN care_providers cp ON cp.id = COALESCE(tel.location_id, tel.entity_id)
WHERE tel.event_type = 'new_registration'
  AND cp.region = $1
  AND tel.effective_date BETWEEN $2 AND $3
ORDER BY tel.effective_date, cp.name
"""

_EDITION_SQL = """
SELECT source_uri, source_published_at, reconciled_at
FROM pipeline_runs
WHERE run_type = 'reconciliation' AND status = 'completed' AND counts_reconciled = TRUE
ORDER BY source_retrieved_at DESC
LIMIT 1
"""


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    @classmethod
    def ending(cls, end: date) -> "Window":
        return cls(start=end - timedelta(days=WINDOW_DAYS - 1), end=end)

    def contains(self, value: date | None) -> bool:
        return value is not None and self.start <= value <= self.end


def _parse_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def select_published_ratings(
    rows: Iterable[dict[str, Any]], *, region: str, window: Window
) -> list[dict[str, Any]]:
    """Registered locations in ``region`` whose current overall rating was
    published inside ``window``. Mirrors territory_brief._current_rating_evidence."""
    selected = []
    for row in rows:
        if row.get("region") != region or row.get("registrationStatus") != "Registered":
            continue
        current = row.get("currentRatings")
        overall = current.get("overall") if isinstance(current, dict) else None
        if not isinstance(overall, dict) or not overall.get("rating"):
            continue
        published = _parse_date(
            current.get("reportDate") or overall.get("reportDate") or overall.get("date")
        )
        if not window.contains(published):
            continue
        selected.append(
            {
                "location_id": row.get("locationId"),
                "name": row.get("name"),
                "local_authority": row.get("localAuthority"),
                "rating": overall.get("rating"),
                "published": published.isoformat(),
                "cqc_url": f"https://www.cqc.org.uk/location/{row.get('locationId')}",
            }
        )
    return sorted(selected, key=lambda item: (item["published"], item["name"] or ""))


def load_ndjson(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_registration_endings(rows, *, region: str, window: Window):
    """Report dated endings, preserving succession/dormancy uncertainty."""
    from api.services.registration_endings import EndingIndex, classify_ending

    rows = list(rows)
    index = EndingIndex.build(rows)
    selected = []
    for row in rows:
        if row.get("region") != region:
            continue
        ending = classify_ending(row, index)
        if not ending or not window.contains(ending.end_date):
            continue
        selected.append({
            "location_id": str(row["locationId"]), "name": row.get("name") or "",
            "local_authority": row.get("localAuthority") or "", "date": ending.end_date.isoformat(),
            "classification": "closure_candidate" if ending.ending_class == "confirmed_closure" else ending.ending_class,
            "detail": ending.reason + (" in the supplied snapshot; business closure not confirmed" if ending.ending_class == "confirmed_closure" else ""),
            "cqc_url": f"https://www.cqc.org.uk/location/{row['locationId']}",
        })
    return sorted(selected, key=lambda r: (r["date"], r["location_id"]))


def digest_csv_bytes(registrations, ratings, endings=()) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["section", "date", "location_id", "name", "local_authority", "detail", "cqc_url"])
    for row in registrations:
        writer.writerow(["new_registration", row["effective_date"], row["location_id"], row["name"],
                         row["local_authority"], row["service_types"],
                         f"https://www.cqc.org.uk/location/{row['location_id']}"])
    for row in ratings:
        writer.writerow(["rating_published", row["published"], row["location_id"], row["name"],
                         row["local_authority"], row["rating"], row["cqc_url"]])
    for row in endings:
        writer.writerow(["registration_ended", row["date"], row["location_id"], row["name"],
                         row["local_authority"], f"{row['classification']}: {row['detail']}", row["cqc_url"]])
    return output.getvalue().encode("utf-8")


def render_pdf(
    *,
    region: str,
    window: Window,
    issue: int,
    customer: str,
    registrations: list[dict[str, Any]],
    ratings: list[dict[str, Any]],
    edition: dict[str, Any],
    ratings_source_retrieved_at: str,
    endings: list[dict[str, Any]] | None = None,
    binding: dict[str, Any] | None = None,
    registrations_checked: bool = True,
) -> bytes:
    pdf = PdfBuilder(
        title=f"CareGist Weekly Digest - {region}",
        footer="CareGist Weekly Digest pilot. Source: CQC published register. Not a live feed.",
    )
    pdf.title_block(
        f"{region} - issue {issue} of 4",
        [
            f"Prepared for {customer}",
            f"Observation window: {window.start:%d %B %Y} to {window.end:%d %B %Y}",
            f"CQC directory edition: {edition.get('source_published_at') or 'not recorded'}",
            f"Ratings source retrieved: {ratings_source_retrieved_at}",
            *([f"Order: {binding['order_reference']}",
               f"Digest content SHA-256: {binding['sha256']}"] if binding else []),
        ],
    )
    pdf.heading(f"New registrations ({len(registrations)})" if registrations_checked else "New registrations - not checked")
    if not registrations_checked:
        pdf.paragraph("The registration ledger was not queried for this preview. No registration count or completeness claim is made.")
    elif registrations:
        pdf.table(
            ["Registered", "Name", "Local authority", "Service types"],
            [
                [
                    str(row["effective_date"]),
                    str(row["name"] or ""),
                    str(row["local_authority"] or ""),
                    str(row["service_types"] or ""),
                ]
                for row in registrations
            ],
        )
    else:
        pdf.paragraph("No in-window new registrations were found in the queried ledger for this region.")
    pdf.heading(f"Newly published ratings ({len(ratings)})")
    if ratings:
        pdf.table(
            ["Published", "Name", "Local authority", "Overall rating"],
            [[r["published"], str(r["name"] or ""), str(r["local_authority"] or ""), r["rating"]] for r in ratings],
        )
    else:
        pdf.paragraph("No in-window overall rating publication was found in the supplied CQC snapshot. This is not a complete publication-history search.")
    pdf.heading(f"Registration endings ({len(endings or [])})")
    if endings:
        pdf.table(["Date", "Name", "Classification", "Evidence"], [
            [r["date"], r["name"], r["classification"].replace("_", " "), r["detail"]] for r in endings
        ])
    else:
        pdf.paragraph("No dated registration endings were found for this region in the supplied snapshot.")
    pdf.heading("How to read this digest", level=2)
    pdf.bullets(
        [
            "Each item comes from CQC's published register; the CSV gives the CQC link for every location.",
            "Dates are the CQC registration date and the CQC report publication date.",
            "This digest does not state or imply vacancies, budgets or buying intent.",
            "A registration ending is not proof that a business closed. Successor links, ownership changes, moves and dormancy are distinguished where the supplied records support them. Closure classifications remain bounded to this snapshot; verify the linked CQC record before acting.",
        ]
    )
    # The same canonical event rows appear in the CSV and the source appendix.
    # Packaging validates these labelled blocks, not just a caller-supplied hash.
    if binding:
        csv_bytes = digest_csv_bytes(registrations, ratings, endings or [])
        if hashlib.sha256(csv_bytes).hexdigest() != binding["csv_sha256"]:
            raise ValueError("Digest renderer inputs differ from the bound CSV")
        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
        events = list(reader)
        if events:
            pdf.page_break()
            pdf.heading("Official-source event register")
        for event in events:
            pdf.heading(f"Event ID: {event['section']}|{event['location_id']}|{event['date']}", level=2)
            for label, field in (("Name", "name"), ("Local authority", "local_authority"),
                                 ("Date", "date"), ("Detail", "detail"), ("CQC source", "cqc_url")):
                pdf.paragraph(f"{label}: {event[field]}")
    return pdf.build()


async def fetch_from_database(database_url: str, region: str, window: Window):
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction(readonly=True):
            registrations = [dict(r) for r in await conn.fetch(_NEW_REGISTRATIONS_SQL, region, window.start, window.end)]
            edition_row = await conn.fetchrow(_EDITION_SQL)
    finally:
        await conn.close()
    edition = dict(edition_row) if edition_row else {}
    return registrations, edition


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--region", required=True, choices=REGIONS)
    p.add_argument("--week-ending", required=True, type=date.fromisoformat)
    p.add_argument("--issue", required=True, type=int, choices=(1, 2, 3, 4))
    p.add_argument("--customer", required=True)
    p.add_argument("--order-ref")
    p.add_argument("--customer-reference")
    p.add_argument("--locations-source", required=True, type=Path)
    p.add_argument("--source-retrieved-at", required=True, help="ISO timestamp from the extract run")
    p.add_argument("--out-dir", required=True, type=Path)
    return p.parse_args(argv)


def main(argv: list[str] | None = None, *, database_url: str | None = None) -> int:
    args = parse_args(argv)
    database_url = database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is required.", file=sys.stderr)
        return 2
    window = Window.ending(args.week_ending)
    retrieved = datetime.fromisoformat(args.source_retrieved_at)
    if retrieved.tzinfo is None:
        print("ERROR: --source-retrieved-at must include a timezone.", file=sys.stderr)
        return 2
    if retrieved.astimezone(timezone.utc).date() <= window.end:
        print(
            "ERROR: the ratings export was retrieved on or before the window's last day, "
            "so it could miss publications. Re-run extract_cqc.py first.",
            file=sys.stderr,
        )
        return 2
    if not args.locations_source.exists():
        print(f"ERROR: {args.locations_source} not found.", file=sys.stderr)
        return 2

    source_rows = list(load_ndjson(args.locations_source))
    ratings = select_published_ratings(source_rows, region=args.region, window=window)
    endings = select_registration_endings(source_rows, region=args.region, window=window)
    registrations, edition = asyncio.run(fetch_from_database(database_url, args.region, window))
    csv_bytes = digest_csv_bytes(registrations, ratings, endings)
    from api.services.customer_package import digest_binding
    binding = digest_binding(
        order_reference=args.order_ref or "UNBOUND-PREVIEW",
        customer_reference=args.customer_reference or "UNBOUND-PREVIEW",
        region=args.region, issue=args.issue, week_ending=window.end.isoformat(), csv_bytes=csv_bytes,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"weekly-digest-{args.region.lower().replace(' & ', '-').replace(' ', '-')}-{window.end.isoformat()}-issue{args.issue}"
    pdf_path = args.out_dir / f"{stem}.pdf"
    csv_path = args.out_dir / f"{stem}.csv"
    manifest_path = args.out_dir / f"{stem}.manifest.json"

    pdf_path.write_bytes(
        render_pdf(
            region=args.region,
            window=window,
            issue=args.issue,
            customer=args.customer,
            registrations=registrations,
            ratings=ratings,
            edition=edition,
            ratings_source_retrieved_at=args.source_retrieved_at,
            endings=endings,
            binding=binding,
        )
    )
    csv_path.write_bytes(csv_bytes)
    manifest = {
        "product": "weekly_digest_pilot",
        "region": args.region,
        "issue": args.issue,
        "customer": args.customer,
        "window": {"start": window.start.isoformat(), "end": window.end.isoformat()},
        "binding": binding,
        "counts": {"new_registrations": len(registrations), "ratings_published": len(ratings), "registration_endings": len(endings)},
        "sources": {
            "new_registrations": "trusted_event_ledger (production, read-only)",
            "directory_edition": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in edition.items()},
            "ratings": {
                "file": str(args.locations_source),
                "sha256": sha256_file(args.locations_source),
                "retrieved_at": args.source_retrieved_at,
            },
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"pdf": str(pdf_path), "csv": str(csv_path), "manifest": str(manifest_path), **manifest["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
