from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def patched_db(mock_conn):
    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    with patch("api.routers.providers.get_connection", mock_get_connection):
        yield mock_conn


@pytest.mark.asyncio
async def test_public_search_works_without_api_key(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = [
        {
            "id": "1-100",
            "name": "Sunrise Care Home",
            "slug": "sunrise-care-home",
            "type": "Social Care Org",
            "status": "ACTIVE",
            "town": "Bournemouth",
            "county": "Dorset",
            "postcode": "BH1 1AA",
            "region": "South West",
            "local_authority": "Bournemouth, Christchurch and Poole",
            "overall_rating": "Good",
            "service_types": "Residential Homes",
            "specialisms": "Dementia",
            "number_of_beds": 25,
            "quality_score": 82,
            "quality_tier": "GOOD",
            "phone": "01202000000",
            "website": "https://example.com",
            "last_inspection_date": "2025-01-01",
            "inspection_report_url": "https://example.com/report",
        }
    ]
    mock_conn.fetchrow.return_value = {"total": 1}

    remaining = {
        "burst_remaining": 1,
        "daily_remaining": 19,
        "rolling_7d_remaining": 59,
        "monthly_remaining": 299,
    }

    with patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value=remaining)) as mock_rate_limit:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/providers/search?q=bournemouth")

    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["tier"] == "free"
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "Sunrise Care Home"
    mock_rate_limit.assert_awaited_once()
    guest_key, tier = mock_rate_limit.await_args.args
    assert guest_key.startswith("guest:")
    assert tier == "free"


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup_key", ["sunrise-care-home", "1-100"])
async def test_public_provider_detail_resolves_by_slug_or_id(patched_db, lookup_key):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {
        "id": "1-100",
        "name": "Sunrise Care Home",
        "slug": "sunrise-care-home",
        "type": "Social Care Org",
        "status": "ACTIVE",
        "town": "Bournemouth",
        "county": "Dorset",
        "postcode": "BH1 1AA",
        "region": "South West",
        "local_authority": "Bournemouth, Christchurch and Poole",
        "overall_rating": "Good",
        "service_types": "Residential Homes",
        "specialisms": "Dementia",
        "number_of_beds": 25,
        "quality_score": 82,
        "quality_tier": "GOOD",
        "phone": "01202000000",
        "website": "https://example.com",
        "last_inspection_date": "2025-01-01",
        "inspection_report_url": "https://example.com/report",
    }

    remaining = {
        "burst_remaining": 1,
        "daily_remaining": 19,
        "rolling_7d_remaining": 59,
        "monthly_remaining": 299,
    }

    with patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value=remaining)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/providers/{lookup_key}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == "1-100"
    assert body["data"]["name"] == "Sunrise Care Home"
    mock_conn.fetchrow.assert_awaited_with(
        "\nSELECT * FROM care_providers WHERE slug = $1 OR id = $1\n",
        lookup_key,
    )
