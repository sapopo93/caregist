"""Regression tests for CQC provider-state transition events.

Existing coverage (new_registration, status/ownership/group transitions,
dedupe stability) lives in the tests below. This module additionally fixes the
rating transition rules:

* ``rating_changed`` only for a movement between two *published* ratings.
* ``rating_status_changed`` for everything else involving a non-rated state,
  excluded from rating-movement claims.
* No event at all for representation churn (sentinel -> same sentinel, or a
  casing/whitespace variant of the same published rating).
"""

from datetime import date, datetime, timezone

import pytest

from api.services.provider_state_events import (
    EXCLUDED_FROM_RATING_MOVEMENT,
    RATING_STATUS_EVENT,
    build_provider_state_events,
)
from incremental_update import apply_rating_write_policy, clean_location


OBSERVED_AT = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def test_new_location_emits_feed_compatible_registration_event():
    current = {
        "id": "LOC1",
        "provider_id": "PROV1",
        "name": "Alpha Care",
        "status": "ACTIVE",
        "registration_date": "2026-07-01",
        "last_updated": "2026-07-29T08:00:00Z",
    }

    events = build_provider_state_events(None, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == ["new_registration"]
    assert events[0].effective_date == date(2026, 7, 1)
    assert events[0].effective_at is None
    assert events[0].effective_date_source == "cqc.registrationDate"
    assert events[0].dedupe_key == "new_registration:LOC1:2026-07-01"


def test_changed_location_emits_all_state_transitions_in_stable_order():
    previous = {
        "id": "LOC1",
        "provider_id": "PROV1",
        "overall_rating": "Good",
        "status": "ACTIVE",
        "ownership_type": "Organisation",
    }
    current = {
        "id": "LOC1",
        "provider_id": "PROV2",
        "overall_rating": "Outstanding",
        "status": "INACTIVE",
        "ownership_type": "Individual",
        "last_inspection_date": "2026-07-20",
        "last_updated": "2026-07-29T08:00:00Z",
    }

    first = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)
    second = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in first] == [
        "rating_changed",
        "status_changed",
        "ownership_changed",
        "group_movement",
    ]
    assert all(event.effective_date is None for event in first)
    assert all(event.effective_at is None for event in first)
    assert all(event.effective_date_source is None for event in first)
    assert [event.dedupe_key for event in first] == [event.dedupe_key for event in second]
    assert len({event.dedupe_key for event in first}) == 4


def test_blank_and_null_values_are_equivalent():
    previous = {"id": "LOC1", "provider_id": None, "ownership_type": ""}
    current = {
        "id": "LOC1",
        "provider_id": " ",
        "ownership_type": None,
        "last_updated": "invalid",
    }

    assert build_provider_state_events(previous, current, observed_at=OBSERVED_AT) == []


def test_missing_registration_date_is_not_inferred_from_source_or_observation_time():
    current = {
        "id": "LOC1",
        "provider_id": "PROV1",
        "last_updated": "2026-07-29T08:00:00Z",
    }

    events = build_provider_state_events(None, current, observed_at=OBSERVED_AT)

    assert events[0].effective_date is None
    assert events[0].effective_at is None
    assert events[0].effective_date_source is None
    assert events[0].dedupe_key == "new_registration:LOC1:unknown"


def test_observation_clock_does_not_change_transition_identity_or_effective_time():
    previous = {"id": "LOC1", "status": "ACTIVE"}
    current = {
        "id": "LOC1",
        "status": "INACTIVE",
        "last_updated": "2026-07-29T08:00:00Z",
    }

    first = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)
    replay = build_provider_state_events(
        previous,
        current,
        observed_at=datetime(2026, 8, 2, 18, 30, tzinfo=timezone.utc),
    )

    assert first == replay
    assert first[0].effective_date is None
    assert first[0].effective_at is None


# --- rating transitions: published -> published ------------------------------


def _rated(value, **extra):
    record = {"id": "LOC1", "overall_rating": value, "rating_state": "rated"}
    record.update(extra)
    return record


