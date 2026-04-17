"""Tests for provider comparison endpoint."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.middleware.auth import validate_api_key

HEADERS = {"X-API-Key": "test-master-key-for-pytest"}
STARTER_HEADERS = {"X-API-Key": "starter_key"}


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def patched_db(mock_conn):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    app.dependency_overrides[validate_api_key] = lambda: {
        "tier": "admin",
        "remaining": {
            "burst_remaining": 10,
            "daily_remaining": 100,
            "rolling_7d_remaining": 100,
            "monthly_remaining": 100,
        },
    }
    with patch("api.routers.providers.get_connection", mock_get_connection):
        yield mock_conn
    app.dependency_overrides = {}


def mock_provider_row(slug, name):
    """Create a mock asyncpg Record-like dict."""
    return {
        "id": f"LOC-{slug}",
        "slug": slug,
        "name": name,
        "type": "Care Home",
        "overall_rating": "Good",
        "latitude": Decimal("51.5074"),
        "longitude": Decimal("-0.1278"),
        "is_claimed": False,
        "review_count": 0,
        "avg_review_rating": None,
    }


@pytest.mark.asyncio
async def test_compare_two_providers(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = [
        mock_provider_row("provider-a", "Provider A"),
        mock_provider_row("provider-b", "Provider B"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/providers/compare?slugs=provider-a,provider-b",
            headers=HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    assert data[0]["latitude"] == 51.5074  # Decimal converted to float


@pytest.mark.asyncio
async def test_compare_accepts_provider_ids_for_slugless_cards(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = [
        mock_provider_row("provider-a", "Provider A"),
        mock_provider_row("provider-b", "Provider B"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/providers/compare?slugs=LOC-provider-a,LOC-provider-b",
            headers=HEADERS,
        )

    assert resp.status_code == 200
    query, lookup_keys = mock_conn.fetch.await_args.args
    assert "slug = ANY" in query
    assert "id = ANY" in query
    assert lookup_keys == ["LOC-provider-a", "LOC-provider-b"]


@pytest.mark.asyncio
async def test_compare_respects_starter_limit(patched_db):
    mock_conn = patched_db
    app.dependency_overrides[validate_api_key] = lambda: {
        "tier": "starter",
        "remaining": {
            "burst_remaining": 10,
            "daily_remaining": 100,
            "rolling_7d_remaining": 100,
            "monthly_remaining": 100,
        },
    }
    mock_conn.fetch.return_value = [
        mock_provider_row("a", "A"),
        mock_provider_row("b", "B"),
        mock_provider_row("c", "C"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/providers/compare?slugs=a,b,c,d,e",
            headers=STARTER_HEADERS,
        )
    app.dependency_overrides = {}

    assert resp.status_code == 200
    # Starter tier should only include first 3 slugs.
    call_args = mock_conn.fetch.call_args
    assert len(call_args[0][1]) == 3


@pytest.mark.asyncio
async def test_compare_master_can_compare_more_than_three(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = [
        mock_provider_row("a", "A"),
        mock_provider_row("b", "B"),
        mock_provider_row("c", "C"),
        mock_provider_row("d", "D"),
        mock_provider_row("e", "E"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/providers/compare?slugs=a,b,c,d,e",
            headers=HEADERS,
        )

    assert resp.status_code == 200
    call_args = mock_conn.fetch.call_args
    assert len(call_args[0][1]) == 5


@pytest.mark.asyncio
async def test_compare_empty_slugs(patched_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/providers/compare?slugs=",
            headers=HEADERS,
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_compare_not_found(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/providers/compare?slugs=nonexistent-a,nonexistent-b",
            headers=HEADERS,
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compare_no_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/providers/compare?slugs=a,b")

    assert resp.status_code == 401
