"""P4 competitor scan: same-type registered services around a postcode.

Input: a postcode, a radius and a service type. Output (PDF + CSV):

* every ACTIVE same-type service within the radius, with its resolved current
  rating and publication date (api/services/rating_resolver.py), registered
  places and distance;
* registrations and *confirmed* closures within the radius in the 12 months to
  the CQC export date (api/services/registration_endings.py);
* the "CQC data as at" dates, OGL attribution and a statement that CareGist is
  independent of CQC.

Pure: callers supply directory rows (api/queries/competitor_scan.py), export
rows and source dates. Generation refuses unless ``competitor_scan_enabled``.
"""

from __future__ import annotations

import csv
import io
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable

from api.services.pdf_writer import PdfBuilder
from api.services.rating_resolver import ResolvedRating, evidence_from_provider_row, resolve_rating
from api.services.registration_endings import CONFIRMED_CLOSURE, EndingIndex, classify_ending

OGL_ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0. "
    "Source: Care Quality Commission."
)
INDEPENDENCE_STATEMENT = (
    "CareGist is independent of the Care Quality Commission (CQC). This scan is compiled from "
    "CQC's published register and ratings data; CQC has not produced, reviewed or endorsed it."
)
FACTUAL_STATEMENT = (
    "Ratings and counts describe what CQC has published. They are not statements about any "
    "service's current quality, finances or intentions. Verify each record with CQC before acting."
)

#: Service type -> (directory service_types ILIKE pattern, export-row predicate).
SERVICE_TYPES: dict[str, tuple[str, str]] = {
    "care_home": ("%care home service%", "Care homes (with or without nursing)"),
    "care_home_nursing": ("%care home service with nursing%", "Care homes with nursing"),
    "care_home_residential": ("%care home service without nursing%", "Care homes without nursing"),
    "homecare": ("%domiciliary care service%", "Homecare (domiciliary care)"),
    "supported_living": ("%supported living service%", "Supported living"),
}
MIN_RADIUS_KM = 0.5
MAX_RADIUS_KM = 50.0

_STATUS_TEXT = {
    "current": "",
    "inherited": "inherited from a predecessor registration",
    "unresolved": "not shown: CQC sources conflict",
    "none": "no published rating",
}


class ScanDisabled(RuntimeError):
    pass


class ScanInputError(ValueError):
    pass


def ensure_enabled() -> None:
    from api.config import settings

    if not settings.competitor_scan_enabled:
        raise ScanDisabled("competitor scan is disabled (COMPETITOR_SCAN_ENABLED=false)")


def validate_inputs(postcode: str, radius_km: float, service_type: str) -> tuple[str, float, str]:
    pc = " ".join(str(postcode or "").upper().split())
    if not pc or len(pc.replace(" ", "")) < 5:
        raise ScanInputError("a full UK postcode is required")
    try:
        radius = float(radius_km)
    except (TypeError, ValueError) as exc:
        raise ScanInputError("radius must be a number of kilometres") from exc
    if not (MIN_RADIUS_KM <= radius <= MAX_RADIUS_KM):
        raise ScanInputError(f"radius must be between {MIN_RADIUS_KM} and {MAX_RADIUS_KM} km")
    if service_type not in SERVICE_TYPES:
        raise ScanInputError(f"unknown service type {service_type!r}")
    return pc, radius, service_type


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def export_row_matches(row: dict[str, Any], service_type: str) -> bool:
    gac = {str(g.get("description") or "").casefold() for g in row.get("gacServiceTypes") or [] if isinstance(g, dict)}
    if service_type == "care_home":
        return row.get("careHome") == "Y"
    if service_type == "care_home_nursing":
        return "care home service with nursing" in gac
    if service_type == "care_home_residential":
        return "care home service without nursing" in gac
    if service_type == "homecare":
        return "domiciliary care service" in gac
    return "supported living service" in gac


@dataclass(frozen=True)
class Competitor:
    location_id: str
    name: str
    postcode: str
    distance_km: float
    registered_places: int | None
    registration_date: date | None
    rating: ResolvedRating


@dataclass(frozen=True)
class Movement:
    window_start: date
    window_end: date
    registrations: tuple[str, ...]
    confirmed_closures: tuple[str, ...]
    other_endings: dict[str, int]


@dataclass(frozen=True)
class CompetitorScan:
    postcode: str
    radius_km: float
    service_type: str
    origin: tuple[float, float]
    origin_method: str
    competitors: tuple[Competitor, ...]
    movement: Movement
    data_as_at: dict[str, str]
    rating_counts: dict[str, int] = field(default_factory=dict)


