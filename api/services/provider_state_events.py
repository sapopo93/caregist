"""Deterministic CQC provider-state transition events.

The trusted event ledger is the audit source of truth.  This module is kept
pure so ingestion can calculate and test transitions before any SQL is run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ProviderStateEvent:
    event_type: str
    location_id: str
    provider_id: str | None
    effective_date: date
    old_value: Any
    new_value: Any
    dedupe_key: str
    metadata: dict[str, Any]


def _normalise(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _as_date(value: Any, fallback: date) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(value.strip()[:10])
            except ValueError:
                pass
    return fallback


def _dedupe_key(
    event_type: str,
    location_id: str,
    effective_date: date,
    old_value: Any,
    new_value: Any,
) -> str:
    if event_type == "new_registration":
        # Preserve the key already used by migration 015 and the feed sync.
        return f"new_registration:{location_id}:{effective_date.isoformat()}"
    transition = json.dumps(
        {"old": old_value, "new": new_value},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(
        f"{event_type}|{location_id}|{effective_date.isoformat()}|{transition}".encode("utf-8")
    ).hexdigest()
    return f"{event_type}:{location_id}:{digest[:32]}"


def _event(
    event_type: str,
    current: dict[str, Any],
    *,
    effective_date: date,
    old_value: Any,
    new_value: Any,
) -> ProviderStateEvent:
    location_id = str(current["id"])
    provider_id = _normalise(current.get("provider_id"))
    return ProviderStateEvent(
        event_type=event_type,
        location_id=location_id,
        provider_id=str(provider_id) if provider_id is not None else None,
        effective_date=effective_date,
        old_value=old_value,
        new_value=new_value,
        dedupe_key=_dedupe_key(event_type, location_id, effective_date, old_value, new_value),
        metadata={
            "source_last_updated": current.get("last_updated"),
            "source_inspection_date": current.get("last_inspection_date"),
        },
    )


def build_provider_state_events(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> list[ProviderStateEvent]:
    """Return ordered, replay-safe events for one CQC location transition."""
    observed = observed_at or datetime.now(timezone.utc)
    observed_date = observed.date()
    source_date = _as_date(current.get("last_updated"), observed_date)

    if previous is None:
        effective = _as_date(current.get("registration_date"), source_date)
        snapshot = {
            key: _normalise(current.get(key))
            for key in (
                "name",
                "slug",
                "status",
                "type",
                "registration_date",
                "region",
                "local_authority",
                "postcode",
                "service_types",
            )
        }
        return [
            _event(
                "new_registration",
                current,
                effective_date=effective,
                old_value=None,
                new_value=snapshot,
            )
        ]

    transitions = (
        (
            "rating_changed",
            "overall_rating",
            _as_date(current.get("last_inspection_date"), source_date),
        ),
        ("status_changed", "status", source_date),
        ("ownership_changed", "ownership_type", source_date),
        # CQC provider ID is the authoritative organisation/group membership
        # for a location. A change records movement between provider groups.
        ("group_movement", "provider_id", source_date),
    )
    events: list[ProviderStateEvent] = []
    for event_type, field, effective_date in transitions:
        old_value = _normalise(previous.get(field))
        new_value = _normalise(current.get(field))
        if old_value == new_value:
            continue
        events.append(
            _event(
                event_type,
                current,
                effective_date=effective_date,
                old_value=old_value,
                new_value=new_value,
            )
        )
    return events
