"""Free Territory Brief preview: flag gate, quarantine guard, response honesty and limits.

Fixtures mirror production shapes found in review (19 Oct 2026): service types
stored as CQC labels such as "Domiciliary care service", rating_changed events
without an effective_date, and a PARTIAL freshness status.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.config import Settings
from api.main import app
from api.middleware import ip_rate_limit
from api.queries import territory_preview as q
from api.routers import territory_preview as router_mod
from api.service_taxonomy import resolve_service_filter
from api.services.territory_preview import (
    PreviewScope,
    build_preview,
    pick_examples,
    rating_availability,
    reason_for,
    window_for,
)

WINDOW_END = date(2026, 10, 16)
FRESH = {"status": "fresh", "sourcePublishedAt": "2026-10-14", "reconciledAt": "2026-10-18T01:06:48Z", "message": "ok"}
PARTIAL = {
    "status": "partial",
    "sourcePublishedAt": "2026-10-14",
    "reconciledAt": "2026-10-18T01:06:48Z",
    "message": "Freshness cannot currently be confirmed.",
}


def _event(kind, day, loc, provider, *, old=None, new=None, services="Domiciliary care service"):
    return {
        "event_type": kind,
        "event_date": day,
        "old_value": old,
        "new_value": new,
        "location_id": loc,
        "provider_id": provider,
        "name": f"Location {loc}",
        "town": "Coventry",
        "service_types": services,
    }


EVENTS = [
    _event("new_registration", date(2026, 10, 1), "1-001", "P1"),
    _event("new_registration", date(2026, 9, 20), "1-002", "P1"),  # same provider as 1-001
    _event("new_registration", date(2026, 8, 2), "1-003", "P2"),
    _event("rating_changed", date(2026, 9, 30), "1-004", "P3", old="Requires improvement", new="Good"),
]
SCOPE_ROW = {"organisations": 4260, "locations": 5100, "canonical_name": "West Midlands"}
COUNTS_DATED = {
    "new_registrations": 900,
    "rating_changes_dated": 640,
    "rating_changes_undated": 0,
    "organisations_with_signals": 1200,
}


@pytest.fixture(autouse=True)
def _reset_state():
    ip_rate_limit._public_ip_requests.clear()
    router_mod._cache.clear()
    yield
    ip_rate_limit._public_ip_requests.clear()
    router_mod._cache.clear()


REV = "3:2026-10-18 01:06:48+00"


def _conn(*, quarantine=True, scope_row=SCOPE_ROW, counts=COUNTS_DATED, regs=None, ratings=None, territories=None):
    conn = AsyncMock()
    if territories is not None:
        conn.fetchval = AsyncMock(side_effect=[quarantine, REV] if quarantine else [False])
    else:
        conn.fetchval = AsyncMock(side_effect=[quarantine, REV, WINDOW_END] if quarantine else [False])
    conn.fetchrow = AsyncMock(side_effect=[scope_row, counts])
    if territories is not None:
        conn.fetch = AsyncMock(return_value=territories)
    else:
        conn.fetch = AsyncMock(side_effect=[regs or [], ratings or []])

    @asynccontextmanager
    async def get_connection():
        yield conn

    return conn, get_connection


async def _get(path, conn_factory, enabled=True, freshness=FRESH):
    with patch("api.routers.territory_preview.get_connection", conn_factory), \
         patch("api.routers.territory_preview.get_cqc_freshness", AsyncMock(return_value=freshness)), \
         patch("api.routers.territory_preview.settings.territory_preview_enabled", enabled):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            return await client.get(path)


WM_HOMECARE = "/api/v1/territory-preview?kind=region&name=west%20midlands&service=homecare"


# --- gates ------------------------------------------------------------------


def test_preview_flag_defaults_off():
    cfg = Settings(database_url="postgresql://localhost/x", api_master_key="m", support_internal_token="s")
    assert cfg.territory_preview_enabled is False


@pytest.mark.parametrize("path", [WM_HOMECARE, "/api/v1/territory-preview/territories"])
async def test_closed_flag_returns_404_and_reads_nothing(path):
    conn, factory = _conn()
    resp = await _get(path, factory, enabled=False)
    assert resp.status_code == 404
    conn.fetchval.assert_not_called()
    conn.fetch.assert_not_called()


@pytest.mark.parametrize("path", [WM_HOMECARE, "/api/v1/territory-preview/territories"])
async def test_missing_quarantine_table_fails_closed(path):
    conn, factory = _conn(quarantine=False)
    resp = await _get(path, factory)
    assert resp.status_code == 503
    conn.fetchrow.assert_not_called()
    conn.fetch.assert_not_called()


def test_every_scope_query_excludes_unresolved_quarantine():
    for sql in (
        q.TERRITORIES,
        q.LATEST_REGISTRATION,
        q.scope_counts("region"),
        q.signal_counts("region"),
        q.new_registration_examples("region"),
        q.rating_change_examples("local_authority"),
    ):
        assert "reconciliation_quarantined_locations" in sql
        assert "resolved_at IS NULL" in sql


# --- taxonomy ---------------------------------------------------------------


def test_service_keys_resolve_to_stored_cqc_labels():
    expected = {
        "homecare": "domiciliary care service",
        "residential": "care home service without nursing",
        "nursing": "care home service with nursing",
        "supported_living": "supported living service",
    }
    for key, stored_label in expected.items():
        assert stored_label in resolve_service_filter(q.SERVICE_SLUGS[key])


async def test_service_filter_binds_canonical_aliases_not_display_labels():
    conn, factory = _conn()
    resp = await _get(WM_HOMECARE, factory)
    assert resp.status_code == 200
    sql, name, aliases = conn.fetchrow.call_args_list[0].args
    assert name == "west midlands" and "west midlands" not in sql
    assert "domiciliary care service" in aliases
    assert resp.json()["scope"]["service_label"] == "Home Care"


# --- honest counts ----------------------------------------------------------


async def test_totals_come_from_uncapped_aggregates_not_example_rows():
    regs = [e for e in EVENTS if e["event_type"] == "new_registration"]
    ratings = [e for e in EVENTS if e["event_type"] == "rating_changed"]
    conn, factory = _conn(regs=regs, ratings=ratings)
    body = (await _get(WM_HOMECARE, factory)).json()
    assert body["signals"]["new_registrations"] == 900
    assert body["signals"]["rating_changes"] == {"status": "available", "count": 640, "undated": 0}
    assert body["signals"]["organisations_with_signals"] == 1200
    assert (body["organisations"], body["locations"]) == (4260, 5100)
    assert body["window"] == {"start": "2026-07-19", "end": "2026-10-16", "days": 90}
    assert len(body["examples"]) == 3
    assert {e["provider_id"] for e in body["examples"]} == {"P1", "P2", "P3"}
    assert body["examples"][0]["source_url"] == "https://www.cqc.org.uk/location/1-004"
    for sql in (q.new_registration_examples("region"), q.rating_change_examples("region")):
        assert f"LIMIT {q.EXAMPLE_LIMIT}" in sql
    assert "LIMIT" not in q.signal_counts("region")


async def test_undated_rating_changes_are_unavailable_not_zero():
    counts = {**COUNTS_DATED, "rating_changes_dated": 0, "rating_changes_undated": 34332}
    conn, factory = _conn(counts=counts, regs=EVENTS[:3])
    body = (await _get(WM_HOMECARE, factory)).json()
    ratings = body["signals"]["rating_changes"]
    assert ratings["status"] == "unavailable"
    assert ratings["count"] is None
    assert any("cannot be counted" in c for c in body["caveats"])
    assert all(e["signal"] == "new_registration" for e in body["examples"])


def test_partially_dated_rating_changes_say_so():
    assert rating_availability(5, 0) == {"status": "available", "count": 5, "undated": 0}
    partial = rating_availability(5, 12)
    assert (partial["status"], partial["count"]) == ("partial", 5)
    assert "12 rating changes" in partial["note"]


# --- freshness --------------------------------------------------------------


async def test_partial_freshness_qualifies_every_claim():
    conn, factory = _conn(regs=EVENTS[:3])
    body = (await _get(WM_HOMECARE, factory, freshness=PARTIAL)).json()
    src = body["source"]
    assert src["freshness_status"] == "partial"
    assert src["coverage_confirmed"] is False
    assert src["source_published_at"] == "2026-10-14"
    assert src["window_anchor"] == "2026-10-16"
    assert "not a freshness guarantee" in src["window_anchor_basis"]
    assert body["brief"]["provisional"] is True
    assert "provisional" in body["brief"]["note"]
    assert body["caveats"][0].startswith("CQC source coverage cannot currently be confirmed (status: partial)")


async def test_fresh_source_is_not_qualified():
    conn, factory = _conn(regs=EVENTS[:3])
    body = (await _get(WM_HOMECARE, factory)).json()
    assert body["source"]["coverage_confirmed"] is True
    assert body["brief"]["provisional"] is False
    assert not any("cannot currently be confirmed" in c for c in body["caveats"])


# --- endpoint behaviour -----------------------------------------------------


async def test_unknown_territory_is_404():
    conn, factory = _conn(scope_row={"organisations": 0, "locations": 0, "canonical_name": None})
    resp = await _get("/api/v1/territory-preview?kind=local_authority&name=Atlantis", factory)
    assert resp.status_code == 404


@pytest.mark.parametrize("query", [
    "kind=county&name=Kent",
    "kind=region&name=x",
    "kind=region&name=Kent%3B%20DROP%20TABLE",
    "kind=region&name=Kent&service=dentist",
])
async def test_invalid_input_is_rejected_before_any_query(query):
    conn, factory = _conn()
    resp = await _get(f"/api/v1/territory-preview?{query}", factory)
    assert resp.status_code == 422
    conn.fetchval.assert_not_called()


async def test_responses_are_cached_per_scope_and_source_version():
    conn, factory = _conn(regs=EVENTS[:3])
    conn.fetchval.side_effect = [True, REV, WINDOW_END, True, REV]  # second call: guard + revision only
    first = await _get(WM_HOMECARE, factory)
    second = await _get(WM_HOMECARE, factory)
    assert first.json() == second.json()
    assert conn.fetchrow.await_count == 2  # scope + counts, once


async def test_quarantine_change_bypasses_cached_preview():
    """Regression (review 19 Oct): a newly quarantined location must not survive in a cached preview."""
    before = [_event("new_registration", date(2026, 10, 10), "1-Q", "PQ"), *EVENTS[:1]]
    conn, factory = _conn(regs=before)
    first = (await _get(WM_HOMECARE, factory)).json()
    assert "1-Q" in {e["location_id"] for e in first["examples"]}

    # 1-Q is quarantined: the revision changes and the queries now exclude it.
    after_counts = {**COUNTS_DATED, "new_registrations": COUNTS_DATED["new_registrations"] - 1}
    conn.fetchval.side_effect = [True, "4:2026-10-19 09:00:00+00", WINDOW_END]
    conn.fetchrow.side_effect = [{**SCOPE_ROW, "locations": SCOPE_ROW["locations"] - 1}, after_counts]
    conn.fetch.side_effect = [EVENTS[:1], []]
    second = (await _get(WM_HOMECARE, factory)).json()
    assert "1-Q" not in {e["location_id"] for e in second["examples"]}
    assert second["locations"] == SCOPE_ROW["locations"] - 1
    assert second["signals"]["new_registrations"] == first["signals"]["new_registrations"] - 1


async def test_territory_list_cache_follows_quarantine_revision():
    rows = [{"kind": "region", "name": "West Midlands", "organisations": 4260}]
    conn, factory = _conn(territories=rows)
    conn.fetchval.side_effect = [True, REV, True, REV, True, "4:later"]
    for _ in range(3):
        assert (await _get("/api/v1/territory-preview/territories", factory)).status_code == 200
    assert conn.fetch.await_count == 2  # cached once, re-read after the revision changed


def test_quarantine_revision_tracks_new_updated_and_resolved_rows():
    sql = q.QUARANTINE_REVISION
    assert "resolved_at IS NULL" in sql
    for column in ("created_at", "updated_at", "resolved_at"):
        assert column in sql


async def test_territories_lists_regions_las_and_canonical_services():
    rows = [
        {"kind": "region", "name": "West Midlands", "organisations": 4260},
        {"kind": "local_authority", "name": "Coventry", "organisations": 300},
    ]
    conn, factory = _conn(territories=rows)
    body = (await _get("/api/v1/territory-preview/territories", factory)).json()
    assert body["regions"] == [{"name": "West Midlands", "organisations": 4260}]
    assert body["local_authorities"] == [{"name": "Coventry", "organisations": 300}]
    assert [s["key"] for s in body["services"]] == ["homecare", "residential", "nursing", "supported_living"]
    assert body["services"][0]["label"] == "Home Care"


async def test_public_rate_limit_applies():
    rows = [{"kind": "region", "name": "West Midlands", "organisations": 4260}]
    statuses = []
    for _ in range(ip_rate_limit._MAX_PUBLIC_PER_MINUTE + 1):
        router_mod._cache.clear()
        _, factory = _conn(territories=rows)
        statuses.append((await _get("/api/v1/territory-preview/territories", factory)).status_code)
    assert statuses[-1] == 429
    assert set(statuses[:-1]) == {200}


# --- service ----------------------------------------------------------------


def test_window_ends_at_latest_recorded_registration():
    assert window_for(WINDOW_END) == (date(2026, 7, 19), WINDOW_END)


def test_examples_are_one_per_provider_and_mix_signal_types():
    assert [e["location_id"] for e in pick_examples(EVENTS)] == ["1-004", "1-001", "1-003"]


def test_reasons_are_factual_dated_and_use_canonical_service_names():
    assert reason_for(EVENTS[0], "home-care") == "Registered with CQC on 1 Oct 2026 · Home Care"
    assert reason_for(EVENTS[3], None) == (
        "CQC rating moved from Requires improvement to Good, report dated 30 Sep 2026 · Home Care"
    )


def _body(**kw):
    scope = PreviewScope(kind="region", name="West Midlands", service_key=None, service_slug=None)
    args = {
        "organisations": 400, "locations": 600, "window_end": WINDOW_END,
        "counts": COUNTS_DATED, "events": EVENTS, "freshness": FRESH,
    }
    args.update(kw)
    return build_preview(scope, **args)


def test_small_territory_says_it_does_not_fit_before_payment():
    body = _body(organisations=12, locations=20, events=[])
    assert body["brief"]["fits"] is False
    assert "before any payment" in body["brief"]["note"]
    assert body["examples"] == []


def test_copy_uses_provider_language_and_never_claims_leads_need_or_intent():
    body = _body(freshness=PARTIAL, counts={**COUNTS_DATED, "rating_changes_dated": 0, "rating_changes_undated": 3})
    text = " ".join([body["brief"]["note"], *body["caveats"], *(e["reason"] for e in body["examples"])]).lower()
    assert "providers to focus on, not leads ready to buy" in text
    for banned in ("hot lead", "ready-to-buy", "will buy", "needs your", "guarantee", "account"):
        assert banned not in text
    assert "independent of cqc" in body["source"]["basis"].lower()