def build_competitor_scan(
    *,
    postcode: str,
    radius_km: float,
    service_type: str,
    origin: tuple[float, float],
    origin_method: str,
    directory_rows: Iterable[dict[str, Any]],
    export_rows: list[dict[str, Any]],
    export_window_end: date,
    file_edition_date: date | None,
    data_as_at: dict[str, str],
) -> CompetitorScan:
    ensure_enabled()
    postcode, radius_km, service_type = validate_inputs(postcode, radius_km, service_type)
    competitors = []
    for row in directory_rows:
        resolved = resolve_rating(
            evidence_from_provider_row(row, file_edition_date=file_edition_date),
            registration_date=row.get("registration_date"),
        )
        competitors.append(Competitor(
            location_id=row["id"], name=row["name"], postcode=row.get("postcode") or "",
            distance_km=round(float(row["distance_km"]), 2), registered_places=row.get("number_of_beds"),
            registration_date=row.get("registration_date"), rating=resolved,
        ))
    competitors.sort(key=lambda c: (c.distance_km, c.location_id))

    window_start = export_window_end - timedelta(days=364)
    index = EndingIndex.build(export_rows)
    lat0, lon0 = origin
    registrations, closures, others = [], [], Counter()
    for row in export_rows:
        if not export_row_matches(row, service_type):
            continue
        try:
            lat, lon = float(row["onspdLatitude"]), float(row["onspdLongitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if haversine_km(lat0, lon0, lat, lon) > radius_km:
            continue
        lid = str(row.get("locationId") or "")
        registered = _day(row.get("registrationDate"))
        if registered and window_start <= registered <= export_window_end:
            registrations.append(lid)
        ending = classify_ending(row, index)
        if ending and ending.end_date and window_start <= ending.end_date <= export_window_end:
            if ending.ending_class == CONFIRMED_CLOSURE:
                closures.append(lid)
            else:
                others[ending.ending_class] += 1
    movement = Movement(window_start, export_window_end, tuple(sorted(registrations)),
                        tuple(sorted(closures)), dict(sorted(others.items())))
    return CompetitorScan(
        postcode=postcode, radius_km=radius_km, service_type=service_type, origin=origin,
        origin_method=origin_method, competitors=tuple(competitors), movement=movement,
        data_as_at=dict(data_as_at),
        rating_counts=dict(sorted(Counter(_count_key(c.rating) for c in competitors).items())),
    )


def _day(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _count_key(r: ResolvedRating) -> str:
    return r.value if r.is_current else _STATUS_TEXT[r.status]


def rating_cell(r: ResolvedRating) -> str:
    if not r.displayable:
        return _STATUS_TEXT[r.status]
    note = _STATUS_TEXT[r.status]
    return r.value + (f" ({note})" if note else "")


def scan_to_csv(scan: CompetitorScan) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "cqc_location_id", "name", "postcode", "distance_km", "registered_places", "registration_date",
        "rating", "rating_status", "rating_publication_date", "rating_source",
        "api_rating", "api_rating_date", "file_rating", "file_rating_date", "file_sha256",
        "cqc_url", "cqc_data_as_at", "licence",
    ])
    as_at = "; ".join(f"{k}: {v}" for k, v in scan.data_as_at.items())
    for c in scan.competitors:
        d = c.rating.to_dict()
        w.writerow([
            c.location_id, c.name, c.postcode, f"{c.distance_km:.2f}",
            c.registered_places if c.registered_places is not None else "",
            c.registration_date.isoformat() if c.registration_date else "",
            d["value"] or "", d["status"], d["publication_date"] or "", d["source"] or "",
            d["api_value"] or "", d["api_publication_date"] or "", d["file_value"] or "",
            d["file_publication_date"] or "", d["file_sha256"] or "",
            f"https://www.cqc.org.uk/location/{c.location_id}", as_at, OGL_ATTRIBUTION,
        ])
    return buf.getvalue()


def render_scan_pdf(scan: CompetitorScan) -> bytes:
    label = SERVICE_TYPES[scan.service_type][1]
    pdf = PdfBuilder(title="Competitor scan", footer=f"CareGist  |  {scan.postcode}  |  {label}")
    pdf.title_block(
        subtitle=f"{label} within {scan.radius_km:g} km of {scan.postcode}",
        meta_lines=[f"CQC data as at: {v} ({k})" for k, v in scan.data_as_at.items()]
        + [f"Search centre: {scan.origin[0]:.5f}, {scan.origin[1]:.5f} ({scan.origin_method})"],
    )
    places = [c.registered_places for c in scan.competitors if c.registered_places]
    mv = scan.movement
    pdf.heading("1. Summary")
    pdf.key_values([
        ("Registered services", str(len(scan.competitors))),
        ("Registered places", f"{sum(places)} across {len(places)} services reporting places" if places else "not reported"),
        ("Ratings", ", ".join(f"{k}: {v}" for k, v in scan.rating_counts.items()) or "none"),
        ("Registrations, 12 months", f"{len(mv.registrations)} ({mv.window_start.isoformat()} to {mv.window_end.isoformat()})"),
        ("Confirmed closures, 12 months", str(len(mv.confirmed_closures))),
        ("Other registration endings", ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in mv.other_endings.items()) or "none"),
    ])
    pdf.paragraph(
        "Closures count only confirmed closures: re-registrations and ownership changes that CQC "
        "links to a successor location, dormant services and unresolved endings are reported "
        "separately and not counted as closures.", muted=True,
    )
    pdf.heading("2. Registered services within the radius")
    pdf.table(
        ["Service", "km", "Places", "Rating", "Published"],
        [[f"{c.name}\n{c.location_id}  {c.postcode}", f"{c.distance_km:.1f}",
          str(c.registered_places) if c.registered_places else "-", rating_cell(c.rating),
          c.rating.publication_date.isoformat() if c.rating.displayable and c.rating.publication_date else "-"]
         for c in scan.competitors] or [["No registered services of this type in the radius", "", "", "", ""]],
        widths=[2.6, 0.5, 0.6, 1.5, 0.9],
    )
    pdf.heading("3. Method and sources")
    pdf.bullets([
        "Services: ACTIVE CareGist directory records of the selected type whose location point lies "
        "within the radius (PostGIS distance on the CQC-published coordinates).",
        "Ratings: the most recently published overall rating across CQC's API and CQC's published "
        "ratings file. Inherited ratings are labelled; where the sources conflict no rating is shown.",
        "Movement: registrations and registration endings in CQC's location export within the same "
        "radius; endings are classified as confirmed closures, re-registrations, dormant or unresolved.",
    ])
    pdf.heading("4. Independence, licence and limitations")
    pdf.paragraph(INDEPENDENCE_STATEMENT)
    pdf.paragraph(FACTUAL_STATEMENT)
    pdf.paragraph(OGL_ATTRIBUTION, muted=True)
    return pdf.build()
