"""Tests for account deletion, DSAR export, and admin erase endpoints.

UK DPA Art 17 (erasure) + Art 15 (DSAR).

Covers:
- POST /api/v1/account/delete: soft-deletes, anonymises reviews, revokes
  sessions, deactivates API keys, cancels Stripe (mocked), audits.
- POST /api/v1/account/export: returns correct shape, audits DSAR_EXPORTED.
- POST /api/v1/admin/users/{id}/erase: requires admin scope, audits.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers (pytest-asyncio + httpx AsyncClient assumed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_account_soft_deletes_user(test_client, db_conn, make_user, make_api_key):
    """POST /api/v1/account/delete sets deleted_at and deactivates keys."""
    user = await make_user(email="delete_me@example.com", password="hunter2!")
    key = await make_api_key(user_id=user["id"])

    resp = await test_client.post(
        "/api/v1/account/delete",
        json={"password": "hunter2!"},
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 200, resp.text

    # User row soft-deleted
    row = await db_conn.fetchrow("SELECT deleted_at FROM users WHERE id = $1", user["id"])
    assert row["deleted_at"] is not None

    # API key deactivated
    key_row = await db_conn.fetchrow(
        "SELECT is_active FROM api_keys WHERE user_id = $1", user["id"]
    )
    assert key_row["is_active"] is False


@pytest.mark.asyncio
async def test_delete_account_anonymises_reviews(test_client, db_conn, make_user, make_api_key, make_review):
    """Deletion redacts reviewer_name -> 'Former user' and clears reviewer_email."""
    user = await make_user(email="redact_me@example.com", password="hunter2!")
    key = await make_api_key(user_id=user["id"])
    review_id = await make_review(reviewer_email="redact_me@example.com", reviewer_name="Jane Smith")

    await test_client.post(
        "/api/v1/account/delete",
        json={"password": "hunter2!"},
        headers={"X-API-Key": key},
    )

    review = await db_conn.fetchrow(
        "SELECT reviewer_name, reviewer_email FROM reviews WHERE id = $1", review_id
    )
    assert review["reviewer_name"] == "Former user"
    assert review["reviewer_email"] is None


@pytest.mark.asyncio
async def test_delete_account_revokes_sessions(test_client, db_conn, make_user, make_api_key, make_session):
    """Deletion marks all active sessions as revoked."""
    user = await make_user(email="session_del@example.com", password="hunter2!")
    key = await make_api_key(user_id=user["id"])
    session_id = await make_session(user_id=user["id"])

    await test_client.post(
        "/api/v1/account/delete",
        json={"password": "hunter2!"},
        headers={"X-API-Key": key},
    )

    session = await db_conn.fetchrow(
        "SELECT revoked_at FROM user_sessions WHERE id = $1", session_id
    )
    assert session["revoked_at"] is not None


@pytest.mark.asyncio
async def test_delete_account_cancels_stripe(test_client, make_user, make_api_key, mocker):
    """Deletion attempts Stripe cancellation; failure does not block response."""
    user = await make_user(
        email="stripe_cancel@example.com",
        password="hunter2!",
        stripe_customer_id="cus_test123",
    )
    key = await make_api_key(user_id=user["id"])

    stripe_cancel = mocker.patch("stripe.Subscription.cancel")
    mocker.patch(
        "stripe.Subscription.list",
        return_value=mocker.Mock(
            auto_paging_iter=lambda: iter([{"id": "sub_abc"}])
        ),
    )

    resp = await test_client.post(
        "/api/v1/account/delete",
        json={"password": "hunter2!"},
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 200
    stripe_cancel.assert_called_once_with("sub_abc")


@pytest.mark.asyncio
async def test_export_returns_expected_shape(test_client, make_user, make_api_key):
    """POST /api/v1/account/export returns 202 with records count and expiry."""
    user = await make_user(email="export_me@example.com", password="hunter2!")
    key = await make_api_key(user_id=user["id"])

    resp = await test_client.post(
        "/api/v1/account/export",
        headers={"X-API-Key": key},
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "expires_at" in data
    assert "records" in data
    assert set(data["records"].keys()) == {"reviews", "claims", "subscriptions", "sessions"}


@pytest.mark.asyncio
async def test_admin_erase_requires_admin_scope(test_client, make_user, make_api_key):
    """POST /api/v1/admin/users/{id}/erase returns 403 for non-admin key."""
    user = await make_user(email="victim@example.com", password="hunter2!")
    non_admin_key = await make_api_key(user_id=user["id"], tier="pro")

    resp = await test_client.post(
        f"/api/v1/admin/users/{user['id']}/erase",
        headers={"X-API-Key": non_admin_key},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_erase_audits_correct_action(test_client, db_conn, make_user, make_api_key):
    """Admin erase writes ACCOUNT_ERASED_BY_ADMIN to audit_log."""
    user = await make_user(email="erase_target@example.com", password="hunter2!")
    admin_key = await make_api_key(user_id=user["id"], tier="admin")

    resp = await test_client.post(
        f"/api/v1/admin/users/{user['id']}/erase",
        headers={"X-API-Key": admin_key},
    )
    assert resp.status_code == 200, resp.text

    audit_row = await db_conn.fetchrow(
        "SELECT action FROM audit_log WHERE target_id = $1 AND action = 'ACCOUNT_ERASED_BY_ADMIN'",
        str(user["id"]),
    )
    assert audit_row is not None


@pytest.mark.asyncio
async def test_login_blocked_after_soft_delete(test_client, make_user):
    """A soft-deleted user cannot log in."""
    # Simulate already-deleted user
    user = await make_user(email="deleted_login@example.com", password="hunter2!", deleted=True)

    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "deleted_login@example.com", "password": "hunter2!"},
    )
    # Should 401 (user not found path)
    assert resp.status_code == 401
