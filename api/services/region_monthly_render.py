"""CSV and PDF deliverables for one purchased Region Monthly month.

Both files are drawn from one immutable ``region_monthly_builds`` row. Every
sentence is a fixed template over values the build stored: counts, dates, the
per-metric coverage notes and the fixed limits text. No model writes any text, and
nothing here scores, ranks, predicts or judges a region, a service or a location.

Both files carry the title, the region, the service, the month, the figures with
their coverage notes, the limits stored with the build, the build version, the
time it was built, the data cut-off and the build's ``content_sha256``. The output
is deterministic: the same build row gives the same bytes, whoever downloads it.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timezone
from functools import lru_cache
from typing import Any

from api.service_taxonomy import taxonomy
from api.services import region_monthly as rm
from api.services.pdf_writer import PdfBuilder

TITLE = "Region Monthly"
CSV_CONTENT_TYPE = "text/csv; charset=utf-8"
PDF_CONTENT_TYPE = "application/pdf"
ALL_SERVICES_LABEL = "All services"

# Fixed customer-facing text, apart from the limits (those are stored with the build).
BUILD_NOTICE = (
    "This month was built on {built_on} as build version {version}. If a month is corrected, the "
    "correction is a new numbered version and this version is kept."
)
CUTOFF_NOTICE = "Data cut-off: {cutoff}. The figures use the data CareGist held at that time."
HASH_NOTICE = (
    "The content SHA-256 identifies exactly what was counted. It is the SHA-256 of the canonical JSON form "
    "of the schema version, month, region, service, figures, coverage notes and limits."
)
SOURCE_NOTICE = (
    "CareGist is independent of the Care Quality Commission. These counts are compiled from CQC's published "
    "data and from CareGist's own observations of CQC's directory. They make no statement about the quality "
    "of any service. Contains public sector information licensed under the Open Government Licence v3.0."
)
NO_FIGURE_TEXT = "No figure is given for this month. {coverage}."

RATING_ROWS = (
    ("outstanding", "Outstanding"),
    ("good", "Good"),
    ("requires_improvement", "Requires improvement"),
    ("inadequate", "Inadequate"),
    ("no_published_rating_value", "No published rating value"),
    ("total", "Total"),
)

CSV_COLUMNS = (
    "report", "region", "service", "service_slug", "period_month", "build_version", "built_at",
    "data_cutoff", "content_sha256", "row_type", "metric", "breakdown", "value", "coverage_status",
    "coverage_text", "text",
)

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: Any) -> str:
    """A text cell that a spreadsheet will not read as a formula."""
    if value is None:
        return ""
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


@lru_cache(maxsize=1)
def _service_names() -> dict[str, str]:
    return {entry["slug"]: entry["name"] for entry in taxonomy()}


def service_label(service_slug: str | None) -> str:
    if not service_slug:
        return ALL_SERVICES_LABEL
    return _service_names().get(service_slug, service_slug)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", " and ")).strip("-")


def deliverable_filename(region: str, service_slug: str | None, period_month: date, build_version: int, fmt: str) -> str:
    """``caregist-region-monthly-<region>-<service>-<YYYY-MM>-v<version>.<csv|pdf>``."""
    if fmt not in {"csv", "pdf"}:
        raise ValueError(f"unknown deliverable format {fmt!r}")
    return (
        f"caregist-region-monthly-{_slugify(region)}-{service_slug or 'all-services'}-"
        f"{rm.month_key(period_month)}-v{int(build_version)}.{fmt}"
    )


def _utc(ts: datetime) -> datetime:
    return ts.astimezone(timezone.utc)


def iso_utc(ts: datetime) -> str:
    return _utc(ts).isoformat().replace("+00:00", "Z")


def readable_uk(ts: datetime) -> str:
    local = ts.astimezone(rm.UK)
    return f"{rm.format_day(local.date())} {local:%H:%M} UK time"


def build_notice(build: dict[str, Any]) -> str:
    return BUILD_NOTICE.format(
        built_on=rm.format_day(build["built_at"].astimezone(rm.UK).date()), version=int(build["build_version"])
    )


def cutoff_notice(build: dict[str, Any]) -> str:
    return CUTOFF_NOTICE.format(cutoff=readable_uk(build["built_from_data_cutoff"]))


def verify_build(build: dict[str, Any]) -> bool:
    """True when the stored hash matches the stored content (nothing was altered)."""
    content = rm.canonical_content(
        build["period_month"], build["region"], build["service_slug"], build["metrics"], build["coverage"],
        build["limits"], build["schema_version"],
    )
    return rm.content_sha256(content) == build["content_sha256"]


def _metric_rows(build: dict[str, Any]):
    """(metric key, breakdown label or '', value or None, coverage entry) in a fixed order."""
    for key in rm.METRICS:
        value = build["metrics"].get(key)
        coverage = build["coverage"][key]
        if isinstance(value, dict):
            for field, label in RATING_ROWS:
                yield key, label, value[field], coverage
        else:
            yield key, "", value, coverage


def _coverage_sentence(coverage: dict[str, Any]) -> str:
    text = coverage["text"]
    return text[:1].upper() + text[1:]


def render_csv(build: dict[str, Any]) -> bytes:
    """The limits first, then the notices, then one row per figure with its coverage note."""
    fixed = {
        "report": TITLE,
        "region": build["region"],
        "service": service_label(build["service_slug"]),
        "service_slug": build["service_slug"],
        "period_month": rm.month_key(build["period_month"]),
        "build_version": build["build_version"],
        "built_at": iso_utc(build["built_at"]),
        "data_cutoff": iso_utc(build["built_from_data_cutoff"]),
        "content_sha256": build["content_sha256"],
    }
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="raise", lineterminator="\r\n")
    writer.writeheader()

    def put(row_type: str, **values: Any) -> None:
        row = {col: "" for col in CSV_COLUMNS}
        row.update({key: _cell(val) for key, val in fixed.items()})
        row["row_type"] = row_type
        row.update({key: _cell(val) for key, val in values.items()})
        writer.writerow(row)

    for limit in build["limits"]:
        put("limit", text=limit)
    put("limit", text=build_notice(build))
    put("limit", text=cutoff_notice(build))
    put("limit", text=HASH_NOTICE)
    put("limit", text=SOURCE_NOTICE)
    for key, breakdown, value, coverage in _metric_rows(build):
        definition = rm.METRIC_DEFINITIONS[key]
        put(
            "figure",
            metric=key,
            breakdown=breakdown,
            value="" if value is None else int(value),
            coverage_status=coverage["status"],
            coverage_text=_coverage_sentence(coverage),
            text=definition if value is not None else NO_FIGURE_TEXT.format(coverage=_coverage_sentence(coverage)),
        )
    return buffer.getvalue().encode("utf-8")


def _heading(pdf: PdfBuilder, text: str, *, level: int = 1) -> None:
    """A heading that is never left alone at the foot of a page."""
    pdf._need(110)
    pdf.heading(text, level=level)


def render_pdf(build: dict[str, Any]) -> bytes:
    """A readable A4 PDF of the same build, made with the in-repo PDF writer."""
    month_label = rm.format_month(build["period_month"])
    service = service_label(build["service_slug"])
    pdf = PdfBuilder(
        title=TITLE,
        footer=f"CareGist  |  {TITLE}  |  {build['region']}  |  {rm.month_key(build['period_month'])}  |  "
        f"v{int(build['build_version'])}  |  {build['content_sha256'][:16]}",
    )
    pdf.title_block(
        subtitle=f"{build['region']}  |  {service}  |  {month_label}",
        meta_lines=[
            f"Region: {build['region']}",
            f"Service: {service}",
            f"Month: {month_label} (a UK calendar month)",
            f"Build version: {int(build['build_version'])}",
            f"Built at: {readable_uk(build['built_at'])} ({iso_utc(build['built_at'])})",
            f"Data cut-off: {readable_uk(build['built_from_data_cutoff'])} ({iso_utc(build['built_from_data_cutoff'])})",
            f"Content SHA-256: {build['content_sha256']}",
            build_notice(build),
        ],
    )

    _heading(pdf, "Limits of these figures")
    pdf.bullets(list(build["limits"]))
    pdf.paragraph(HASH_NOTICE, muted=True)

    _heading(pdf, "Figures")
    simple = []
    for key in rm.METRICS:
        value = build["metrics"].get(key)
        if isinstance(value, dict):
            continue
        simple.append(
            [
                rm.METRIC_LABELS[key],
                "No figure" if value is None else str(int(value)),
                _coverage_sentence(build["coverage"][key]),
            ]
        )
    pdf.table(["Figure", "Count", "Coverage"], simple, widths=[2.6, 1.2, 4.2])

    ratings = build["metrics"].get("ratings_published")
    _heading(pdf, rm.METRIC_LABELS["ratings_published"], level=2)
    if isinstance(ratings, dict):
        pdf.table(
            ["Rating value", "Count"],
            [[label, str(int(ratings[field]))] for field, label in RATING_ROWS],
            widths=[3.0, 1.2],
        )
        pdf.paragraph(f"Coverage: {_coverage_sentence(build['coverage']['ratings_published'])}.", muted=True)
    else:
        pdf.paragraph(NO_FIGURE_TEXT.format(coverage=_coverage_sentence(build["coverage"]["ratings_published"])))

    _heading(pdf, "What each figure counts")
    pdf.bullets([f"{rm.METRIC_LABELS[key]}: {rm.METRIC_DEFINITIONS[key]}" for key in rm.METRICS])

    _heading(pdf, "About these figures")
    pdf.paragraph(cutoff_notice(build), muted=True)
    pdf.paragraph(SOURCE_NOTICE, muted=True)
    return pdf.build()
