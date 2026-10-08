"""Acceptance tests (CG-AT) for the provider-facing journeys that are switched off.

Reviews, enquiries and claims are fail-closed by default. While a gate is shut the
endpoint must answer 503, write nothing to the database, and write nothing. The
existing tests only exercise the open path for reviews and enquiries.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.config import Settings
from api.main import app
from api.middleware.auth import validate_api_key

HEADERS = {"X-API-Key": "test-master-key-for-pytest"}
USER = {"tier": "starter", "remaining": {}, "user_id": 1, "email": "jane@care.co.uk"}


@pytest.fixture
def signed_in():
    app.dependency_overrides[validate_api_key] = lambda: USER
    yield
    app.dependency_overrides = {}


def _conn_spy():
    conn = AsyncMock()

    @asynccontextmanager
    async def get_connection():
        yield conn

    return conn, get_connection


# CG-AT-021 default: nothing customer-contributed is open unless somebody switches it on.
def test_review_enquiry_and_claim_gates_default_to_closed():
    cfg = Settings(database_url="postgresql://localhost/x", api_master_key="m", support_internal_token="s")
    assert (cfg.review_submissions_enabled, cfg.enquiries_enabled, cfg.provider_claims_enabled) == (False, False, False)


# CG-AT-021 negative: reviews closed -> 503 and nothing written.
@pytest.mark.asyncio
async def test_review_submission_closed_returns_503_and_writes_nothing(signed_in):
    conn, get_connection = _conn_spy()
    with patch("api.routers.reviews.get_connection", get_connection), \
         patch("api.routers.reviews.settings.review_submissions_enabled", False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            resp = await client.post(
                "/api/v1/providers/some-home/reviews",
                json={"rating": 4, "title": "Fine", "body": "A considered review of the home.",
                      "reviewer_name": "John Doe", "reviewer_email": "john@example.com", "relationship": "family_member"},
                headers=HEADERS,
            )
    assert resp.status_code == 503
    conn.fetchrow.assert_not_called()
    conn.execute.assert_not_called()


# CG-AT-022 negative: enquiries closed -> 503 and nothing written (the confirmation email is only built after the insert).
@pytest.mark.asyncio
async def test_enquiry_closed_returns_503_and_sends_nothing(signed_in):
    conn, get_connection = _conn_spy()
    with patch("api.routers.enquiries.get_connection", get_connection), \
         patch("api.routers.enquiries.settings.enquiries_enabled", False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            resp = await client.post(
                "/api/v1/providers/some-home/enquire",
                json={"enquirer_name": "Jane", "enquirer_email": "jane@example.com", "message": "Do you have a vacancy?"},
                headers=HEADERS,
            )
    assert resp.status_code == 503
    conn.fetchrow.assert_not_called()
    conn.execute.assert_not_called()


# CG-AT-023 negative: claim accepted while the outbound gate is shut queues no email.
@pytest.mark.asyncio
async def test_claim_accepted_with_outbound_gate_closed_queues_no_email(signed_in):
    conn, get_connection = _conn_spy()
    conn.fetchrow.side_effect = [
        {"id": "LOC1", "is_claimed": False},
        None,
        {"id": 1, "provider_id": "LOC1", "status": "pending", "claimant_name": "Jane",
         "claimant_email": "jane@care.co.uk", "created_at": "2026-01-01"},
    ]
    queue = AsyncMock()
    with patch("api.routers.claims.get_connection", get_connection), \
         patch("api.routers.claims.settings.provider_claims_enabled", True), \
         patch("api.routers.claims.settings.outbound_communications_enabled", False), \
         patch("api.utils.email_queue.queue_email", queue):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            resp = await client.post(
                "/api/v1/providers/some-home/claim",
                json={"claimant_name": "Jane Smith", "claimant_email": "jane@care.co.uk",
                      "claimant_role": "Registered Manager", "proof_of_association": "CQC ID 12345"},
                headers=HEADERS,
            )
    assert resp.status_code == 201
    queue.assert_not_called()
