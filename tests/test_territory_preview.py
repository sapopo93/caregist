"""Free Territory Brief preview: flag gate, response shape, wording and limits."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.config import Settings
from api.main import app
from api.middleware import ip_rate_limit
from api.services.territory_preview import (
    PreviewScope,
    build_preview,
    pick_examples,
    reason_for,
    window_for,
)

AS_OF = date(2026, 10, 14)


def _event(kind, day, loc, provider, *, old=None, new=None, services="Homecare Agencies"):
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
    _event("new_registration", date(2026, 9, 20), "1-002", "P1"),  # same organisation as 1-001
    _event("new_registration", date(2026, 8, 2), "1-003", "P2"),
    _event("rating_changed", date(2026, 9, 30), "1-004", "P3", old="Requires improvement", new="Good"),
]


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    ip_rate_limit._public_ip_requests.clear()
    yield
    ip_rate_limit._public_ip_requests.clear()


def _conn(counts=None, as_of=AS_OF, regs=None, ratings=None, territories=None):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=counts)
    conn.fetchval = AsyncMock(return_value=as_of)
    if territories is not None:
        conn.fetch = AsyncMock(return_value=territories)
    else:
        conn.fetch = AsyncMock(side_effect=[regs or [], ratings or []])

    @asynccontextmanager
    async def get_connection():
        yield conn

    return conn, get_connection


async def _get(path, conn_factory, enabled=True):
    with patch("api.routers.territory_preview.get_connection", conn_factory), \
         patch("api.routers.territory_preview.settings.territory_preview_enabled", enabled):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            return await client.get(path)


# --- gate -------------------------------------------------------------------


def test_preview_flag_defaults_off():
    cfg = Settings(database_url="postgresql://localhost/x", api_master_key="m", support_internal_token="s")
    assert cfg.territory_preview_enabled is False


@pytest.mark.parametrize("path", [
    "/api/v1/territory-preview?kind=region&name=West%20Midlands",
    "/api/v1/territory-preview/territories",
])
async def test_closed_flag_returns_404_and_reads_nothing(path):
    conn, factory = _conn()
    resp = await _get(path, factory, enabled=False)
    assert resp.status_code == 404
    conn.fetch.assert_not_called()
    conn.fetchrow.assert_not_called()


# --- endpoint ---------------------------------------------------------------


async def test_preview_returns_counts_signals_and_three_examples():
    counts = {"organisations": 412, "locations": 655, "latest_registration": AS_OF, "canonical_name": "West Midlands"}
    regs = [e for e in EVENTS if e["event_type"] == "new_registration"]
    ratings = [e for e in EVENTS if e["event_type"] == "rating_changed"]
    conn, factory = _conn(counts=counts, regs=regs, ratings=ratings)
    resp = await _get("/api/v1/territory-preview?kind=region&name=west%20midlands&service=homecare", factory)
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == {
        "kind": "region", "name": "West Midlands", "service": "homecare", "service_label": "Homecare Agencies",
    }
    assert (body["organisations"], body["locations"]) == (412, 655)
    assert body["signals"] == {"new_registrations": 3, "rating_changes": 1, "organisations_with_signals": 3}
    assert body["window"] == {"start": "2026-07-17", "end": "2026-10-14", "days": 90}
    assert len(body["examples"]) == 3
    assert {e["provider_id"] for e in body["examples"]} == {"P1", "P2", "P3"}
    assert body["examples"][0]["source_url"] == "https://www.cqc.org.uk/location/1-004"
    assert body["brief"]["fits"] is True
    # Territory name and service label are bound parameters, never interpolated.
    args = conn.fetchrow.call_args.args
    assert args[1:] == ("west midlands", "Homecare Agencies")
    assert "west midlands" not in args[0]


async def test_unknown_territory_is_404():
    conn, factory = _conn(counts={"organisations": 0, "locations": 0, "latest_registration": None, "canonical_name": None})
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
    conn.fetchrow.assert_not_called()


async def test_territories_lists_regions_las_and_services():
    rows = [
        {"kind": "region", "name": "West Midlands", "organisations": 3000},
        {"kind": "local_authority", "name": "Coventry", "organisations": 300},
    ]
    conn, factory = _conn(territories=rows)
    resp = await _get("/api/v1/territory-preview/territories", factory)
    assert resp.status_code == 200
    body = resp.json()
    assert body["regions"] == [{"name": "West Midlands", "organisations": 3000}]
    assert body["local_authorities"] == [{"name": "Coventry", "organisations": 300}]
    assert [s["key"] for s in body["services"]] == ["homecare", "residential", "nursing", "supported_living"]


async def test_public_rate_limit_applies():
    rows = [{"kind": "region", "name": "West Midlands", "organisations": 3000}]
    statuses = []
    for _ in range(ip_rate_limit._MAX_PUBLIC_PER_MINUTE + 1):
        _, factory = _conn(territories=rows)
        statuses.append((await _get("/api/v1/territory-preview/territories", factory)).status_code)
    assert statuses[-1] == 429
    assert set(statuses[:-1]) == {200}


# --- service ----------------------------------------------------------------


def test_window_is_anchored_to_source_date_not_today():
    assert window_for(AS_OF) == (date(2026, 7, 17), AS_OF)


def test_examples_are_one_per_organisation_and_mix_signal_types():
    picked = pick_examples(EVENTS)
    assert [e["location_id"] for e in picked] == ["1-004", "1-001", "1-003"]


def test_reasons_are_factual_and_dated():
    reg = reason_for(EVENTS[0], AS_OF, "Homecare Agencies")
    assert reg == "Registered with CQC on 1 Oct 2026, 1 week before the data date · Homecare Agencies"
    rating = reason_for(EVENTS[3], AS_OF, None)
    assert rating == "CQC rating moved from Requires improvement to Good, report dated 30 Sep 2026 · Homecare Agencies"


def test_small_territory_says_it_does_not_fit_before_payment():
    scope = PreviewScope(kind="local_authority", name="Rutland", service_key=None, service_label=None)
    body = build_preview(scope, organisations=12, locations=20, as_of=AS_OF, events=[])
    assert body["brief"]["fits"] is False
    assert "before any payment" in body["brief"]["note"]
    assert body["examples"] == []


def test_copy_never_claims_leads_need_or_intent():
    scope = PreviewScope(kind="region", name="West Midlands", service_key=None, service_label=None)
    body = build_preview(scope, organisations=400, locations=600, as_of=AS_OF, events=EVENTS)
    text = " ".join([body["brief"]["note"], *body["caveats"], *(e["reason"] for e in body["examples"])]).lower()
    assert "not leads ready to buy" in text
    for banned in ("hot lead", "ready-to-buy", "will buy", "needs your", "guarantee"):
        assert banned not in text
    assert "independent of cqc" in body["source"]["basis"].lower()
