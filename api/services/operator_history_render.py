"""CSV and PDF deliverables for a paid Operator History.

Both files are drawn from the record that was pinned to the order at checkout
(``operator_history.build_operator_history``). Every sentence is a fixed template
over values quoted from CQC or from CareGist's own observation records, counts
and dates. No model writes any text, and nothing here scores, ranks, predicts or
judges an operator.

Both files carry the title, the CQC Provider ID, the legal name as held, the CQC
edition date and its SHA-256 values, the record's ``content_sha256``, the fixed
limits text and a statement that the record is fixed at the time it was built.
The output is deterministic: the same record and build date give the same bytes.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from api.services.operator_history import STATUS_LABELS, format_date
from api.services.pdf_writer import PdfBuilder

TITLE = "Operator History"
CSV_CONTENT_TYPE = "text/csv; charset=utf-8"
PDF_CONTENT_TYPE = "application/pdf"

# Fixed customer-facing text, apart from the limits (those are the stage 1 templates).
PINNED_NOTICE = (
    "This record was built on {built_on} from the CQC edition retrieved on {retrieved_on} "
    "and is fixed at that point. A later CQC edition does not change it."
)
HASH_NOTICE = (
    "The content SHA-256 identifies exactly what was built. It is the SHA-256 of the "
    "record's canonical JSON form, without the hash itself."
)
SOURCE_NOTICE = (
    "CareGist is independent of the Care Quality Commission. This record is compiled from "
    "CQC's published data and from CareGist's own observations of CQC's active directory. "
    "It makes no statement about the quality of any service. "
    "Contains public sector information licensed under the Open Government Licence v3.0."
)
EARLIER_NAME_TEXT = (
    "Held under the name {name} in the CQC editions CareGist stored from {first} to {last}."
)
LOCATION_TEXT = "Status held by CareGist: {status}."
LOCATION_SERVICES_TEXT = " Service types: {services}."
RECORD_NOT_A_RATING_TEXT = (
    "CQC record quoted as held: {rating}. This value is not a published overall rating, so "
    "it is not listed as a rating event."
)
RECORD_NO_DATE_TEXT = (
    "CQC record quoted as held: {rating}. No inspection date is held for it, so it is not "
    "listed as a rating event."
)

CSV_COLUMNS = (
    "report", "cqc_provider_id", "legal_name_as_held", "edition_retrieved_on",
    "edition_source_as_of", "edition_providers_sha256", "edition_locations_sha256",
    "content_sha256", "record_built_on", "row_type", "date", "location_id",
    "location_name", "kind", "rating", "status", "text", "source_label", "source_url",
)

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: Any) -> str:
    """A text cell that a spreadsheet will not read as a formula."""
    if value is None:
        return ""
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def deliverable_filename(provider_id: str, built_on: date, fmt: str) -> str:
    """``caregist-operator-history-<CQC Provider ID>-<YYYY-MM-DD>.<csv|pdf>``."""
    if fmt not in {"csv", "pdf"}:
        raise ValueError(f"unknown deliverable format {fmt!r}")
    return f"caregist-operator-history-{provider_id}-{built_on.isoformat()}.{fmt}"


def pinned_notice(record: dict[str, Any], built_on: date) -> str:
    retrieved_on = date.fromisoformat(record["provider"]["edition"]["retrieved_on"])
    return PINNED_NOTICE.format(built_on=format_date(built_on), retrieved_on=format_date(retrieved_on))


def _is_event_rating(entry: dict[str, Any]) -> bool:
    return bool(entry["inspection_date"] and entry["is_published_rating"])


def render_csv(record: dict[str, Any], *, built_on: date) -> bytes:
    """One source-linked row per location and per dated event, with the limits first."""
    edition = record["provider"]["edition"]
    fixed = {
        "report": TITLE,
        "cqc_provider_id": record["provider_id"],
        "legal_name_as_held": record["provider"]["legal_name"],
        "edition_retrieved_on": edition["retrieved_on"],
        "edition_source_as_of": edition["source_as_of"],
        "edition_providers_sha256": edition["providers_sha256"],
        "edition_locations_sha256": edition["locations_sha256"],
        "content_sha256": record["content_sha256"],
        "record_built_on": built_on.isoformat(),
    }
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="raise")
    writer.writeheader()

    def put(row_type: str, **values: Any) -> None:
        row = {col: "" for col in CSV_COLUMNS}
        row.update({key: _cell(val) for key, val in fixed.items()})
        row["row_type"] = row_type
        row.update({key: _cell(val) for key, val in values.items()})
        writer.writerow(row)

    for limit in record["limits"]:
        put("limit", text=limit)
    put("limit", text=pinned_notice(record, built_on))
    put("limit", text=HASH_NOTICE)
    put("limit", text=SOURCE_NOTICE)
    for earlier in record["provider"]["earlier_names"]:
        put(
            "earlier_name",
            date=earlier["first_edition_retrieved_on"],
            text=EARLIER_NAME_TEXT.format(
                name=earlier["name"],
                first=format_date(date.fromisoformat(earlier["first_edition_retrieved_on"])),
                last=format_date(date.fromisoformat(earlier["last_edition_retrieved_on"])),
            ),
            source_label="CQC edition stored by CareGist",
        )
    for loc in record["locations"]:
        text = LOCATION_TEXT.format(status=STATUS_LABELS[loc["status"]["state"]])
        if loc["service_types"]:
            text += LOCATION_SERVICES_TEXT.format(services="; ".join(loc["service_types"]))
        put(
            "location", date=loc["registration_date"], location_id=loc["location_id"],
            location_name=loc["name"], status=loc["status"]["label"], text=text,
            source_label=loc["registration_source"]["label"], source_url=loc["registration_source"]["url"],
        )
    for event in record["events"]:
        put(
            "event", date=event["date"], location_id=event["location_id"],
            location_name=event["location_name"], kind=event["kind"], rating=event.get("rating"),
            text=event["text"], source_label=event["source"]["label"], source_url=event["source"]["url"],
        )
    for loc in record["locations"]:
        for entry in loc["rating_history"]:
            if _is_event_rating(entry):
                continue
            template = RECORD_NO_DATE_TEXT if entry["is_published_rating"] else RECORD_NOT_A_RATING_TEXT
            put(
                "rating_record", date=entry["inspection_date"], location_id=loc["location_id"],
                location_name=loc["name"], rating=entry["rating"],
                text=template.format(rating=entry["rating"]),
                source_label=entry["source"]["label"], source_url=entry["source"]["url"],
            )
    return buffer.getvalue().encode("utf-8")


def render_pdf(record: dict[str, Any], *, built_on: date) -> bytes:
    """A readable A4 PDF of the same record, built with the in-repo PDF writer."""
    edition = record["provider"]["edition"]
    summary = record["summary"]
    pdf = PdfBuilder(
        title=TITLE,
        footer=f"CareGist  |  {TITLE}  |  {record['provider_id']}  |  {record['content_sha256'][:16]}",
    )
    pdf.title_block(
        subtitle=record["provider"]["legal_name"],
        meta_lines=[
            f"CQC Provider ID: {record['provider_id']}",
            f"Legal name as held by CareGist: {record['provider']['legal_name']}",
            f"CQC edition retrieved on {format_date(date.fromisoformat(edition['retrieved_on']))} "
            f"(data as of {format_date(date.fromisoformat(edition['source_as_of']))})",
            f"Edition providers file SHA-256: {edition['providers_sha256']}",
            f"Edition locations file SHA-256: {edition['locations_sha256']}",
            f"Content SHA-256: {record['content_sha256']}",
            f"Record built on {format_date(built_on)}",
            pinned_notice(record, built_on),
        ],
    )

    pdf.heading("Limits of this record")
    pdf.bullets(list(record["limits"]))
    pdf.paragraph(HASH_NOTICE, muted=True)

    pdf.heading("Summary")
    rows = [
        ("Locations held", str(summary["locations_total"])),
        ("On CQC's active directory", str(summary["on_active_directory"])),
        ("No longer on CQC's active directory", str(summary["no_longer_on_active_directory"])),
        ("Status not held", str(summary["status_not_held"])),
        ("Earliest registration date", summary["earliest_registration_date"] or "None held"),
        ("Latest registration date", summary["latest_registration_date"] or "None held"),
        ("Rating records held", str(summary["rating_records"])),
        ("Inspection dates held", _range(summary["earliest_inspection_date"], summary["latest_inspection_date"])),
        ("Closures observed", str(summary["closures_observed"])),
        ("Reinstatements observed", str(summary["reinstatements_observed"])),
        ("First closure observed on", summary["first_closure_observed_on"] or "None held"),
        ("Observations included up to", record["history_cutoff"] or "None held"),
    ]
    pdf.key_values(rows)

    if record["provider"]["earlier_names"]:
        pdf.heading("Earlier names held")
        pdf.bullets([
            EARLIER_NAME_TEXT.format(
                name=item["name"],
                first=format_date(date.fromisoformat(item["first_edition_retrieved_on"])),
                last=format_date(date.fromisoformat(item["last_edition_retrieved_on"])),
            )
            for item in record["provider"]["earlier_names"]
        ])

    pdf.heading("Locations")
    pdf.table(
        ["CQC location ID", "Name", "Registered", "Status", "Source"],
        [
            [loc["location_id"], loc["name"], loc["registration_date"] or "Not held",
             loc["status"]["label"], loc["registration_source"]["url"]]
            for loc in record["locations"]
        ],
        widths=[1.5, 2.2, 1.2, 1.8, 3.0],
    )

    pdf.heading("Dated events")
    if record["events"]:
        pdf.table(
            ["Date", "Location", "Event", "Source"],
            [
                [event["date"], f"{event['location_name']} ({event['location_id']})", event["text"],
                 f"{event['source']['label']}" + (f"\n{event['source']['url']}" if event["source"]["url"] else "")]
                for event in record["events"]
            ],
            widths=[1.1, 2.2, 3.4, 2.8],
        )
    else:
        pdf.paragraph("CareGist holds no dated events for this operator's locations.")

    other = [(loc, entry) for loc in record["locations"] for entry in loc["rating_history"] if not _is_event_rating(entry)]
    if other:
        pdf.heading("Other CQC records quoted as held")
        pdf.table(
            ["Date", "Location", "Record", "Source"],
            [
                [entry["inspection_date"] or "No date held", f"{loc['name']} ({loc['location_id']})",
                 (RECORD_NO_DATE_TEXT if entry["is_published_rating"] else RECORD_NOT_A_RATING_TEXT).format(
                     rating=entry["rating"]),
                 entry["source"]["url"] or entry["source"]["label"]]
                for loc, entry in other
            ],
            widths=[1.1, 2.2, 3.4, 2.8],
        )

    pdf.heading("About this record")
    pdf.paragraph(SOURCE_NOTICE, muted=True)
    return pdf.build()


def _range(first: str | None, last: str | None) -> str:
    if not first:
        return "None held"
    return first if first == last else f"{first} to {last}"
