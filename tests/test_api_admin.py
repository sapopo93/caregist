"""Tests for admin endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.middleware.auth import validate_api_key

MASTER_KEY = "test-master-key-for-pytest"
REGULAR_KEY = "regular_key"
HEADERS = {"X-API-Key": MASTER_KEY}


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
        "name": "master",
        "remaining": {
            "burst_remaining": 10,
            "daily_remaining": 100,
            "rolling_7d_remaining": 100,
            "monthly_remaining": 100,
        },
    }
    with patch("api.routers.admin.get_connection", mock_get_connection):
        yield mock_conn
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_dashboard_stats(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {
        "total_providers": 55818,
        "claimed_providers": 5,
        "pending_claims": 3,
        "pending_reviews": 12,
        "new_enquiries": 8,
        "total_reviews": 50,
        "total_enquiries": 200,
    }
    mock_conn.fetch.return_value = [
        {"name": "Test Care Home", "slug": "test-care-home", "enquiry_count": 15, "is_claimed": True, "overall_rating": "Good"},
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/stats", headers=HEADERS)

    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total_providers"] == 55818
    assert data["data"]["pending_claims"] == 3
    assert len(data["top_enquired"]) == 1


@pytest.mark.asyncio
async def test_admin_requires_master_key(patched_db):
    app.dependency_overrides[validate_api_key] = lambda: {
        "tier": "free",
        "name": "Regular User",
        "remaining": {
            "burst_remaining": 10,
            "daily_remaining": 100,
            "rolling_7d_remaining": 100,
            "monthly_remaining": 100,
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/stats",
            headers={"X-API-Key": REGULAR_KEY},
        )
    app.dependency_overrides = {}

    assert resp.status_code == 403
    assert "Admin access required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_no_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/stats")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_moderate_claim_approve(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {"id": 1, "provider_id": "LOC123", "status": "approved"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/api/v1/admin/claims/1", json={
            "status": "approved",
        }, headers=HEADERS)

    assert resp.status_code == 200
    assert resp.json()["message"] == "Claim approved."
    # Verify MARK_PROVIDER_CLAIMED was called
    assert mock_conn.execute.called


@pytest.mark.asyncio
async def test_moderate_claim_reject(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {"id": 1, "provider_id": "LOC123", "status": "rejected"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/api/v1/admin/claims/1", json={
            "status": "rejected",
            "admin_notes": "Could not verify association.",
        }, headers=HEADERS)

    assert resp.status_code == 200
    assert resp.json()["message"] == "Claim rejected."


@pytest.mark.asyncio
async def test_moderate_claim_invalid_status(patched_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/api/v1/admin/claims/1", json={
            "status": "invalid",
        }, headers=HEADERS)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_moderate_review(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {"id": 1, "provider_id": "LOC123", "status": "approved"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/api/v1/admin/reviews/1", json={
            "status": "approved",
        }, headers=HEADERS)

    assert resp.status_code == 200
    # Verify review stats were updated
    assert mock_conn.execute.called


@pytest.mark.asyncio
async def test_list_claims(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = [
        {"id": 1, "provider_id": "LOC1", "status": "pending", "claimant_name": "Jane", "claimant_email": "jane@test.com",
         "claimant_phone": None, "claimant_role": "Manager", "organisation_name": None,
         "proof_of_association": "I manage this", "admin_notes": None,
         "created_at": "2026-01-01", "reviewed_at": None,
         "provider_name": "Test Home", "provider_slug": "test-home"},
    ]
    mock_conn.fetchrow.return_value = {"total": 1}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/claims?status=pending", headers=HEADERS)

    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] == 1
    assert len(resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_update_enquiry_status(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.return_value = {"id": 1, "status": "read"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/api/v1/admin/enquiries/1", json={
            "status": "read",
        }, headers=HEADERS)

    assert resp.status_code == 200
    assert "read" in resp.json()["message"]


@pytest.mark.asyncio
async def test_update_enquiry_invalid_status(patched_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/api/v1/admin/enquiries/1", json={
            "status": "pending",
        }, headers=HEADERS)

    assert resp.status_code == 422
