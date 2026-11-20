"""Operator History against a real Postgres: identity, history, refusals, determinism."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware import ip_rate_limit
from api.services import operator_history as oh
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio

MULTI = "1-1000001"
RENAMED = "1-1000002"
CLOSED = "1-1000003"
REINSTATED = "1-1000004"
NO_RATINGS = "1-1000005"
SHARED_A = "1-1000006"
SHARED_B = "1-1000007"
DISPUTED_LOCATION = "1-1000008"
DISPUTED_BY_EDITION = "1-1000009"
DISPUTED_RECORDED = "1-1000010"
DISPUTED_NAMES = "1-1000011"
NO_EDITION = "1-1000012"
NO_LOCATIONS = "1-1000013"
DISPUTED_LEDGER = "1-1000014"
UNKNOWN = "1-9999999"


def utc(y, m, d, h=9):
    return datetime(y, m, d, h, 0, tzinfo=timezone.utc)


async def add_location(conn, location_id, provider_id, *, name=None, status="ACTIVE", registered=date(2016, 1, 4),
                       services="Residential social care|Homecare"):
    await conn.execute(
        """INSERT INTO care_providers (id, provider_id, name, slug, status, registration_date, service_types,
                                       ownership_type, region, local_authority)
           VALUES ($1, $2, $3, $4, $5, $6, $7, 'Organisation', 'Test Region', 'Testshire')""",
        location_id, provider_id, name or f"Location {location_id}", f"slug-{location_id}", status, registered, services,
    )


async def add_rating(conn, location_id, rating, inspected, recorded, url=None):
    await conn.execute(
        """INSERT INTO provider_rating_history (provider_id, overall_rating, inspection_date, report_url, recorded_at)
           VALUES ($1, $2, $3, $4, $5)""",
        location_id, rating, inspected, url or f"https://www.cqc.org.uk/location/{location_id}/reports/{inspected}", recorded,
    )


_event_counter = 0


async def add_ledger(conn, event_type, location_id, provider_id, old, new, observed, *, source_url=None):
    global _event_counter
    _event_counter += 1
    await conn.execute(
        """INSERT INTO trusted_event_ledger (entity_type, entity_id, provider_id, location_id, event_type, effective_date,
                                             observed_at, old_value, new_value, source, dedupe_key, source_url)
           VALUES ('location', $1::text, $2, $1::varchar, $3, NULL, $4, $5::jsonb, $6::jsonb, 'test', $7, $8)""",
        location_id, provider_id, event_type, observed,
        None if old is None else json.dumps(old), None if new is None else json.dumps(new),
        f"test:{event_type}:{location_id}:{_event_counter}", source_url,
    )


async def add_edition(conn, retrieved, rows, tag):
    """One immutable edition: rows are (location_id, provider_id, provider_name)."""
    async with conn.transaction():
        edition_id = await conn.fetchval(
            """INSERT INTO territory_brief_source_editions
               (source_retrieved_at, source_as_of, locations_sha256, providers_sha256, location_count)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            retrieved, retrieved.date(), (tag + "l").encode().hex().ljust(64, "0")[:64],
            (tag + "p").encode().hex().ljust(64, "0")[:64], len(rows),
        )
        for location_id, provider_id, provider_name in rows:
            await conn.execute(
                """INSERT INTO territory_brief_source_locations
                   (edition_id, location_id, local_authority, region, provider_name, payload)
                   VALUES ($1, $2, 'Testshire', 'Test Region', $3, $4::jsonb)""",
                edition_id, location_id, provider_name,
                json.dumps({"locationId": location_id, "providerId": provider_id}),
            )
    return edition_id


