from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from api.services.radar import (
    RadarFilters,
    build_radar_query,
    canonical_event,
    decode_cursor,
    encode_cursor,
    enforce_plan_scope,
    parse_event_types,
    require_radar_access,
)
from api.routers.radar import _saved_view_filters


def test_launch_event_types_reject_speculative_signals():
    assert parse_event_types(None) == ("new_registration", "rating_changed")
    with pytest.raises(HTTPException) as exc:
        parse_event_types(["new_registration", "predicted_closure"])
    assert exc.value.status_code == 422
    assert "predicted_closure" in exc.value.detail


def test_regional_scope_is_mandatory_and_cannot_be_overridden():
    with pytest.raises(HTTPException) as missing:
        enforce_plan_scope("radar-regional", RadarFilters(), {})
    assert missing.value.status_code == 409

    with pytest.raises(HTTPException) as outside:
        enforce_plan_scope(
            "radar-regional",
            RadarFilters(region="London"),
            {"region": "North West"},
        )
    assert outside.value.status_code == 403

    scoped = enforce_plan_scope(
        "radar-regional",
        RadarFilters(),
        {"region": "North West"},
    )
    assert scoped.region == "North West"
    assert scoped.from_date is not None
    assert scoped.from_date >= datetime.now(UTC).date() - timedelta(days=91)


def test_saved_view_contract_rejects_untyped_or_speculative_filters():
    with pytest.raises(HTTPException) as untyped:
        _saved_view_filters({"event_types": "rating_changed"})
    assert untyped.value.status_code == 422

    with pytest.raises(HTTPException) as speculative:
        _saved_view_filters({"event_types": ["predicted_closure"]})
    assert speculative.value.status_code == 422

    parsed = _saved_view_filters(
        {"event_types": ["rating_changed"], "q": "Leeds", "from_date": "2026-08-01"}
    )
    assert parsed.event_types == ("rating_changed",)
    assert parsed.q == "Leeds"
    assert parsed.from_date == date(2026, 8, 1)


def test_radar_browser_plan_rejects_machine_api_key():
    assert require_radar_access("radar-national", "session")["history_days"] == 365
    with pytest.raises(HTTPException) as exc:
        require_radar_access("radar-national", "api_key")
    assert exc.value.status_code == 403
    assert "not machine API access" in exc.value.detail


def test_cursor_round_trip_and_tamper_rejection():
    observed_at = datetime(2026, 8, 9, 9, 30, tzinfo=UTC)
    event_id = uuid4()
    assert decode_cursor(encode_cursor(observed_at, str(event_id))) == (observed_at, event_id)

    with pytest.raises(HTTPException) as exc:
        decode_cursor("not-a-valid-cursor")
    assert exc.value.status_code == 422


def test_radar_query_uses_stable_keyset_cursor_and_bound_parameters():
    cursor = (datetime(2026, 8, 9, 9, 30, tzinfo=UTC), uuid4())
    query, args = build_radar_query(
        RadarFilters(
            q="Leeds",
            region="Yorkshire & Humberside",
            event_types=("rating_changed",),
            from_date=date(2026, 7, 1),
        ),
        cursor=cursor,
        limit=50,
    )

    assert "ORDER BY tel.observed_at DESC, tel.public_event_id DESC" in query
    assert "(tel.observed_at, tel.public_event_id) <" in query
    assert "Leeds" not in query
    assert args[0] == ["rating_changed"]
    assert args[-1] == 51


def _event_row(explanation_status: str) -> dict:
    return {
        "id": 9,
        "public_event_id": UUID("11111111-1111-1111-1111-111111111111"),
        "schema_version": 1,
        "entity_level": "location",
        "event_type": "rating_changed",
        "effective_date": date(2026, 8, 8),
        "effective_at": None,
        "effective_date_source": "cqc.registrationDate",
        "observed_at": datetime(2026, 8, 8, 12, tzinfo=UTC),
        "old_value": '"Good"',
        "new_value": '"Requires improvement"',
        "metadata": {},
        "source_published_at": datetime(2026, 8, 8, 10, tzinfo=UTC),
        "source_checked_at": datetime(2026, 8, 8, 11, tzinfo=UTC),
        "source_url": "https://www.cqc.org.uk/location/1-12345",
        "source_snapshot_sha256": "a" * 64,
        "explanation_status": explanation_status,
        "cqc_location_id": "1-12345",
        "cqc_provider_id": "1-99999",
        "name": "Example Care Service",
        "slug": "example-care-service",
        "type": "Social Care Org",
        "status": "ACTIVE",
        "region": "London",
        "local_authority": "Camden",
        "town": "London",
        "postcode": "NW1 1AA",
        "service_types": "Residential Homes",
        "overall_rating": "Requires improvement",
        "inspection_report_url": None,
        "facts": ["Medicines records were incomplete."],
        "interpretation": ["Compliance support may be relevant."],
        "model_version": "model-1",
        "prompt_version": "prompt-1",
    }


def test_unreviewed_explanation_never_leaks_draft_narrative():
    event = canonical_event(_event_row("pending"), matched_region="London")

    assert event["change"] == {"old": "Good", "new": "Requires improvement"}
    assert event["entity"]["level"] == "location"
    assert event["effective_date"] == "2026-08-08"
    assert event["effective_at"] is None
    assert event["effective_date_source"] == "cqc.registrationDate"
    assert event["effective_timing_statement"] == "CQC published the effective date as 2026-08-08."
    assert event["first_observed_at"] == "2026-08-08T12:00:00+00:00"
    assert event["explanation"] == {
        "status": "pending",
        "facts": [],
        "interpretation": [],
        "model_version": None,
        "prompt_version": None,
    }
    assert "matches London territory" in event["ranking"]["reasons"]


def test_published_explanation_keeps_fact_and_interpretation_separate():
    event = canonical_event(_event_row("published"))

    assert event["explanation"]["facts"] == ["Medicines records were incomplete."]
    assert event["explanation"]["interpretation"] == ["Compliance support may be relevant."]
    assert event["source"]["snapshot_sha256"] == "a" * 64


def test_event_with_no_cqc_effective_time_keeps_effective_fields_null():
    row = _event_row("not_requested")
    row.update(
        effective_date=None,
        effective_at=None,
        effective_date_source=None,
    )

    event = canonical_event(row)

    assert event["effective_date"] is None
    assert event["effective_at"] is None
    assert event["effective_date_source"] is None
    assert event["effective_timing_statement"] == (
        "CQC did not publish an effective timestamp; CareGist first observed "
        "this change at 2026-08-08T12:00:00+00:00."
    )
