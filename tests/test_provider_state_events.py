from datetime import date, datetime, timezone

from api.services.provider_state_events import build_provider_state_events


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
    assert first[0].effective_date == date(2026, 7, 20)
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
