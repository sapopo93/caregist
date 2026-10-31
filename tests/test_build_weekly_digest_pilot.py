from __future__ import annotations

from datetime import date

import pytest

from tools import build_weekly_digest_pilot as digest

WINDOW = digest.Window.ending(date(2026, 10, 19))


def _location(location_id, *, region="North West", status="Registered", rating="Good", report_date="2026-10-15"):
    return {
        "locationId": location_id,
        "name": f"Home {location_id}",
        "region": region,
        "localAuthority": "Manchester",
        "registrationStatus": status,
        "currentRatings": {"overall": {"rating": rating, "reportDate": report_date}},
    }


def test_window_is_seven_days_inclusive():
    assert WINDOW.start == date(2026, 10, 13)
    assert WINDOW.contains(date(2026, 10, 13)) and WINDOW.contains(date(2026, 10, 19))
    assert not WINDOW.contains(date(2026, 10, 12)) and not WINDOW.contains(date(2026, 10, 20))


def test_selects_only_registered_in_region_ratings_published_in_window():
    rows = [
        _location("1-in"),
        _location("1-other-region", region="London"),
        _location("1-deregistered", status="Deregistered"),
        _location("1-before", report_date="2026-10-12"),
        _location("1-after", report_date="2026-10-20"),
        _location("1-unrated", rating=None),
        {"locationId": "1-no-ratings", "region": "North West", "registrationStatus": "Registered"},
    ]

    selected = digest.select_published_ratings(rows, region="North West", window=WINDOW)

    assert [r["location_id"] for r in selected] == ["1-in"]
    assert selected[0]["published"] == "2026-10-15"
    assert selected[0]["cqc_url"] == "https://www.cqc.org.uk/location/1-in"


def test_report_date_at_current_ratings_level_is_honoured():
    row = _location("1-top")
    row["currentRatings"] = {"reportDate": "2026-10-14", "overall": {"rating": "Outstanding"}}

    assert digest.select_published_ratings([row], region="North West", window=WINDOW)[0]["rating"] == "Outstanding"


def test_pdf_renders_both_sections_and_states_sources():
    pdf = digest.render_pdf(
        region="North West",
        window=WINDOW,
        issue=1,
        customer="Buyer Ltd",
        registrations=[{"effective_date": date(2026, 10, 14), "name": "New Home", "local_authority": "Bolton", "service_types": "Homecare agencies"}],
        ratings=digest.select_published_ratings([_location("1-in")], region="North West", window=WINDOW),
        edition={"source_published_at": date(2026, 10, 14)},
        ratings_source_retrieved_at="2026-10-20T07:30:00+00:00",
    )
    assert pdf.startswith(b"%PDF")


def test_refuses_an_export_retrieved_before_the_window_closed(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    source = tmp_path / "locations.ndjson"
    source.write_text("", encoding="utf-8")

    code = digest.main([
        "--region", "North West", "--week-ending", "2026-10-19", "--issue", "1",
        "--customer", "Buyer Ltd", "--locations-source", str(source),
        "--source-retrieved-at", "2026-10-19T23:00:00+00:00", "--out-dir", str(tmp_path / "out"),
    ])

    assert code == 2
    assert "retrieved on or before" in capsys.readouterr().err


def test_rejects_unknown_region():
    with pytest.raises(SystemExit):
        digest.parse_args(["--region", "Narnia", "--week-ending", "2026-10-19", "--issue", "1",
                           "--customer", "x", "--locations-source", "x", "--source-retrieved-at", "x", "--out-dir", "x"])


def test_endings_distinguish_closure_candidate_from_successor_and_dormancy():
    rows = [
        {"locationId": "closed", "registrationStatus": "Deregistered", "region": "North West",
         "deregistrationDate": "2026-10-15", "name": "Closed", "postalCode": "M1 1AA"},
        {"locationId": "moved", "registrationStatus": "Deregistered", "region": "North West",
         "deregistrationDate": "2026-10-16", "relationships": [
             {"type": "HSCA Successor", "relatedLocationId": "new", "reason": "Location Move"}]},
        {"locationId": "dormant", "registrationStatus": "Deregistered", "region": "North West",
         "deregistrationDate": "2026-10-17", "dormancy": "Y"},
        {"locationId": "old", "registrationStatus": "Deregistered", "region": "North West",
         "deregistrationDate": "1999-01-01"},
        {"locationId": "elsewhere", "registrationStatus": "Deregistered", "region": "London",
         "deregistrationDate": "2026-10-17"},
    ]
    endings = digest.select_registration_endings(rows, region="North West", window=WINDOW)
    assert [(r["location_id"], r["classification"]) for r in endings] == [
        ("closed", "closure_candidate"), ("moved", "re_registration"), ("dormant", "dormant")]
    csv_bytes = digest.digest_csv_bytes([], [], endings)
    assert csv_bytes.count(b"registration_ended") == 3
    assert b"Location Move" in csv_bytes