async def seed_world(conn):
    # MULTI: three locations, ratings on two, an ownership artefact row on each.
    await add_location(conn, "1-L-A", MULTI, name="Alpha House", registered=date(2015, 6, 1))
    await add_location(conn, "1-L-B", MULTI, name="Alpha Court", registered=date(2018, 2, 20), services="Homecare")
    await add_location(conn, "1-L-C", MULTI, name="Alpha Lodge", registered=date(2022, 9, 5))
    await add_rating(conn, "1-L-A", "Good", date(2019, 5, 1), utc(2026, 3, 31))
    await add_rating(conn, "1-L-A", "Requires improvement", date(2023, 3, 10), utc(2026, 4, 2))
    await add_rating(conn, "1-L-B", "Outstanding", date(2021, 7, 14), utc(2026, 4, 2))
    await add_rating(conn, "1-L-B", "Not Yet Inspected", date(2022, 1, 1), utc(2026, 4, 3))
    for loc in ("1-L-A", "1-L-B", "1-L-C"):
        # Seeding artefact: old value is a category, new value is empty. Never history.
        await add_ledger(conn, "ownership_changed", loc, MULTI, "Organisation", None, utc(2026, 8, 10))
    # RENAMED: one location, two editions with different names.
    await add_location(conn, "2-L-A", RENAMED, name="Beta Road", registered=date(2012, 4, 1))
    # CLOSED: an INACTIVE location with an observation, one with none, one ACTIVE.
    await add_location(conn, "3-L-X", CLOSED, name="Closed House", status="INACTIVE", registered=date(2014, 3, 3))
    await add_location(conn, "3-L-Z", CLOSED, name="Older Absent House", status="INACTIVE", registered=date(2011, 1, 1))
    await add_location(conn, "3-L-Y", CLOSED, name="Open House", registered=date(2019, 8, 8))
    await add_ledger(conn, "status_changed", "3-L-X", CLOSED, "ACTIVE", "INACTIVE", utc(2026, 8, 12),
                     source_url="https://api.service.cqc.org.uk/public/v1/locations/3-L-X")
    await add_rating(conn, "3-L-X", "Good", date(2020, 1, 15), utc(2026, 4, 5))
    # REINSTATED: absent then back.
    await add_location(conn, "4-L-R", REINSTATED, name="Returned House", registered=date(2017, 5, 5))
    await add_ledger(conn, "status_changed", "4-L-R", REINSTATED, "ACTIVE", "INACTIVE", utc(2026, 8, 12))
    await add_ledger(conn, "status_changed", "4-L-R", REINSTATED, "INACTIVE", "ACTIVE", utc(2026, 9, 3))
    # NO_RATINGS: nothing in provider_rating_history.
    await add_location(conn, "5-L-A", NO_RATINGS, name="Unrated House", registered=date(2025, 11, 1))
    # Two operators that share one legal name.
    await add_location(conn, "6-L-A", SHARED_A, registered=date(2013, 1, 1))
    await add_location(conn, "7-L-A", SHARED_B, registered=date(2014, 1, 1))
    await add_location(conn, "7-L-B", SHARED_B, registered=date(2015, 1, 1))
    # Disputed: CareGist holds the location under 8, an edition lists it under 9.
    await add_location(conn, "8-L-A", DISPUTED_LOCATION, registered=date(2010, 4, 1))
    await add_location(conn, "10-L-A", DISPUTED_RECORDED, registered=date(2010, 4, 1))
    await add_location(conn, "11-L-A", DISPUTED_NAMES, registered=date(2010, 4, 1))
    await add_location(conn, "11-L-B", DISPUTED_NAMES, registered=date(2010, 4, 1))
    await add_location(conn, "12-L-A", NO_EDITION, registered=date(2010, 4, 1))
    await add_location(conn, "14-L-A", DISPUTED_LEDGER, registered=date(2010, 4, 1))
    await add_ledger(conn, "status_changed", "14-L-A", "1-7777777", "ACTIVE", "INACTIVE", utc(2026, 8, 20))
    await conn.execute(
        "INSERT INTO operator_identity_disputes (provider_id, reason) VALUES ($1, 'Owner flagged: two registrations')",
        DISPUTED_RECORDED,
    )

    e1 = [
        ("1-L-A", MULTI, "Alpha Care Ltd"), ("1-L-B", MULTI, "Alpha Care Ltd"), ("1-L-C", MULTI, "Alpha Care Ltd"),
        ("2-L-A", RENAMED, "Beta Homes Ltd"),
        ("3-L-X", CLOSED, "Delta Living Ltd"), ("3-L-Z", CLOSED, "Delta Living Ltd"), ("3-L-Y", CLOSED, "Delta Living Ltd"),
        ("4-L-R", REINSTATED, "Epsilon Care Ltd"),
        ("5-L-A", NO_RATINGS, "Zeta Support Ltd"),
        ("6-L-A", SHARED_A, "Gamma Care Ltd"),
        ("7-L-A", SHARED_B, "Gamma Care Ltd"), ("7-L-B", SHARED_B, "Gamma Care Ltd"),
        ("8-L-A", DISPUTED_BY_EDITION, "Eta Care Ltd"),
        ("10-L-A", DISPUTED_RECORDED, "Theta Care Ltd"),
        ("11-L-A", DISPUTED_NAMES, "Iota Care Ltd"), ("11-L-B", DISPUTED_NAMES, "Iota Care Limited"),
        ("14-L-A", DISPUTED_LEDGER, "Kappa Care Ltd"),
        ("13-L-A", NO_LOCATIONS, "Lambda Care Ltd"),
    ]
    await add_edition(conn, utc(2026, 9, 1), e1, "e1")
    await add_edition(conn, utc(2026, 10, 15), [("2-L-A", RENAMED, "Beta Homes Group Ltd")], "e2")


