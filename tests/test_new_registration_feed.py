from contextlib import asynccontextmanager
from datetime import date
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.services.new_registration_feed import (
    FeedFilters,
    build_weekly_digest_html,
    deliver_new_registration_event,
    digest_key_for_week,
    event_matches_filter,
    queue_weekly_new_registration_digests,
    sync_new_registration_event_payloads,
)


HEADERS = {"X-API-Key": "change_me_in_production"}


def _auth(tier: str = "starter") -> dict:
    return {
        "tier": tier,
        "remaining": {
            "second": 10,
            "day": 10,
            "week": 10,
            "month": 10,
            "burst_remaining": 10,
            "daily_remaining": 10,
            "rolling_7d_remaining": 10,
            "monthly_remaining": 10,
        },
        "user_id": 7,
        "email": "ops@caregist.co.uk",
    }


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="OK")
    return conn


def test_sync_new_registration_event_payloads_maps_inserted_rows():
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "dedupe_key": "new_registration:LOC123:2026-04-01",
                "provider_id": "PROV1",
                "effective_date": date(2026, 4, 1),
                "confidence_score": 0.99,
                "metadata": {
                    "name": "Sunrise Care",
                    "slug": "sunrise-care",
                    "region": "London",
                    "local_authority": "Camden",
                },
            }
        ]
    )

    rows = asyncio.run(sync_new_registration_event_payloads(conn, force=True))

    assert len(rows) == 1
    assert rows[0]["dedupe_key"] == "new_registration:LOC123:2026-04-01"
    assert rows[0]["name"] == "Sunrise Care"
    assert rows[0]["confidence_score"] == pytest.approx(0.99)


def test_event_matches_filter_checks_region_service_type_and_dates():
    payload = {
        "name": "Sunrise Care",
        "town": "Barnet",
        "local_authority": "Barnet",
        "region": "London",
        "service_types": "Home care service",
        "type": "Social Care Org",
        "postcode": "N1 1AA",
        "effective_date": "2026-04-03",
    }

    assert event_matches_filter(payload, {"region": "London", "service_type": "Home care"})
    assert not event_matches_filter(payload, {"region": "South East"})
    assert not event_matches_filter(payload, {"from_date": "2026-04-04"})


@pytest.mark.asyncio
async def test_deliver_new_registration_event_skips_already_delivered(mock_conn):
    mock_conn.fetch.return_value = [
        {
            "id": 10,
            "url": "https://example.com/webhook",
            "secret": "secret",
            "filter_config": {},
        }
    ]
    mock_conn.fetchrow.return_value = {
        "id": 22,
        "delivered_at": "2026-04-10T00:00:00Z",
        "attempt_count": 1,
    }

    with patch("api.services.new_registration_feed.deliver_webhook", new=AsyncMock(return_value=(True, 1, 200, None))) as deliver_mock:
        delivered = await deliver_new_registration_event(
            mock_conn,
            {"dedupe_key": "new_registration:LOC1:2026-04-01", "name": "Sunrise", "effective_date": "2026-04-01"},
        )

    assert delivered == 0
    deliver_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_queue_weekly_new_registration_digests_is_idempotent(mock_conn):
    mock_conn.fetch.return_value = [
        {
            "id": 1,
            "user_id": 7,
            "email": "ops@caregist.co.uk",
            "filters": {"region": "London"},
            "unsubscribe_token": "token-1",
        }
    ]
    mock_conn.fetchval.side_effect = [None, 1]

    with patch("api.services.new_registration_feed.list_new_registration_events", new=AsyncMock(return_value=([
        {
            "slug": "sunrise-care",
            "name": "Sunrise Care",
            "town": "London",
            "region": "London",
            "local_authority": "Camden",
            "service_types": "Home care",
            "effective_date": "2026-04-01",
        }
    ], 1))), patch("api.services.new_registration_feed.queue_email", new=AsyncMock(return_value=55)) as queue_mock:
        first = await queue_weekly_new_registration_digests(mock_conn, reference_date=date(2026, 4, 10))
        second = await queue_weekly_new_registration_digests(mock_conn, reference_date=date(2026, 4, 10))

    assert first == {"queued": 1, "skipped": 0}
    assert second == {"queued": 0, "skipped": 1}
    queue_mock.assert_awaited_once()


def test_digest_helpers_render_expected_content():
    digest_key = digest_key_for_week(date(2026, 4, 10))
    html = build_weekly_digest_html(
        {"region": "London"},
        [
            {
                "slug": "sunrise-care",
                "name": "Sunrise Care",
                "town": "London",
                "region": "London",
                "local_authority": "Camden",
                "service_types": "Home care",
                "effective_date": "2026-04-01",
            }
        ],
        digest_key,
    )

    assert digest_key == "2026-W15"
    assert "Sunrise Care" in html
    assert "Applied filters" in html


@pytest.fixture
def patched_feed_dependencies(mock_conn):
    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    from api.middleware.auth import validate_api_key

    app.dependency_overrides = {}
    app.dependency_overrides[validate_api_key] = lambda: _auth("starter")
    with patch("api.routers.feed.get_connection", mock_get_connection), patch(
        "api.routers.feed.sync_new_registration_events", new=AsyncMock(return_value=1)
    ):
        yield mock_conn
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_feed_endpoint_returns_filtered_results(patched_feed_dependencies):
    mock_conn = patched_feed_dependencies
    mock_conn.fetch.return_value = [
        {
            "id": 1,
            "event_type": "new_registration",
            "effective_date": "2026-04-01",
            "observed_at": "2026-04-01T00:00:00Z",
            "confidence_score": 0.99,
            "dedupe_key": "new_registration:LOC1:2026-04-01",
            "metadata": {},
            "provider_location_id": "LOC1",
            "provider_id": "PROV1",
            "slug": "sunrise-care",
            "name": "Sunrise Care",
            "type": "Social Care Org",
            "status": "ACTIVE",
            "region": "London",
            "local_authority": "Camden",
            "town": "London",
            "county": "Greater London",
            "postcode": "N1 1AA",
            "registration_date": "2026-04-01",
            "service_types": "Home care",
            "website": "https://example.com",
            "phone": "0207000000",
            "overall_rating": None,
        }
    ]
    mock_conn.fetchrow.return_value = {"total": 1}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/feed/new-registrations?region=London", headers=HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["name"] == "Sunrise Care"


@pytest.mark.asyncio
async def test_feed_export_is_blocked_for_free_tier(mock_conn):
    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    from api.middleware.auth import validate_api_key

    app.dependency_overrides = {validate_api_key: lambda: _auth("free")}
    with patch("api.routers.feed.get_connection", mock_get_connection):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/feed/new-registrations/export.csv", headers=HEADERS)
    app.dependency_overrides = {}

    assert response.status_code == 403
    assert "Starter" in response.json()["detail"]