def test_published_rating_movement_is_a_rating_changed_event_with_full_evidence():
    previous = _rated("Good")
    current = _rated(
        "Outstanding",
        rating_state="rated",
        rating_report_date="2026-09-10",
        source_url="https://api.service.cqc.org.uk/public/v1/locations/1-1",
        last_updated="2026-09-16T08:00:00Z",
    )

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == ["rating_changed"]
    event = events[0]
    assert event.old_value == "Good"
    assert event.new_value == "Outstanding"
    assert event.metadata["rating_movement_eligible"] is True
    assert event.metadata["previous_rating"] == "Good"
    assert event.metadata["destination_rating"] == "Outstanding"
    assert event.metadata["destination_rating_state"] == "rated"
    assert event.metadata["destination_evidenced"] is True
    assert event.metadata["incomplete"] is False
    assert event.metadata["publication_date"] == "2026-09-10"
    assert event.metadata["observed_at"] == "2026-09-16T08:00:00Z"
    assert event.metadata["source_reference"].endswith("/locations/1-1")
    assert event.event_type not in EXCLUDED_FROM_RATING_MOVEMENT


def test_rating_changed_defaults_its_source_reference_to_the_canonical_endpoint():
    events = build_provider_state_events(_rated("Good"), _rated("Outstanding"), observed_at=OBSERVED_AT)

    assert events[0].metadata["source_reference"].endswith("/locations/LOC1")


@pytest.mark.parametrize(
    "previous_value,current_value",
    [
        ("Requires Improvement", "Requires improvement"),
        ("Requires improvement", "requires   improvement"),
        ("Good", "good"),
        ("Outstanding", " Outstanding "),
    ],
)
def test_casing_and_whitespace_variants_are_not_rating_movement(previous_value, current_value):
    """The 2026-08/09 ledger recorded these as 24k destination-less changes."""

    events = build_provider_state_events(
        _rated(previous_value),
        _rated(current_value),
        observed_at=OBSERVED_AT,
    )

    assert events == []


# --- rating transitions: sentinels and omissions -----------------------------


def _sentinel(raw_value, state, **extra):
    record = {"id": "LOC1", "overall_rating": raw_value, "rating_state": state}
    record.update(extra)
    return record


def test_sentinel_to_sentinel_is_a_rating_status_event_not_a_rating_change():
    previous = _sentinel("Not Yet Inspected", "not_yet_inspected")
    current = _sentinel("No Published Rating", "not_published")

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == [RATING_STATUS_EVENT]
    event = events[0]
    assert event.event_type in EXCLUDED_FROM_RATING_MOVEMENT
    assert event.old_value == "not_yet_inspected"
    assert event.new_value == "not_published"
    assert event.metadata["rating_movement_eligible"] is False
    assert event.metadata["previous_rating"] is None
    assert event.metadata["destination_rating"] is None


@pytest.mark.parametrize(
    "raw_value,state",
    [
        ("Not Yet Inspected", "not_yet_inspected"),
        ("No Published Rating", "not_published"),
        ("Inspected but not rated", "unrated"),
        ("not yet inspected", "not_yet_inspected"),
    ],
)
def test_sentinel_stored_twice_produces_no_event(raw_value, state):
    """Sentinel -> identical sentinel is representation, not movement."""

    previous = _sentinel(raw_value, state)
    current = _sentinel(raw_value, state)

    assert build_provider_state_events(previous, current, observed_at=OBSERVED_AT) == []


def test_sentinel_left_by_the_old_pipeline_does_not_re_read_as_movement():
    """A sentinel string in the rating column names its own non-rated state."""

    previous = {"id": "LOC1", "overall_rating": "Not Yet Inspected"}
    current = {
        "id": "LOC1",
        "rating_state": "not_yet_inspected",
        "historic_rating": "Not Yet Inspected",
    }

    assert build_provider_state_events(previous, current, observed_at=OBSERVED_AT) == []


