"""Two-gate claim verification tests.

Gate 1: email domain matches CQC website domain  → auto-approve (status='approved')
Gate 2: domain mismatch / no website             → pending_review for admin
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware.auth import validate_api_key

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def patched_db(mock_conn):
    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    app.dependency_overrides[validate_api_key] = lambda: {
        "tier": "starter",
        "remaining": {
            "burst_remaining": 10,
            "daily_remaining": 100,
            "rolling_7d_remaining": 100,
            "monthly_remaining": 100,
        },
        "user_id": 1,
        "email": "ops@caregist.co.uk",
    }
    with patch("api.routers.claims.get_connection", mock_get_connection):
        with patch("api.routers.claims.write_audit_log", new=AsyncMock()):
            yield mock_conn
    app.dependency_overrides = {}


HEADERS = {"X-API-Key": "test-master-key-for-pytest"}

_CLAIM_ROW = {
    "id": 1,
    "provider_id": "LOC123",
    "status": "approved",
    "claimant_name": "Jane",
    "claimant_email": "jane@acme.co.uk",
    "fast_track": False,
    "review_reason": "domain match",
    "created_at": "2026-01-01",
}

_PENDING_ROW = {**_CLAIM_ROW, "status": "pending_review"}


# ---------------------------------------------------------------------------
# Gate 1: domain match → auto-approve
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_domain_match_auto_approves(patched_db):
    """Exact domain match triggers auto-approval."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": "https://www.acme.co.uk"},  # provider lookup
        None,                                                                          # HAS_PENDING_CLAIM
        _CLAIM_ROW,                                                                    # INSERT_CLAIM
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane Smith",
                "claimant_email": "jane@acme.co.uk",
                "claimant_role": "Registered Manager",
                "proof_of_association": "CQC ID 12345",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["gate"] == "auto_approved"
    assert "automatically approved" in data["message"]
    # provider should be marked as claimed
    mock_conn.execute.assert_awaited()


@pytest.mark.asyncio
async def test_subdomain_match_auto_approves(patched_db):
    """Subdomain of the provider domain is accepted (Gate 1)."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": "https://acme.co.uk"},
        None,
        _CLAIM_ROW,
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane Smith",
                "claimant_email": "jane@care.acme.co.uk",
                "claimant_role": "Manager",
                "proof_of_association": "I manage this location",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 201
    assert resp.json()["gate"] == "auto_approved"


@pytest.mark.asyncio
async def test_www_prefix_stripped_and_matches(patched_db):
    """Provider website with www. prefix is normalised before comparison."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": "https://www.acme.co.uk/about"},
        None,
        _CLAIM_ROW,
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane",
                "claimant_email": "jane@acme.co.uk",
                "claimant_role": "Owner",
                "proof_of_association": "CQC registered owner",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 201
    assert resp.json()["gate"] == "auto_approved"


