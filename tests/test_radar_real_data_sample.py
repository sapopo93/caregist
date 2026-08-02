from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from tools.generate_radar_territory_sample import (
    SampleBundle,
    build_sample,
    collect_events,
    render_markdown,
    select_territory,
)


WINDOW_START = date(2026, 2, 14)
WINDOW_END = date(2026, 2, 20)


def _provider_names() -> dict[str, str]:
    return {
        "P1": "Alpha Care Ltd",
        "P2": "Beta Care Ltd",
        "P3": "Gamma Care Ltd",
        "P4": "Delta Care Ltd",
    }


def _registration_row(provider_id: str, location_id: str, name: str, registration_date: str, territory: str = "Gloucestershire") -> dict[str, object]:
    return {
        "providerId": provider_id,
        "locationId": location_id,
        "name": name,
        "localAuthority": territory,
        "region": "South West",
        "registrationDate": registration_date,
        "registrationStatus": "Registered",
    }


def test_select_territory_prefers_highest_count_then_alphabetical():
    counts = Counter({"Bradford": 3, "Gloucestershire": 3, "Hampshire": 2})

    assert select_territory(counts) == "Bradford"


def test_collect_events_includes_seven_day_boundaries():
    rows = [
        _registration_row("P1", "L1", "Boundary Start", "2026-02-14"),
        _registration_row("P2", "L2", "Boundary End", "2026-02-20"),
        _registration_row("P3", "L3", "Outside Window", "2026-02-13"),
        {
            "providerId": "P4",
            "locationId": "L4",
            "name": "Rating Boundary",
            "localAuthority": "Gloucestershire",
            "region": "South West",
            "historicRatings": [
                {"reportDate": "2026-02-18", "overall": {"rating": "Good"}},
                {"reportDate": "2026-02-20", "overall": {"rating": "Outstanding"}},
            ],
        },
    ]

    events, skipped = collect_events(
        rows,
        provider_names=_provider_names(),
        source_path=Path("/Users/user/CareGist/_locations_detail.ndjson"),
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert skipped == 1
    assert [event.location_id for event in events] == ["L1", "L2", "L4"]
    assert [event.effective_date.isoformat() for event in events] == ["2026-02-14", "2026-02-20", "2026-02-20"]


def test_collect_events_skips_missing_fields_without_crashing():
    rows = [
        {
            "providerId": "P1",
            "locationId": "L1",
            "name": "Missing Provider Name",
            "localAuthority": "Gloucestershire",
            "region": "South West",
            "registrationDate": "2026-02-18",
        },
        {
            "providerId": "P2",
            "locationId": "L2",
            "name": "Missing Date",
            "localAuthority": "Gloucestershire",
            "region": "South West",
        },
        {
            "providerId": "P3",
            "locationId": "L3",
            "name": "Missing Territory",
            "region": "South West",
            "registrationDate": "2026-02-18",
        },
    ]

    events, skipped = collect_events(
        rows,
        provider_names={"P2": "Beta Care Ltd"},
        source_path=Path("/Users/user/CareGist/_locations_detail.ndjson"),
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert events == []
    assert skipped == 3


def test_event_ordering_is_deterministic_by_date_then_provider_then_location():
    rows = [
        _registration_row("P2", "L2", "Beta House", "2026-02-20"),
        _registration_row("P1", "L1", "Alpha House", "2026-02-20"),
    ]

    events, _ = collect_events(
        rows,
        provider_names=_provider_names(),
        source_path=Path("/Users/user/CareGist/_locations_detail.ndjson"),
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )

    assert [event.provider_name for event in events] == ["Alpha Care Ltd", "Beta Care Ltd"]
    assert [event.location_name for event in events] == ["Alpha House", "Beta House"]


def test_zero_event_handling_renders_explicit_empty_window(tmp_path: Path):
    locations = tmp_path / "locations.ndjson"
    providers = tmp_path / "providers.ndjson"
    locations.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "providerId": "P1",
                        "locationId": "L1",
                        "name": "No Event Care",
                        "localAuthority": "Gloucestershire",
                        "region": "South West",
                        "currentRatings": {"overall": {"reportDate": "2026-02-20", "rating": "Good"}},
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    providers.write_text(json.dumps({"providerId": "P1", "name": "No Event Care Ltd"}) + "\n", encoding="utf-8")

    bundle = build_sample(locations_source=locations, providers_source=providers)
    rendered = render_markdown(bundle)

    assert bundle.selected_territory is None
    assert "No supported events found" in rendered
    assert "no supported new-registration or rating-change events" in rendered


def test_markdown_includes_required_headers_and_cta_placeholder():
    bundle = SampleBundle(
        generated_at=datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc),
        as_of_date=date(2026, 2, 20),
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        selection_rule="rule",
        selected_territory=None,
        territory_counts=[],
        events=[],
        source_paths={"locations_detail": "/Users/user/CareGist/_locations_detail.ndjson", "providers_detail": "/Users/user/CareGist/_providers_detail.ndjson"},
        rating_change_reason="reason",
        skipped_locations=0,
        zero_event_reason="No supported events were found.",
    )

    rendered = render_markdown(bundle)

    assert rendered.startswith("# DRAFT — not approved\n# INTERNAL SAMPLE — not for sending or publication")
    assert "[CTA PLACEHOLDER:" in rendered


def test_build_sample_is_deterministic_for_identical_inputs(tmp_path: Path):
    locations = tmp_path / "locations.ndjson"
    providers = tmp_path / "providers.ndjson"
    locations.write_text(
        json.dumps(_registration_row("P1", "L1", "Alpha House", "2026-02-20")) + "\n",
        encoding="utf-8",
    )
    providers.write_text(
        json.dumps({"providerId": "P1", "name": "Alpha Care Ltd"}) + "\n",
        encoding="utf-8",
    )

    first = build_sample(locations_source=locations, providers_source=providers)
    second = build_sample(locations_source=locations, providers_source=providers)

    assert first == second
    assert first.generated_at.isoformat() == "2026-02-20T00:00:00+00:00"