@pytest.fixture
async def world(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    await apply_full_schema(conn)
    await seed_world(conn)
    ip_rate_limit._public_ip_requests.clear()
    yield conn, fresh_db
    await conn.close()


async def refusal_code(conn, **kwargs):
    with pytest.raises(oh.OperatorRefusal) as excinfo:
        await oh.coverage_preview(conn, **kwargs)
    return excinfo.value


# --- the multi-location operator ---------------------------------------------


async def test_multi_location_operator_record_is_sorted_dated_and_sourced(world):
    conn, _ = world
    record = await oh.build_operator_history(conn, await oh.resolve_operator(conn, provider_id=MULTI))
    assert record["provider_id"] == MULTI
    assert record["provider"]["legal_name"] == "Alpha Care Ltd"
    assert record["provider"]["edition"]["retrieved_on"] == "2026-09-01"
    assert len(record["provider"]["edition"]["providers_sha256"]) == 64
    assert [loc["location_id"] for loc in record["locations"]] == ["1-L-A", "1-L-B", "1-L-C"]
    first = record["locations"][0]
    assert first["registration_date"] == "2015-06-01"
    assert first["registration_source"]["label"] == "CQC registration date"
    assert first["registration_source"]["url"].endswith("/location/1-L-A")
    assert [r["inspection_date"] for r in first["rating_history"]] == ["2019-05-01", "2023-03-10"]
    assert [r["rating"] for r in first["rating_history"]] == ["Good", "Requires improvement"]
    assert all(r["source"]["url"].startswith("https://www.cqc.org.uk/") for r in first["rating_history"])
    assert record["locations"][1]["service_types"] == ["Homecare"]
    assert record["events"] == sorted(record["events"], key=lambda e: (e["date"], oh.EVENT_ORDER[e["kind"]], e["location_id"]))
    assert {e["kind"] for e in record["events"]} == {"registration", "rating_published"}
    assert all(e["source"]["label"] for e in record["events"])
    summary = record["summary"]
    assert (summary["locations_total"], summary["on_active_directory"], summary["no_longer_on_active_directory"]) == (3, 3, 0)
    assert (summary["earliest_registration_date"], summary["latest_registration_date"]) == ("2015-06-01", "2022-09-05")
    assert summary["rating_records"] == 4


async def test_sentinel_rating_text_is_listed_as_quoted_but_never_an_event(world):
    conn, _ = world
    record = await oh.build_operator_history(conn, await oh.resolve_operator(conn, provider_id=MULTI))
    court = record["locations"][1]
    sentinel = [r for r in court["rating_history"] if r["rating"] == "Not Yet Inspected"]
    assert len(sentinel) == 1 and sentinel[0]["is_published_rating"] is False
    published = [e for e in record["events"] if e["kind"] == "rating_published" and e["location_id"] == "1-L-B"]
    assert [e["rating"] for e in published] == ["Outstanding"]


async def test_ownership_artefact_rows_never_appear_as_history(world):
    conn, _ = world
    assert await conn.fetchval("SELECT count(*) FROM trusted_event_ledger WHERE event_type = 'ownership_changed'") == 3
    record = await oh.build_operator_history(conn, await oh.resolve_operator(conn, provider_id=MULTI))
    blob = json.dumps(record).lower()
    assert "ownership" not in blob
    assert "organisation" not in blob
    assert all(e["kind"] in {"registration", "closure_observed", "reinstatement_observed", "rating_published"} for e in record["events"])


# --- renamed operator ---------------------------------------------------------


async def test_renamed_operator_shows_latest_name_and_lists_the_earlier_one_with_its_edition_date(world):
    conn, _ = world
    preview = await oh.coverage_preview(conn, provider_id=RENAMED)
    assert preview["legal_name"] == "Beta Homes Group Ltd"
    assert preview["edition"]["retrieved_on"] == "2026-10-15"
    assert preview["earlier_names"] == [
        {"name": "Beta Homes Ltd", "first_edition_retrieved_on": "2026-09-01", "last_edition_retrieved_on": "2026-09-01"}
    ]
    assert any("before 1 September 2026" in line for line in preview["limits"])


async def test_an_earlier_name_still_finds_the_operator_by_name(world):
    conn, _ = world
    preview = await oh.coverage_preview(conn, name="beta homes ltd")
    assert preview["provider_id"] == RENAMED and preview["legal_name"] == "Beta Homes Group Ltd"


# --- closures and reinstatements ---------------------------------------------


async def test_closure_is_first_observed_never_a_deregistration_date(world):
    conn, _ = world
    record = await oh.build_operator_history(conn, await oh.resolve_operator(conn, provider_id=CLOSED))
    by_id = {loc["location_id"]: loc for loc in record["locations"]}
    closed = by_id["3-L-X"]["status"]
    assert closed["state"] == "no_longer_on_active_directory"
    assert closed["first_observed_absent_on"] == "2026-08-12"
    assert closed["observations"][0]["source"]["url"].endswith("/locations/3-L-X")
    closures = [e for e in record["events"] if e["kind"] == "closure_observed"]
    assert [(e["date"], e["location_id"]) for e in closures] == [("2026-08-12", "3-L-X")]
    assert "not CQC's deregistration date" in closures[0]["text"]
    blob = json.dumps(record).lower()
    assert "deregistration_date" not in blob and "deregistered_on" not in blob
    # Absent before CareGist started observing: no date is invented.
    older = by_id["3-L-Z"]["status"]
    assert older["state"] == "no_longer_on_active_directory"
    assert older["first_observed_absent_on"] is None and older["observations"] == []
    assert by_id["3-L-Y"]["status"]["state"] == "on_active_directory"
    summary = record["summary"]
    assert (summary["on_active_directory"], summary["no_longer_on_active_directory"]) == (1, 2)
    assert (summary["closures_observed"], summary["first_closure_observed_on"]) == (1, "2026-08-12")
    # The ledger-wide first status observation is 12 August 2026; ownership artefact rows (10 August) do not count.
    assert any("began recording changes to a location's status on 12 August 2026" in line for line in record["limits"])


async def test_reinstated_location_shows_closure_then_reinstatement(world):
    conn, _ = world
    record = await oh.build_operator_history(conn, await oh.resolve_operator(conn, provider_id=REINSTATED))
    loc = record["locations"][0]
    assert loc["status"]["state"] == "on_active_directory"
    assert loc["status"]["first_observed_absent_on"] == "2026-08-12"
    assert loc["status"]["latest_reinstatement_observed_on"] == "2026-09-03"
    assert [(e["kind"], e["date"]) for e in record["events"]] == [
        ("registration", "2017-05-05"), ("closure_observed", "2026-08-12"), ("reinstatement_observed", "2026-09-03"),
    ]
    assert "back on CQC's active directory" in record["events"][2]["text"]
    preview = await oh.coverage_preview(conn, provider_id=REINSTATED)
    assert (preview["status_changes"]["closures_observed"], preview["status_changes"]["reinstatements_observed"]) == (1, 1)
    assert preview["history_cutoff"] == "2026-09-03"


async def test_operator_with_no_rating_history(world):
    conn, _ = world
    preview = await oh.coverage_preview(conn, provider_id=NO_RATINGS)
    assert preview["ratings"] == {"records": 0, "earliest_inspection_date": None, "latest_inspection_date": None}
    assert oh.LIMIT_RATING_NONE in preview["limits"]
    assert preview["history_cutoff"] is None and oh.LIMIT_CUTOFF_NONE in preview["limits"]


async def test_preview_carries_the_limits_and_no_completeness_or_risk_wording(world):
    conn, _ = world
    for provider_id in (MULTI, RENAMED, CLOSED, REINSTATED, NO_RATINGS):
        preview = await oh.coverage_preview(conn, provider_id=provider_id)
        assert preview["limits"][0] == oh.LIMIT_CLOSURE
        assert oh.LIMIT_LOCATIONS in preview["limits"]
        assert any("Closure dates are the date CareGist first observed" in line for line in preview["limits"])
        text = " ".join(preview["limits"]).lower()
        assert [b for b in ("every location", "complete", "all history", "risk", "score") if b in text] == []
        assert set(preview) == {
            "provider_id", "legal_name", "edition", "earlier_names", "locations", "registrations", "ratings",
            "status_changes", "history_cutoff", "limits",
        }


async def test_multi_preview_counts_dates_and_cutoff(world):
    conn, _ = world
    preview = await oh.coverage_preview(conn, provider_id=MULTI)
    assert preview["locations"] == {"total": 3, "on_active_directory": 3, "no_longer_on_active_directory": 0, "status_not_held": 0}
    assert preview["registrations"] == {"earliest": "2015-06-01", "latest": "2022-09-05"}
    assert preview["ratings"] == {"records": 4, "earliest_inspection_date": "2019-05-01", "latest_inspection_date": "2023-03-10"}
    # Rating history was first recorded on 31 March 2026 and last recorded on 3 April 2026.
    assert preview["history_cutoff"] == "2026-04-03"
    assert any("from 31 March 2026" in line for line in preview["limits"])
    assert any("up to 3 April 2026" in line for line in preview["limits"])


async def test_observed_through_leaves_out_later_observations(world):
    conn, _ = world
    preview = await oh.coverage_preview(conn, provider_id=REINSTATED, observed_through=date(2026, 8, 31))
    assert preview["status_changes"]["reinstatements_observed"] == 0
    assert preview["status_changes"]["closures_observed"] == 1
    assert preview["history_cutoff"] == "2026-08-31"


# --- refusals -----------------------------------------------------------------


async def test_shared_name_is_ambiguous_and_never_auto_picked(world):
    conn, _ = world
    for name in ("Gamma Care Ltd", "gamma care", "Gamma"):
        refusal = await refusal_code(conn, name=name)
        assert refusal.code == "ambiguous" and refusal.http_status == 409
        assert refusal.total_matches == 2
        assert refusal.candidates == [
            {"provider_id": SHARED_B, "name": "Gamma Care Ltd", "location_count": 2},
            {"provider_id": SHARED_A, "name": "Gamma Care Ltd", "location_count": 1},
        ]
        assert all(set(c) == {"provider_id", "name", "location_count"} for c in refusal.candidates)
    # Choosing by Provider ID resolves it.
    assert (await oh.coverage_preview(conn, provider_id=SHARED_A))["legal_name"] == "Gamma Care Ltd"


async def test_ambiguity_lists_at_most_ten_candidates(world):
    conn, _ = world
    for index in range(12):
        provider_id = f"1-20000{index:02d}"
        await add_location(conn, f"x-{index}", provider_id)
        await add_edition(conn, utc(2026, 10, 20, 8 + index % 10), [(f"x-{index}", provider_id, f"Sigma Trust {index}")], f"sig{index}")
    refusal = await refusal_code(conn, name="Sigma Trust")
    assert refusal.code == "ambiguous"
    assert refusal.total_matches == 12 and len(refusal.candidates) == 10


async def test_unknown_provider_id_is_not_found(world):
    conn, _ = world
    assert (await refusal_code(conn, provider_id=UNKNOWN)).code == "not_found"
    assert (await refusal_code(conn, name="Nobody Has This Name")).code == "not_found"


async def test_disputed_identity_is_refused_from_every_side(world):
    conn, _ = world
    # CareGist holds the location under 8; the edition lists it under 9.
    for provider_id in (DISPUTED_LOCATION, DISPUTED_BY_EDITION):
        refusal = await refusal_code(conn, provider_id=provider_id)
        assert refusal.code == "identity_disputed", provider_id
        assert "location_under_another_provider_id" in refusal.reasons
    recorded = await refusal_code(conn, provider_id=DISPUTED_RECORDED)
    assert recorded.code == "identity_disputed" and "recorded_dispute" in recorded.reasons
    names = await refusal_code(conn, provider_id=DISPUTED_NAMES)
    assert names.code == "identity_disputed" and "edition_names_conflict" in names.reasons
    ledger = await refusal_code(conn, provider_id=DISPUTED_LEDGER)
    assert ledger.code == "identity_disputed" and "observation_under_another_provider_id" in ledger.reasons
    # A name that resolves to a disputed operator is refused the same way.
    assert (await refusal_code(conn, name="Theta Care Ltd")).code == "identity_disputed"
    # Resolving the dispute lifts the refusal.
    await conn.execute("UPDATE operator_identity_disputes SET resolved_at = NOW() WHERE provider_id = $1", DISPUTED_RECORDED)
    assert (await oh.coverage_preview(conn, provider_id=DISPUTED_RECORDED))["legal_name"] == "Theta Care Ltd"


async def test_provider_without_a_held_name_is_refused(world):
    conn, _ = world
    refusal = await refusal_code(conn, provider_id=NO_EDITION)
    assert refusal.code == "no_legal_name_held"


async def test_operator_with_no_locations_is_refused(world):
    conn, _ = world
    assert (await refusal_code(conn, provider_id=NO_LOCATIONS)).code == "not_enough_history"


async def test_no_edition_held_at_all_refuses_by_id_and_by_name(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await add_location(conn, "9-L-A", "1-3000001", name="Only Location")
        assert await conn.fetchval("SELECT count(*) FROM territory_brief_source_editions") == 0
        assert (await refusal_code(conn, provider_id="1-3000001")).code == "no_legal_name_held"
        by_name = await refusal_code(conn, name="Only Location")
        assert by_name.code == "no_legal_name_held"
        assert "does not hold a CQC provider name" in by_name.message
        assert (await refusal_code(conn, provider_id=UNKNOWN)).code == "not_found"
    finally:
        await conn.close()


async def test_invalid_input_never_reaches_the_database(world):
    conn, _ = world
    for kwargs in ({}, {"provider_id": MULTI, "name": "Alpha Care"}, {"provider_id": "1-1' OR '1'='1"}, {"name": "ab"}):
        assert (await refusal_code(conn, **kwargs)).code == "invalid_input"


@pytest.mark.parametrize("hostile", [
    "Robert'); DROP TABLE care_providers;--", "' OR '1'='1", "\" OR \"\"=\"", "%%%", "___", "\\\\\\", "a%' OR 1=1 --", "Alpha Care Ltd'; --",
])
async def test_sql_metacharacters_in_a_name_are_only_data(world, hostile):
    conn, _ = world
    before = await conn.fetchval("SELECT count(*) FROM care_providers")
    refusal = await refusal_code(conn, name=hostile)
    assert refusal.code == "not_found"  # wildcards are literal: nothing matches, nothing is returned
    assert await conn.fetchval("SELECT count(*) FROM care_providers") == before


async def test_name_search_does_not_match_a_different_name_through_wildcards(world):
    conn, _ = world
    # '_' and '%' are literal: "Alpha_Care" must not match "Alpha Care Ltd".
    assert (await refusal_code(conn, name="Alpha_Care")).code == "not_found"
    assert (await oh.coverage_preview(conn, name="Alpha Care"))["provider_id"] == MULTI


# --- determinism --------------------------------------------------------------


async def seed_fixed_operator(conn, order):
    """The same data inserted in a given order; serial ids differ between orders."""
    steps = {
        "locations": lambda: _locations(conn, order),
        "ratings": lambda: _ratings(conn, order),
        "events": lambda: _events(conn, order),
        "edition": lambda: add_edition(conn, utc(2026, 9, 1), [("d-L-1", "1-4000001", "Order Test Ltd"), ("d-L-2", "1-4000001", "Order Test Ltd")], "ord"),
    }
    for name in (["locations", "edition", "ratings", "events"] if order == "forward" else ["edition", "locations", "events", "ratings"]):
        await steps[name]()


async def _locations(conn, order):
    rows = [("d-L-1", date(2015, 1, 1), "ACTIVE"), ("d-L-2", date(2016, 2, 2), "INACTIVE")]
    for location_id, registered, status in (rows if order == "forward" else list(reversed(rows))):
        await add_location(conn, location_id, "1-4000001", registered=registered, status=status)


async def _ratings(conn, order):
    rows = [("d-L-1", "Good", date(2019, 1, 1), utc(2026, 4, 1)), ("d-L-1", "Outstanding", date(2022, 1, 1), utc(2026, 4, 1)),
            ("d-L-2", "Inadequate", date(2020, 1, 1), utc(2026, 4, 2))]
    for row in (rows if order == "forward" else list(reversed(rows))):
        await add_rating(conn, *row)


async def _events(conn, order):
    rows = [("d-L-2", "ACTIVE", "INACTIVE", utc(2026, 9, 1)), ("d-L-1", "ACTIVE", "INACTIVE", utc(2026, 9, 2)),
            ("d-L-1", "INACTIVE", "ACTIVE", utc(2026, 9, 3))]
    for loc, old, new, when in (rows if order == "forward" else list(reversed(rows))):
        await add_ledger(conn, "status_changed", loc, "1-4000001", old, new, when)


async def test_same_data_gives_the_same_hash_whatever_the_insert_order(world):
    conn, _ = world
    hashes = []
    for order in ("forward", "reverse"):
        tx = conn.transaction()
        await tx.start()
        try:
            await seed_fixed_operator(conn, order)
            operator = await oh.resolve_operator(conn, provider_id="1-4000001")
            first = await oh.build_operator_history(conn, operator)
            again = await oh.build_operator_history(conn, operator)
            assert first == again
            assert first["content_sha256"] == oh.content_sha256(first)
            hashes.append(first["content_sha256"])
        finally:
            await tx.rollback()
    assert hashes[0] == hashes[1] and len(hashes[0]) == 64


async def test_hash_changes_when_the_data_changes_and_carries_no_serial_ids(world):
    conn, _ = world
    operator = await oh.resolve_operator(conn, provider_id=MULTI)
    before = await oh.build_operator_history(conn, operator)
    await add_rating(conn, "1-L-C", "Good", date(2024, 2, 2), utc(2026, 5, 1))
    after = await oh.build_operator_history(conn, operator)
    assert before["content_sha256"] != after["content_sha256"]
    blob = json.dumps(after)
    assert "generated" not in blob and '"id"' not in blob and "edition_id" not in blob


# --- the router over the real schema -----------------------------------------


async def http_get(conn, path, *, enabled=True):
    @asynccontextmanager
    async def factory():
        yield conn

    with patch("api.routers.operator_history.get_connection", factory), \
         patch("api.routers.operator_history.settings.operator_history_enabled", enabled):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            return await client.get(path)


async def test_route_serves_the_preview_when_enabled_and_404s_when_off(world):
    conn, _ = world
    ok = await http_get(conn, f"/api/v1/operator-history/coverage?provider_id={MULTI}")
    assert ok.status_code == 200
    body = ok.json()
    assert body["legal_name"] == "Alpha Care Ltd" and body["locations"]["total"] == 3
    assert "locations_list" not in body and "events" not in body
    off = await http_get(conn, f"/api/v1/operator-history/coverage?provider_id={MULTI}", enabled=False)
    unknown = await http_get(conn, "/api/v1/operator-history/nothing", enabled=False)
    assert off.status_code == 404 and (off.status_code, off.json()) == (unknown.status_code, unknown.json())


async def test_route_refusals_carry_stable_codes_and_no_other_operators_data(world):
    conn, _ = world
    amb = await http_get(conn, "/api/v1/operator-history/coverage?name=Gamma%20Care")
    assert amb.status_code == 409
    detail = amb.json()["detail"]
    assert detail["code"] == "ambiguous"
    assert all(set(c) == {"provider_id", "name", "location_count"} for c in detail["candidates"])
    for leaked in ("registration_date", "inspection_date", "report_url", "locations_list", "1-L-A", "7-L-A"):
        assert leaked not in amb.text
    for query, status, code in [
        (f"provider_id={UNKNOWN}", 404, "not_found"),
        (f"provider_id={DISPUTED_RECORDED}", 409, "identity_disputed"),
        (f"provider_id={NO_EDITION}", 409, "no_legal_name_held"),
        (f"provider_id={NO_LOCATIONS}", 409, "not_enough_history"),
        ("provider_id=1-12", 422, "invalid_input"),
        ("name=%27%3B%20DROP%20TABLE%20care_providers%3B--", 404, "not_found"),
    ]:
        resp = await http_get(conn, f"/api/v1/operator-history/coverage?{query}")
        assert (resp.status_code, resp.json()["detail"]["code"]) == (status, code), query
        assert resp.json()["detail"]["message"] == oh.REFUSAL_MESSAGES[code]
    assert await conn.fetchval("SELECT count(*) FROM care_providers") > 0


# --- names bound through the real importer ------------------------------------


async def test_names_come_from_editions_written_by_the_real_importer(fresh_db, tmp_path):
    import psycopg2

    from tools.import_territory_brief_source import import_edition

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        provider_id = "1-5000001"
        await add_location(conn, "5-I-A", provider_id, name="Importer House", registered=date(2018, 1, 1))
        await add_location(conn, "5-I-B", provider_id, name="Importer Court", registered=date(2019, 1, 1))

        def snapshot(label, folder):
            folder.mkdir()
            locations = folder / "locations.jsonl"
            providers = folder / "providers.jsonl"
            locations.write_text("\n".join(json.dumps({
                "locationId": lid, "providerId": provider_id, "name": f"Location {lid}", "localAuthority": "Testshire",
                "region": "Test Region", "registrationDate": "2018-01-01",
            }) for lid in ("5-I-A", "5-I-B")))
            providers.write_text(json.dumps({"providerId": provider_id, "name": label}))
            return locations, providers

        sync = psycopg2.connect(fresh_db)
        try:
            for label, when, folder in (("Importer Care Ltd", datetime(2026, 11, 1, tzinfo=timezone.utc), tmp_path / "one"),
                                        ("Importer Care Group Ltd", datetime(2026, 11, 10, tzinfo=timezone.utc), tmp_path / "two")):
                locations, providers = snapshot(label, folder)
                import_edition(sync, locations, providers, when)
        finally:
            sync.close()
        preview = await oh.coverage_preview(conn, provider_id=provider_id)
        assert preview["legal_name"] == "Importer Care Group Ltd"
        assert preview["edition"]["retrieved_on"] == "2026-11-10"
        assert [n["name"] for n in preview["earlier_names"]] == ["Importer Care Ltd"]
        assert preview["locations"]["total"] == 2
        assert (await oh.coverage_preview(conn, name="importer care ltd"))["provider_id"] == provider_id
    finally:
        await conn.close()