def test_sentinel_to_published_rating_is_a_status_event_with_no_previous_rating():
    previous = _sentinel("Not Yet Inspected", "not_yet_inspected")
    current = _rated("Good", rating_state="rated")

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == [RATING_STATUS_EVENT]
    assert events[0].old_value == "not_yet_inspected"
    assert events[0].new_value == "rated"
    assert events[0].metadata["previous_rating"] is None
    assert events[0].metadata["destination_rating"] == "Good"
    assert events[0].metadata["destination_evidenced"] is True


def _stored_after_payload(payload, existing=None):
    """Merge one CQC payload into a stored row the way ``upsert_provider`` does.

    The payload goes through the real ``clean_location`` and the real
    ``apply_rating_write_policy`` (the same call ``upsert_provider`` makes with
    ``full_record=record``); only the SQL round-trip is skipped. Hand-building
    the stored row instead would bypass the decision under test.
    """
    cleaned = clean_location(payload)
    assert cleaned is not None
    written = apply_rating_write_policy(cleaned, existing, full_record=cleaned)
    return {**(existing or {}), **written}


RATED_PAYLOAD = {
    "locationId": "LOC1",
    "name": "Alpha Care",
    "registrationStatus": "Registered",
    "currentRatings": {"overall": {"rating": "Good", "reportDate": "2026-02-01"}},
    "lastUpdated": "2026-03-01T08:00:00Z",
}

WITHDRAWN_PAYLOAD = {
    **RATED_PAYLOAD,
    # The source no longer publishes a current overall rating, and still
    # publishes the historic rating it withdrew.
    "currentRatings": {},
    "historicRatings": [{"overall": {"rating": "Good"}, "date": "2025-01-05"}],
    "lastUpdated": "2026-09-16T08:00:00Z",
}


def test_published_rating_withdrawn_by_the_source_is_a_real_transition_not_a_carry_forward():
    """The 2026-09 shape, driven through the real clean/merge path.

    The source stops publishing a current overall rating: the stored row must
    stop asserting one, keep the withdrawn rating as labelled evidence with its
    date, and the classifier must report the real rated -> not current
    transition rather than a carried-forward value.
    """
    previous = _stored_after_payload(RATED_PAYLOAD)
    assert previous["overall_rating"] == "Good"
    assert previous["rating_state"] == "rated"

    current = _stored_after_payload(WITHDRAWN_PAYLOAD, previous)

    assert current["overall_rating"] is None
    assert current["rating_state"] == "not_published"
    assert current["last_published_rating"] == "Good"
    # The row's own recorded publication date wins over the historic entry's
    # date (2025-01-05): the merge does not overwrite a date it already knows.
    assert current["last_published_rating_date"] == "2026-02-01"
    assert current["rating_report_date"] == "2025-01-05"

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == [RATING_STATUS_EVENT]
    event = events[0]
    assert event.old_value == "rated"
    assert event.new_value == "not_published"
    assert event.metadata["previous_rating"] == "Good"
    assert event.metadata["destination_rating"] is None
    assert event.metadata["destination_evidenced"] is True
    assert event.metadata["incomplete"] is False
    assert event.metadata["historic_rating"] == "Good"
    # The event is dated by the current payload: the source now reports only
    # the historic entry, and its date is what the source publishes today.
    assert event.metadata["publication_date"] == "2025-01-05"

    # A later genuine rating must move from the recorded state, never from the
    # withdrawn value: not_published -> rated, with no rating_changed event
    # pretending "Good" was still the live rating.
    republished = _stored_after_payload(
        {
            **WITHDRAWN_PAYLOAD,
            "currentRatings": {
                "overall": {"rating": "Requires Improvement", "reportDate": "2026-10-01"}
            },
        },
        current,
    )
    assert republished["overall_rating"] == "Requires Improvement"

    again = build_provider_state_events(current, republished, observed_at=OBSERVED_AT)

    assert [event.event_type for event in again] == [RATING_STATUS_EVENT]
    assert again[0].old_value == "not_published"
    assert again[0].new_value == "rated"
    assert again[0].metadata["destination_rating"] == "Requires Improvement"
    assert "rating_changed" not in {event.event_type for event in again}


