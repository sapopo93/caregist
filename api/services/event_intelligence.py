"""Deterministic event-intelligence primitives for the CareGist MLP."""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

from tools.evidence_language_guard import scan_text


SCORE_VERSION = "mlp-v1"
MAX_SCORE = 100
STALE_INSPECTION_DAYS = 730


@dataclass(frozen=True)
class MarketEvent:
    event_type: str
    subject_type: str
    subject_id: str
    occurred_at: date
    detected_at: datetime
    snapshot_id: int
    payload: dict[str, Any]
    dedup_key: str


@dataclass(frozen=True)
class LocationSignal:
    subject_id: str
    score_version: str
    computed_at: date
    inspection_age_score: int
    rating_limbo_score: int
    supplier_lead_score: int
    inputs: dict[str, Any]


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def stable_row_hash(row: dict[str, Any]) -> str:
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _event_key(event_type: str, subject_id: str, *parts: Any) -> str:
    salient = "|".join(str(part) for part in parts if part is not None)
    digest = hashlib.sha256(f"{event_type}|{subject_id}|{salient}".encode("utf-8")).hexdigest()
    return f"{event_type}:{subject_id}:{digest[:24]}"


def _as_date(value: Any, fallback: date) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return fallback


def _normalise_service_types(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value)]


def _registration_events(
    row: dict[str, Any],
    *,
    previous_provider_ids: set[Any],
    detected_at: datetime,
    snapshot_id: int,
) -> list[MarketEvent]:
    location_id = str(row["cqc_location_id"])
    provider_id = row.get("cqc_provider_id")
    occurred_at = _as_date(row.get("registration_date"), detected_at.date())
    events: list[MarketEvent] = []
    if provider_id and provider_id not in previous_provider_ids:
        events.append(
            MarketEvent(
                event_type="provider_registered",
                subject_type="provider",
                subject_id=str(provider_id),
                occurred_at=occurred_at,
                detected_at=detected_at,
                snapshot_id=snapshot_id,
                payload={"new": row},
                dedup_key=_event_key("provider_registered", str(provider_id), occurred_at),
            )
        )
    events.append(
        MarketEvent(
            event_type="location_registered",
            subject_type="location",
            subject_id=location_id,
            occurred_at=occurred_at,
            detected_at=detected_at,
            snapshot_id=snapshot_id,
            payload={"new": row},
            dedup_key=_event_key("location_registered", location_id, occurred_at),
        )
    )
    return events


def _archived_event(row: dict[str, Any], *, occurred_at: date, detected_at: datetime, snapshot_id: int) -> MarketEvent:
    location_id = str(row["cqc_location_id"])
    return MarketEvent(
        event_type="location_archived",
        subject_type="location",
        subject_id=location_id,
        occurred_at=occurred_at,
        detected_at=detected_at,
        snapshot_id=snapshot_id,
        payload={"old": row},
        dedup_key=_event_key("location_archived", location_id, occurred_at),
    )


def _rating_event(
    old: dict[str, Any],
    new: dict[str, Any],
    *,
    detected_at: datetime,
    snapshot_id: int,
) -> MarketEvent | None:
    if old.get("latest_rating") == new.get("latest_rating"):
        return None
    location_id = str(new["cqc_location_id"])
    effective_date = _as_date(new.get("rating_publication_date"), detected_at.date())
    return MarketEvent(
        event_type="rating_changed",
        subject_type="location",
        subject_id=location_id,
        occurred_at=effective_date,
        detected_at=detected_at,
        snapshot_id=snapshot_id,
        payload={
            "old_rating": old.get("latest_rating"),
            "new_rating": new.get("latest_rating"),
            "old": old,
            "new": new,
        },
        dedup_key=_event_key(
            "rating_changed",
            location_id,
            old.get("latest_rating"),
            new.get("latest_rating"),
            effective_date,
        ),
    )


def diff_market_events(
    previous_locations: list[dict[str, Any]],
    current_locations: list[dict[str, Any]],
    *,
    snapshot_id: int,
    detected_at: datetime | None = None,
) -> list[MarketEvent]:
    detected = detected_at or datetime.now(timezone.utc)
    today = detected.date()
    previous_by_location = {row["cqc_location_id"]: row for row in previous_locations}
    current_by_location = {row["cqc_location_id"]: row for row in current_locations}
    previous_provider_ids = {row.get("cqc_provider_id") for row in previous_locations if row.get("cqc_provider_id")}
    emitted_provider_ids = set(previous_provider_ids)
    events: list[MarketEvent] = []

    for location_id in sorted(set(current_by_location) - set(previous_by_location)):
        row = current_by_location[location_id]
        events.extend(
            _registration_events(
                row,
                previous_provider_ids=emitted_provider_ids,
                detected_at=detected,
                snapshot_id=snapshot_id,
            )
        )
        if row.get("cqc_provider_id"):
            emitted_provider_ids.add(row.get("cqc_provider_id"))

    for location_id in sorted(set(previous_by_location) - set(current_by_location)):
        events.append(
            _archived_event(
                previous_by_location[location_id],
                occurred_at=today,
                detected_at=detected,
                snapshot_id=snapshot_id,
            )
        )

    for location_id in sorted(set(previous_by_location) & set(current_by_location)):
        event = _rating_event(
            previous_by_location[location_id],
            current_by_location[location_id],
            detected_at=detected,
            snapshot_id=snapshot_id,
        )
        if event:
            events.append(event)

    return events