@pytest.mark.asyncio
async def test_http_website_matches(patched_db):
    """http:// scheme (not https://) is handled correctly."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": "http://acme.co.uk"},
        None,
        _CLAIM_ROW,
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane",
                "claimant_email": "jane@acme.co.uk",
                "claimant_role": "Owner",
                "proof_of_association": "Proof here",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 201
    assert resp.json()["gate"] == "auto_approved"


# ---------------------------------------------------------------------------
# Gate 2: domain mismatch → pending_review
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_domain_mismatch_queues_for_review(patched_db):
    """Different email domain queues claim for admin review."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": "https://www.acme.co.uk"},
        None,
        _PENDING_ROW,
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Bob Jones",
                "claimant_email": "bob@gmail.com",
                "claimant_role": "Director",
                "proof_of_association": "I am the director",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["gate"] == "pending_review"
    assert "1–2 business days" in data["message"]
    # Provider must NOT be marked as claimed automatically
    mock_conn.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_website_queues_for_review(patched_db):
    """Provider with no website field → domain match impossible → Gate 2."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": None},
        None,
        _PENDING_ROW,
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane",
                "claimant_email": "jane@acme.co.uk",
                "claimant_role": "Owner",
                "proof_of_association": "I own this place",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 201
    assert resp.json()["gate"] == "pending_review"


@pytest.mark.asyncio
async def test_empty_website_queues_for_review(patched_db):
    """Provider with empty-string website → Gate 2."""
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": ""},
        None,
        _PENDING_ROW,
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane",
                "claimant_email": "jane@acme.co.uk",
                "claimant_role": "Owner",
                "proof_of_association": "I own this place",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 201
    assert resp.json()["gate"] == "pending_review"


# ---------------------------------------------------------------------------
# Admin queue: approving a pending_review claim marks provider claimed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_approve_pending_review_marks_provider_claimed(patched_db):
    """After admin approves a pending_review claim via PATCH /admin/claims/{id},
    the provider must be marked as claimed.

    This test patches the admin router's get_connection to verify the
    UPDATE care_providers call is issued on approval.
    """
    mock_conn = patched_db

    # Simulate the claim row returned after UPDATE_CLAIM_STATUS
    mock_conn.fetchrow.side_effect = [
        {"id": 42, "provider_id": "LOC123", "status": "approved"},
    ]

    app.dependency_overrides[validate_api_key] = lambda: {
        "tier": "admin",
        "remaining": {
            "burst_remaining": 10,
            "daily_remaining": 100,
            "rolling_7d_remaining": 100,
            "monthly_remaining": 100,
        },
        "user_id": 99,
        "email": "admin@caregist.co.uk",
        "name": "Admin User",
    }

    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    with patch("api.routers.admin.get_connection", mock_get_connection):
        with patch("api.routers.admin.write_audit_log", new=AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/admin/claims/42",
                    json={"status": "approved", "admin_notes": "Verified by phone"},
                    headers=HEADERS,
                )

    app.dependency_overrides = {}
    assert resp.status_code == 200
    # MARK_PROVIDER_CLAIMED (UPDATE care_providers SET is_claimed=true) must be called
    assert mock_conn.execute.call_count >= 1


# ---------------------------------------------------------------------------
# Existing guard: already-claimed and pending-exists still reject
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_already_claimed_rejects(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": True, "website": "https://acme.co.uk"},
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane",
                "claimant_email": "jane@acme.co.uk",
                "claimant_role": "Owner",
                "proof_of_association": "Test",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 409
    assert "already been claimed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_pending_claim_blocks_duplicate(patched_db):
    mock_conn = patched_db
    mock_conn.fetchrow.side_effect = [
        {"id": "LOC123", "is_claimed": False, "website": "https://acme.co.uk"},
        {"id": 99},  # existing pending claim
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/providers/test-provider/claim",
            json={
                "claimant_name": "Jane",
                "claimant_email": "jane@acme.co.uk",
                "claimant_role": "Owner",
                "proof_of_association": "Test",
            },
            headers=HEADERS,
        )

    assert resp.status_code == 409
    assert "already pending" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Domain utility unit tests (no HTTP involved)
# ---------------------------------------------------------------------------

from api.routers.claims import _extract_domain, _extract_website_domain, _domains_match


def test_extract_domain_basic():
    assert _extract_domain("jane@Acme.CO.UK") == "acme.co.uk"


def test_extract_website_domain_strips_www():
    assert _extract_website_domain("https://www.acme.co.uk/about") == "acme.co.uk"


def test_extract_website_domain_no_www():
    assert _extract_website_domain("https://acme.co.uk") == "acme.co.uk"


def test_extract_website_domain_http():
    assert _extract_website_domain("http://acme.co.uk") == "acme.co.uk"


def test_extract_website_domain_no_scheme():
    assert _extract_website_domain("www.acme.co.uk") == "acme.co.uk"


def test_extract_website_domain_none():
    assert _extract_website_domain(None) is None


def test_extract_website_domain_empty():
    assert _extract_website_domain("") is None


def test_domains_match_exact():
    assert _domains_match("acme.co.uk", "acme.co.uk") is True


def test_domains_match_subdomain():
    assert _domains_match("care.acme.co.uk", "acme.co.uk") is True


def test_domains_match_no_match():
    assert _domains_match("gmail.com", "acme.co.uk") is False


def test_domains_match_partial_suffix_not_subdomain():
    # "notacme.co.uk" should NOT match "acme.co.uk"
    assert _domains_match("notacme.co.uk", "acme.co.uk") is False


def test_domains_match_www2_not_stripped():
    # www2.acme.co.uk: the website extraction won't strip www2,
    # so comparison is straightforward
    assert _domains_match("acme.co.uk", "www2.acme.co.uk") is False
