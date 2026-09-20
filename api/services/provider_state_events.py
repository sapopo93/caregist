"""Deterministic CQC provider-state transition events.

The trusted event ledger is the audit source of truth.  This module is kept
pure so ingestion can calculate and test transitions before any SQL is run.

Rating transitions are split in two, because CQC publishes sentinel strings
("Not Yet Inspected", "No Published Rating", "Inspected but not rated") and
omitted fields through the same path as real ratings (see
``api.services.rating_states``):

* ``rating_changed`` -- a published rating moved to a *different* published
  rating. Only this event type may feed rating-movement claims.
* ``rating_status_changed`` -- the availability of a published rating changed
  (rated -> not yet inspected, sentinel -> published, ...). It is recorded for
  the audit trail and is explicitly excluded from rating-movement claims.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from api.services.rating_states import (
    RATING_STATES,
    UNKNOWN,
    classify_rating,
    classify_stored_rating,
    is_published_value,
    normalize_rating_text,
)

#: Event type for "the availability of a published rating changed".
#: Deliberately *not* ``rating_changed``: every customer-facing consumer
#: (webhooks, feed queries, rating-movement counters, delivery outbox
#: subscriptions, nightly monitors) keys on the literal ``rating_changed``, so
#: this type is excluded from rating-movement claims by construction.
RATING_STATUS_EVENT = "rating_status_changed"

#: Event types that must never be counted as rating movement.
EXCLUDED_FROM_RATING_MOVEMENT = frozenset({RATING_STATUS_EVENT})

#: Canonical CQC location endpoint, used as the event's source reference when
#: the observation itself did not carry one.
CQC_LOCATION_ENDPOINT = "https://api.service.cqc.org.uk/public/v1/locations/{location_id}"


@dataclass(frozen=True)
class ProviderStateEvent:
    event_type: str
    location_id: str
    provider_id: str | None
    effective_date: date | None
    effective_at: datetime | None
    effective_date_source: str | None
    old_value: Any
    new_value: Any
    dedupe_key: str
    metadata: dict[str, Any]


def _normalise(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _as_explicit_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(value.strip())
            except ValueError:
                pass
    return None


def _dedupe_key(
    event_type: str,
    location_id: str,
    effective_date: date | None,
    effective_at: datetime | None,
    source_change_identity: Any,
    old_value: Any,
    new_value: Any,
) -> str:
    if event_type == "new_registration":
        # Preserve the key already used by migration 015 and the feed sync.
        suffix = effective_date.isoformat() if effective_date is not None else "unknown"
        return f"new_registration:{location_id}:{suffix}"
    transition = json.dumps(
        {"old": old_value, "new": new_value},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(
        (
            f"{event_type}|{location_id}|"
            f"{effective_date.isoformat() if effective_date else ''}|"
            f"{effective_at.isoformat() if effective_at else ''}|"
            f"{source_change_identity or ''}|{transition}"
        ).encode("utf-8")
    ).hexdigest()
    return f"{event_type}:{location_id}:{digest[:32]}"


def _event(
    event_type: str,
    current: dict[str, Any],
    *,
    effective_date: date | None,
    effective_at: datetime | None = None,
    effective_date_source: str | None = None,
    old_value: Any,
    new_value: Any,
    extra_metadata: dict[str, Any] | None = None,
) -> ProviderStateEvent:
    location_id = str(current["id"])
    provider_id = _normalise(current.get("provider_id"))
    metadata = {
        "source_last_updated": current.get("last_updated"),
        "source_inspection_date": current.get("last_inspection_date"),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return ProviderStateEvent(
        event_type=event_type,
        location_id=location_id,
        provider_id=str(provider_id) if provider_id is not None else None,
        effective_date=effective_date,
        effective_at=effective_at,
        effective_date_source=effective_date_source,
        old_value=old_value,
        new_value=new_value,
        dedupe_key=_dedupe_key(
            event_type,
            location_id,
            effective_date,
            effective_at,
            current.get("last_updated") or current.get("source_snapshot_sha256"),
            old_value,
            new_value,
        ),
        metadata=metadata,
    )


def _stored_rating_state(record: dict[str, Any]) -> str | None:
    """Return the recorded ``rating_state`` column value, if it is a known state."""
    state = record.get("rating_state")
    if isinstance(state, str) and state in RATING_STATES:
        return state
    return None


def _last_published_evidence(
    record: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    """Return ``(rating, date)`` of the last rating the source published, if held.

    ``care_providers.last_published_rating`` is evidence about the past, kept
    deliberately separate from the current rating columns. Only a real published
    rating counts here, so a sentinel can never be promoted back into a rating
    claim.
    """
    if not record:
        return (None, None)
    raw = record.get("last_published_rating")
    if not isinstance(raw, str) or not raw.strip():
        return (None, None)
    state, value = classify_stored_rating(raw)
    if not (is_published_value(state) and value is not None):
        return (None, None)
    stored_date = record.get("last_published_rating_date")
    return (value, str(stored_date) if stored_date else None)


def _rating_observation(record: dict[str, Any] | None) -> tuple[str, str | None]:
    """Return ``(state, published_value_or_None)`` for one side of a transition.

    The row's recorded ``rating_state`` is authoritative, because it is written
    from the *current* source payload. The stored rating column is only
    consulted when there is no usable recorded state (a legacy row written
    before states existed). Trusting the column first was the defect: a value
    left in the column by an earlier payload suppressed the real
    rated -> not-currently-rated transition and then invented a movement when
    the source published a rating again. A published value is returned only for
    the ``rated`` state.
    """
    if not record:
        return (UNKNOWN, None)

    recorded = _stored_rating_state(record)
    if recorded is not None:
        if is_published_value(recorded):
            value = record.get("overall_rating")
            return (
                recorded,
                value if isinstance(value, str) and value.strip() else None,
            )
        if recorded != UNKNOWN:
            # A recorded non-rated state (a sentinel) names itself. The column
            # is not allowed to override it.
            return (recorded, None)
        # 'unknown': we could not read the source for this row. That is an
        # evidence gap, not a statement about the rating, so an old value still
        # sitting in the column must not be read as a current rating.
        return (UNKNOWN, None)

    # No usable recorded state at all (legacy row): fall back to the column,
    # which may name a real rating or a sentinel the old behaviour left there.
    # The column is classified with the *stored* authority
    # (:func:`classify_stored_rating`): a legacy ``""``/NULL column means
    # storage says nothing -> UNKNOWN. It must not be read as a payload field,
    # because an absent or blank value there means the opposite thing -- a
    # payload the pipeline could read that publishes no current rating
    # (``not_published``) -- and this row was never a read payload.
    state, value = classify_stored_rating(record.get("overall_rating"))
    if is_published_value(state) and value is not None:
        return (state, value)
    if state != UNKNOWN:
        return (state, None)
    return (UNKNOWN, None)


def _rating_metadata(
    current: dict[str, Any],
    previous_state: str,
    previous_value: str | None,
    current_state: str,
    current_value: str | None,
    *,
    movement: bool,
    previous_last_published: str | None = None,
    previous_last_published_date: str | None = None,
) -> dict[str, Any]:
    """Evidence bundle stored with a rating-scoped event.

    Everything needed to re-check the claim travels with the event: the
    previous and destination values, the destination *state*, where each came
    from, the source reference, the observation time and the best available
    publication date. Nothing is inferred from today's rating.
    """
    historic_raw = current.get("historic_rating")
    has_historic = historic_raw is not None and str(historic_raw).strip() != ""
    historic_state, historic_value = classify_rating(
        historic_raw,
        current_ratings_present=False,
        historic_rating_present=True,
    )
    last_published_value, last_published_date = _last_published_evidence(current)

    previous_rating = previous_value
    previous_rating_date = current.get("rating_report_date") if previous_value else None
    previous_source = "care_providers.overall_rating" if previous_value else None
    if (
        previous_rating is None
        and not is_published_value(previous_state)
        and previous_last_published
    ):
        # The row no longer asserts a current rating, but it holds the last
        # rating the source did publish, with its own date. Recorded as labelled
        # evidence of the value being left behind — never as a current rating.
        previous_rating = previous_last_published
        previous_rating_date = previous_last_published_date
        previous_source = "care_providers.last_published_rating"
    if (
        previous_rating is None
        and not is_published_value(previous_state)
        and is_published_value(historic_state)
    ):
        # The row cannot evidence the rating being left behind (the old
        # pipeline stored "" for it) but the source can. Recorded as historic
        # evidence, labelled as such, never as the current rating.
        previous_rating = historic_value
        previous_source = "cqc.historicRatings[0].overall.rating"

    destination_evidenced = current_state != UNKNOWN
    publication_date = (
        current.get("rating_report_date")
        or current.get("historic_rating_date")
        or current.get("source_published_at")
    )
    return {
        "previous_rating": previous_rating,
        "previous_rating_state": previous_state,
        "previous_rating_source": previous_source,
        "previous_rating_date": previous_rating_date,
        "destination_rating": current_value,
        "destination_rating_state": current_state,
        "destination_evidenced": destination_evidenced,
        "destination_report_date": current.get("rating_report_date"),
        "historic_rating": historic_raw if has_historic else None,
        "historic_rating_state": historic_state if has_historic else None,
        "historic_rating_date": current.get("historic_rating_date"),
        # The last rating the source actually published, kept as its own labelled
        # evidence (with its own date) so clearing the current rating when the
        # source stops publishing one loses nothing.
        "last_published_rating": last_published_value,
        "last_published_rating_date": last_published_date,
        "publication_date": publication_date,
        "observed_at": current.get("last_updated"),
        "source_reference": current.get("source_url")
        or CQC_LOCATION_ENDPOINT.format(location_id=current["id"]),
        # An unevidenced destination is marked incomplete rather than emitted
        # with a null destination or silently stored as a blank string.
        "incomplete": not destination_evidenced,
        "incomplete_reason": (
            None if destination_evidenced else "destination_rating_not_evidenced"
        ),
        "rating_movement_eligible": movement,
    }


def _rating_transition_event(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> ProviderStateEvent | None:
    """Build the rating-scoped event for one transition, or None.

    See the module docstring: only a movement between two *published* ratings
    is a ``rating_changed`` event. Anything involving a non-rated state is
    recorded as ``RATING_STATUS_EVENT``, which no rating-movement claim or
    customer-facing feed consumes.
    """
    previous_state, previous_value = _rating_observation(previous)
    current_state, current_value = _rating_observation(current)
    # Evidence of what the row says the source last published. Kept separate
    # from the current rating: it names the value being left behind when the row
    # itself can no longer evidence one, and the event records it as such.
    previous_last_published, previous_last_published_date = _last_published_evidence(previous)

    if is_published_value(previous_state) and is_published_value(current_state):
        if normalize_rating_text(previous_value) == normalize_rating_text(current_value):
            # "Requires Improvement" -> "Requires improvement" is the same
            # published rating: casing/whitespace is representation, not
            # movement.
            return None
        return _event(
            "rating_changed",
            current,
            effective_date=None,
            old_value=previous_value,
            new_value=current_value,
            extra_metadata=_rating_metadata(
                current,
                previous_state,
                previous_value,
                current_state,
                current_value,
                movement=True,
                previous_last_published=previous_last_published,
                previous_last_published_date=previous_last_published_date,
            ),
        )

    if previous_state == current_state:
        return None

    return _event(
        RATING_STATUS_EVENT,
        current,
        effective_date=None,
        # The destination is the evidenced state itself, never a null value.
        old_value=previous_state,
        new_value=current_state,
        extra_metadata=_rating_metadata(
            current,
            previous_state,
            previous_value,
            current_state,
            current_value,
            movement=False,
            previous_last_published=previous_last_published,
            previous_last_published_date=previous_last_published_date,
        ),
    )


def build_provider_state_events(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> list[ProviderStateEvent]:
    """Return ordered, replay-safe events for one CQC location transition."""
    # ``observed_at`` remains accepted for callers that timestamp the collection
    # attempt. It must not influence event identity or CQC effective timing;
    # trusted_event_ledger.observed_at is set only by the first successful INSERT.
    _ = observed_at

    if previous is None:
        effective = _as_explicit_date(current.get("registration_date"))
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
                effective_date_source="cqc.registrationDate" if effective else None,
                old_value=None,
                new_value=snapshot,
            )
        ]

    events: list[ProviderStateEvent] = []
    rating_event = _rating_transition_event(previous, current)
    if rating_event is not None:
        events.append(rating_event)

    transitions = (
        ("status_changed", "status"),
        ("ownership_changed", "ownership_type"),
        # CQC provider ID is the authoritative organisation/group membership
        # for a location. A change records movement between provider groups.
        ("group_movement", "provider_id"),
    )
    for event_type, field in transitions:
        old_value = _normalise(previous.get(field))
        new_value = _normalise(current.get(field))
        if old_value == new_value:
            continue
        events.append(
            _event(
                event_type,
                current,
                effective_date=None,
                old_value=old_value,
                new_value=new_value,
            )
        )
    return events
