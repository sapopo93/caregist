"""Tests for provider claiming endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from api.main import app


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def patched_db(mock_conn):
    """Patch get_connection to yield a mock connection."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    with patch("api.routers.claims.get_connection", mock_get_connection), \
         patch("api.routers.providers.get_connection", mock_get_connection), \
         patch("api.middleware.auth.get_connection", mock_get_connection):
        yield mock_conn


HEADERS = {"X-API-Key": "change_me_in_production"}


@pytest.mark.asyncio
async def test_submit_claim_success(patched_db):
    mock_conn = patched_db
    # Provider exists and is not claimed
    mock_conn.fetchrow.side_effect = [
        # validate_api_key: key lookup (skipped for master key)
        {"id": "LOC123", "is_claimed": False},  # PROVIDER_ID_BY_SLUG
        None,  # HAS_PENDING_CLAIM
        {"id": 1, "provider_id": "LOC123", "status": "pending", "claimant_name": "Jane", "claimant_email": "jane@care.co.uk", "created_at": "2026-01-01"},  # INSERT_CLAIM
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test-provider/claim", json={
            "claimant_name": "Jane Smith",
            "claimant_email": "jane@care.co.uk",
            "claimant_role": "Registered Manager",
            "proof_of_association": "I am the registered manager, CQC ID 12345",
        }, headers=HEADERS)

    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == "Claim submitted successfully. We'll review it within 2 business days."


@pytest.mark.asyncio
async def test_submit_claim_already_claimed(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": True},  # Already claimed
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test-provider/claim", json={
            "claimant_name": "Jane",
            "claimant_email": "jane@care.co.uk",
            "claimant_role": "Owner",
            "proof_of_association": "I own this place",
        }, headers=HEADERS)

    assert resp.status_code == 409
    assert "already been claimed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_submit_claim_provider_not_found(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/nonexistent/claim", json={
            "claimant_name": "Jane",
            "claimant_email": "jane@care.co.uk",
            "claimant_role": "Owner",
            "proof_of_association": "Test",
        }, headers=HEADERS)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_claim_pending_exists(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False},
        {"id": 99},  # Existing pending claim
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test-provider/claim", json={
            "claimant_name": "Jane",
            "claimant_email": "jane@care.co.uk",
            "claimant_role": "Owner",
            "proof_of_association": "Test",
        }, headers=HEADERS)

    assert resp.status_code == 409
    assert "already pending" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_submit_claim_validation():
    """Missing required fields should return 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/providers/test/claim", json={
            "claimant_name": "Jane",
        }, headers=HEADERS)

    assert resp.status_code == 422
