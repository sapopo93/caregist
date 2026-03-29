"""Tests for provider comparison endpoint."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from api.main import app

HEADERS = {"X-API-Key": "change_me_in_production"}


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

    with patch("api.routers.providers.get_connection", mock_get_connection), \
         patch("api.middleware.auth.get_connection", mock_get_connection):
        yield mock_conn


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
async def test_compare_max_three(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = [
        mock_provider_row("a", "A"),
        mock_provider_row("b", "B"),
        mock_provider_row("c", "C"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/providers/compare?slugs=a,b,c,d,e",
            headers=HEADERS,
        )

    assert resp.status_code == 200
    # Query should only include first 3 slugs
    call_args = mock_conn.fetch.call_args
    assert len(call_args[0][1]) == 3


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