def test_previous_rating_evidenced_only_by_historic_data_is_labelled_as_such():
    previous = {"id": "LOC1", "overall_rating": "", "status": "ACTIVE"}
    current = {
        "id": "LOC1",
        "overall_rating": None,
        "rating_state": "not_published",
        "historic_rating": "Good",
        "historic_rating_date": "2025-01-05",
        "status": "ACTIVE",
    }

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == [RATING_STATUS_EVENT]
    assert events[0].metadata["previous_rating"] == "Good"
    assert events[0].metadata["previous_rating_source"] == "cqc.historicRatings[0].overall.rating"
    assert events[0].metadata["rating_movement_eligible"] is False


def test_evidence_gap_destination_is_marked_incomplete_not_null():
    previous = _rated("Good")
    current = {"id": "LOC1", "overall_rating": None, "rating_state": "unknown"}

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == [RATING_STATUS_EVENT]
    event = events[0]
    assert event.new_value == "unknown"
    assert event.metadata["destination_evidenced"] is False
    assert event.metadata["incomplete"] is True
    assert event.metadata["incomplete_reason"] == "destination_rating_not_evidenced"
    # The event exists and is flagged; it is never a fabricated movement.
    assert event.event_type != "rating_changed"


def test_unknown_to_unknown_is_not_an_event():
    current = {"id": "LOC1", "overall_rating": None, "rating_state": "unknown"}

    assert build_provider_state_events(dict(current), current, observed_at=OBSERVED_AT) == []


def test_blank_row_cannot_become_a_fabricated_rating_movement():
    """An old '' column is not evidence of a previous rating to move from."""

    previous = {"id": "LOC1", "overall_rating": "", "status": "ACTIVE"}
    current = _rated("Good", status="ACTIVE")

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == [RATING_STATUS_EVENT]
    assert events[0].old_value == "unknown"
    assert events[0].new_value == "rated"
    assert events[0].metadata["previous_rating"] is None
    assert events[0].metadata["destination_rating"] == "Good"


def test_rating_event_precedes_other_transitions():
    previous = _rated("Good", status="ACTIVE")
    current = _sentinel("Not Yet Inspected", "not_yet_inspected", status="INACTIVE")

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == [RATING_STATUS_EVENT, "status_changed"]


def test_rating_movement_claims_can_exclude_status_events_by_type():
    """Consumers must be able to key on the literal type, not on metadata."""

    previous = _rated("Good")
    current = _sentinel("Not Yet Inspected", "not_yet_inspected")

    events = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)

    movement = [event for event in events if event.event_type == "rating_changed"]
    non_movement = [event for event in events if event.event_type in EXCLUDED_FROM_RATING_MOVEMENT]
    assert movement == []
    assert [event.event_type for event in non_movement] == [RATING_STATUS_EVENT]
    assert all(event.metadata["rating_movement_eligible"] is False for event in non_movement)


def test_rating_status_event_dedupe_key_is_stable_and_distinct():
    previous = _sentinel("Not Yet Inspected", "not_yet_inspected")
    current = _sentinel("No Published Rating", "not_published")

    first = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)[0]
    replay = build_provider_state_events(previous, current, observed_at=OBSERVED_AT)[0]
    movement = build_provider_state_events(_rated("Good"), _rated("Outstanding"), observed_at=OBSERVED_AT)[0]

    assert first.dedupe_key == replay.dedupe_key
    assert first.dedupe_key != movement.dedupe_key
    assert first.dedupe_key.startswith(f"{RATING_STATUS_EVENT}:LOC1:")


def test_new_registration_does_not_emit_a_rating_event():
    current = _rated(
        "Good",
        name="Alpha Care",
        status="ACTIVE",
        registration_date="2026-07-01",
    )

    events = build_provider_state_events(None, current, observed_at=OBSERVED_AT)

    assert [event.event_type for event in events] == ["new_registration"]