def evaluate_stale_inspection_events(
    locations: list[dict[str, Any]],
    *,
    threshold_months: int,
    today: date,
    snapshot_id: int,
) -> list[MarketEvent]:
    threshold_days = threshold_months * 30
    events: list[MarketEvent] = []
    detected = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    effective_month = today.strftime("%Y-%m")
    for row in locations:
        published = _as_date(row.get("rating_publication_date"), today)
        if (today - published).days < threshold_days:
            continue
        location_id = str(row["cqc_location_id"])
        events.append(
            MarketEvent(
                event_type="inspection_became_stale",
                subject_type="location",
                subject_id=location_id,
                occurred_at=today,
                detected_at=detected,
                snapshot_id=snapshot_id,
                payload={
                    "threshold_months": threshold_months,
                    "rating_publication_date": published,
                    "latest_rating": row.get("latest_rating"),
                },
                dedup_key=f"inspection_became_stale:{location_id}:{threshold_months}:{effective_month}",
            )
        )
    return events


def _bounded_score(value: int) -> int:
    return max(0, min(MAX_SCORE, value))


def compute_location_signals(location: dict[str, Any], *, today: date) -> LocationSignal:
    rating_publication_date = _as_date(location.get("rating_publication_date"), today)
    registration_date = _as_date(location.get("registration_date"), today)
    inspection_age_days = (today - rating_publication_date).days
    registration_age_days = (today - registration_date).days
    latest_rating = location.get("latest_rating")
    service_types = _normalise_service_types(location.get("service_types"))
    service_blob = " ".join(service_types).lower()

    inspection_age_score = _bounded_score(round(inspection_age_days / STALE_INSPECTION_DAYS * MAX_SCORE))
    rating_limbo_score = MAX_SCORE if not latest_rating else _bounded_score(round(inspection_age_days / STALE_INSPECTION_DAYS * 80))
    new_entrant_points = 30 if registration_age_days <= 90 else 0
    homecare_points = 25 if "homecare" in service_blob or "home care" in service_blob else 0
    unrated_points = 25 if not latest_rating else 0
    region_points = 10 if location.get("region") else 0
    supplier_lead_score = _bounded_score(new_entrant_points + homecare_points + unrated_points + region_points)

    inputs = {
        "inspection_age_days": inspection_age_days,
        "registration_age_days": registration_age_days,
        "latest_rating": latest_rating,
        "service_types": service_types,
        "region": location.get("region"),
    }
    return LocationSignal(
        subject_id=str(location["cqc_location_id"]),
        score_version=SCORE_VERSION,
        computed_at=today,
        inspection_age_score=inspection_age_score,
        rating_limbo_score=rating_limbo_score,
        supplier_lead_score=supplier_lead_score,
        inputs=inputs,
    )


def _is_homecare_event(event: dict[str, Any]) -> bool:
    payload = event.get("payload", {})
    service_types = payload.get("service_types")
    if service_types is None and isinstance(payload.get("new"), dict):
        service_types = payload["new"].get("service_types")
    service_blob = " ".join(_normalise_service_types(service_types)).lower()
    return "homecare" in service_blob or "home care" in service_blob


def _average_inspection_age_score(signals: list[dict[str, Any]]) -> int:
    if not signals:
        return 0
    return round(sum(int(signal.get("inspection_age_score", 0)) for signal in signals) / len(signals))


def build_homecare_movement_report(
    *,
    events: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    generated_at: date,
) -> str:
    homecare_events = [event for event in events if _is_homecare_event(event)]
    registrations = sum(1 for event in homecare_events if event.get("event_type") == "location_registered")
    stale_events = sum(1 for event in events if event.get("event_type") == "inspection_became_stale")
    high_supplier = sum(1 for signal in signals if int(signal.get("supplier_lead_score", 0)) >= 80)
    avg_inspection_age = _average_inspection_age_score(signals)

    html_report = f"""<!doctype html>
<html lang="en-GB">
<head><meta charset="utf-8"><title>England Homecare Movement Report</title></head>
<body>
  <h1>England Homecare Movement Report</h1>
  <p>Generated {html.escape(generated_at.isoformat())}</p>
  <dl>
    <dt>New homecare registrations</dt><dd>{registrations}</dd>
    <dt>Inspection age signal</dt><dd>{avg_inspection_age}</dd>
    <dt>rating-limbo exposure</dt><dd>{stale_events}</dd>
    <dt>Supplier trigger count</dt><dd>{high_supplier}</dd>
  </dl>
  <p>This report describes movement, public-quality visibility, inspection age, and regulatory latency.</p>
</body>
</html>
"""
    findings = scan_text("homecare-movement-report.html", html_report)
    if findings:
        joined = ", ".join(finding.phrase for finding in findings)
        raise ValueError(f"Report contains banned provider/location framing: {joined}")
    return html_report
