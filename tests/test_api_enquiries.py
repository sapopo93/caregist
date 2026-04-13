"""Tests for enquiry (lead-gen) endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.middleware.auth import validate_api_key

HEADERS = {"X-API-Key": "test-master-key-for-pytest"}


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
        "user_id": 1,
        "email": "ops@caregist.co.uk",
    }
    with patch("api.routers.enquiries.get_connection", mock_get_connection):
        yield mock_conn
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_submit_enquiry_success(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False},  # PROVIDER_ID_BY_SLUG
        {"id": 1, "provider_id": "LOC123", "status": "new", "enquirer_name": "Sarah", "created_at": "2026-01-01"},
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test-provider/enquire", json={
            "enquirer_name": "Sarah Jones",
            "enquirer_email": "sarah@example.com",
            "enquirer_phone": "07700900123",
            "relationship": "family_member",
            "care_type": "Residential care",
            "urgency": "within_month",
            "message": "My mother needs full-time residential care. She has early-stage dementia.",
        }, headers=HEADERS)

    assert resp.status_code == 201
    assert "sent" in resp.json()["message"]


@pytest.mark.asyncio
async def test_submit_enquiry_provider_not_found(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/nonexistent/enquire", json={
            "enquirer_name": "Sarah",
            "enquirer_email": "sarah@example.com",
            "message": "Test enquiry",
        }, headers=HEADERS)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_enquiry_invalid_urgency(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {"id": "LOC123", "is_claimed": False}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test/enquire", json={
            "enquirer_name": "Sarah",
            "enquirer_email": "sarah@example.com",
            "urgency": "invalid_urgency",
            "message": "Test",
        }, headers=HEADERS)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_enquiry_missing_message(patched_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test/enquire", json={
            "enquirer_name": "Sarah",
            "enquirer_email": "sarah@example.com",
        }, headers=HEADERS)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_enquiry_updates_count(patched_db):
    """Verify that enquiry count is updated after submission."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False},
        {"id": 1, "provider_id": "LOC123", "status": "new", "enquirer_name": "Sarah", "created_at": "2026-01-01"},
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/providers/test-provider/enquire", json={
            "enquirer_name": "Sarah",
            "enquirer_email": "sarah@example.com",
            "message": "Test",
        }, headers=HEADERS)

    # Verify execute was called (for UPDATE_PROVIDER_ENQUIRY_COUNT)
    assert mock_conn.execute.called
