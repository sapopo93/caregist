"""Tests for review endpoints."""

import pytest
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

    with patch("api.routers.reviews.get_connection", mock_get_connection), \
         patch("api.routers.providers.get_connection", mock_get_connection), \
         patch("api.middleware.auth.get_connection", mock_get_connection):
        yield mock_conn


@pytest.mark.asyncio
async def test_submit_review_success(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False},  # PROVIDER_ID_BY_SLUG
        {"id": 1, "provider_id": "LOC123", "status": "pending", "rating": 4, "title": "Great care", "reviewer_name": "John", "created_at": "2026-01-01"},
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test-provider/reviews", json={
            "rating": 4,
            "title": "Great care",
            "body": "The staff were wonderful and attentive.",
            "reviewer_name": "John Doe",
            "reviewer_email": "john@example.com",
            "relationship": "family_member",
        }, headers=HEADERS)

    assert resp.status_code == 201
    assert "moderated" in resp.json()["message"]


@pytest.mark.asyncio
async def test_submit_review_invalid_rating(patched_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test/reviews", json={
            "rating": 6,
            "title": "Test",
            "body": "Test review",
            "reviewer_name": "John",
            "reviewer_email": "john@example.com",
        }, headers=HEADERS)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_review_invalid_relationship(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {"id": "LOC123", "is_claimed": False}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test/reviews", json={
            "rating": 4,
            "title": "Test",
            "body": "Test review body text",
            "reviewer_name": "John",
            "reviewer_email": "john@example.com",
            "relationship": "invalid_value",
        }, headers=HEADERS)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_reviews(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False},  # PROVIDER_ID_BY_SLUG
        {"total": 1},  # COUNT
        {"count": 1, "avg_rating": 4.0},  # SUMMARY
    ]
    mock_conn.fetch.return_value = [
        {"id": 1, "rating": 4, "title": "Great", "body": "Good care", "reviewer_name": "John", "relationship": "family_member", "visit_date": None, "created_at": "2026-01-01"}
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/providers/test-provider/reviews", headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["count"] == 1
    assert data["summary"]["avg_rating"] == 4.0
    assert len(data["data"]) == 1


@pytest.mark.asyncio
async def test_list_reviews_provider_not_found(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/providers/nonexistent/reviews", headers=HEADERS)

    assert resp.status_code == 404
