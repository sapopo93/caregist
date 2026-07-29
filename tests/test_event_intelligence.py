from datetime import date, datetime, timezone

from api.services.event_intelligence import (
    build_homecare_movement_report,
    compute_location_signals,
    diff_market_events,
    evaluate_stale_inspection_events,
    stable_row_hash,
)


def test_stable_row_hash_is_deterministic_for_equivalent_rows():
    left = {"name": "Sunrise", "services": ["Homecare", "Nursing"], "empty": None}
    right = {"empty": None, "services": ["Homecare", "Nursing"], "name": "Sunrise"}

    assert stable_row_hash(left) == stable_row_hash(right)


def test_diff_market_events_emits_expected_mlp_events_idempotently():
    previous = [
        {
            "cqc_location_id": "LOC1",
            "cqc_provider_id": "PROV1",
            "name": "Alpha Care",
            "registration_status": "Registered",
            "latest_rating": "Good",
            "rating_publication_date": date(2024, 1, 1),
            "row_hash": "old-loc1",
        },
        {
            "cqc_location_id": "LOC2",
            "cqc_provider_id": "PROV2",
            "name": "Beta Care",
            "registration_status": "Registered",
            "latest_rating": "Good",
            "rating_publication_date": date(2024, 1, 1),
            "row_hash": "old-loc2",
        },
    ]
    current = [
        {
            "cqc_location_id": "LOC1",
            "cqc_provider_id": "PROV1",
            "name": "Alpha Care",
            "registration_status": "Registered",
            "latest_rating": "Outstanding",
            "rating_publication_date": date(2026, 1, 1),
            "row_hash": "new-loc1",
        },
        {
            "cqc_location_id": "LOC3",
            "cqc_provider_id": "PROV3",
            "name": "Gamma Homecare",
            "registration_status": "Registered",
            "registration_date": date(2026, 6, 1),
            "latest_rating": None,
            "row_hash": "new-loc3",
        },
    ]

    first = diff_market_events(previous, current, snapshot_id=2, detected_at=datetime(2026, 6, 30, tzinfo=timezone.utc))
    second = diff_market_events(previous, current, snapshot_id=2, detected_at=datetime(2026, 6, 30, tzinfo=timezone.utc))

    assert [event.event_type for event in first] == [
        "provider_registered",
        "location_registered",
        "location_archived",
        "rating_changed",
    ]
    assert [event.dedup_key for event in first] == [event.dedup_key for event in second]
    assert len({event.dedup_key for event in first}) == 4


def test_diff_market_events_emits_one_provider_event_for_multiple_new_locations():
    events = diff_market_events(
        [],
        [
            {
                "cqc_location_id": "LOC1",
                "cqc_provider_id": "PROV1",
                "name": "Gamma Homecare North",
                "registration_date": date(2026, 6, 1),
                "row_hash": "loc1",
            },
            {
                "cqc_location_id": "LOC2",
                "cqc_provider_id": "PROV1",
                "name": "Gamma Homecare South",
                "registration_date": date(2026, 6, 1),
                "row_hash": "loc2",
            },
        ],
        snapshot_id=2,
        detected_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    assert [event.event_type for event in events].count("provider_registered") == 1
    assert [event.event_type for event in events].count("location_registered") == 2


def test_stale_evaluator_emits_single_threshold_event_key():
    events = evaluate_stale_inspection_events(
        [
            {
                "cqc_location_id": "LOC1",
                "rating_publication_date": date(2024, 6, 1),
                "latest_rating": "Good",
            }
        ],
        threshold_months=24,
        today=date(2026, 6, 30),
        snapshot_id=5,
    )

    assert len(events) == 1
    assert events[0].event_type == "inspection_became_stale"
    assert events[0].dedup_key.endswith(":24:2026-06")


def test_core_signals_are_deterministic_and_versioned():
    signal = compute_location_signals(
        {
            "cqc_location_id": "LOC1",
            "registration_date": date(2026, 6, 1),
            "rating_publication_date": date(2024, 6, 1),
            "latest_rating": None,
            "service_types": ["Homecare agencies"],
            "region": "London",
        },
        today=date(2026, 6, 30),
    )

    assert signal.score_version == "mlp-v1"
    assert signal.inspection_age_score == 100
    assert signal.rating_limbo_score == 100
    assert signal.supplier_lead_score >= 80
    assert signal.inputs["inspection_age_days"] == 759


def test_report_builder_uses_evidence_grade_language():
    html = build_homecare_movement_report(
        events=[
            {"event_type": "location_registered", "payload": {"new": {"service_types": ["Homecare"], "region": "London"}}},
            {"event_type": "inspection_became_stale", "payload": {"region": "London"}},
        ],
        signals=[
            {
                "subject_id": "LOC1",
                "supplier_lead_score": 82,
                "inspection_age_score": 100,
                "rating_limbo_score": 100,
                "inputs": {"region": "London"},
            }
        ],
        generated_at=date(2026, 6, 30),
    )

    assert "England Homecare Movement Report" in html
    assert "New homecare registrations</dt><dd>1</dd>" in html
    assert "inspection age" in html
    assert "rating-limbo exposure" in html
