"""Tests for stable auth identity derived from API keys."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.middleware.auth import hash_api_key, validate_api_key
from api.routers.auth import LoginRequest, TeamKeyCreateRequest, create_team_key, logout_session, reveal_key, rotate_key
from api.routers.comparisons import _get_user_id


@pytest.mark.asyncio
async def test_validate_api_key_returns_user_context():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 7,
            "key_hash": hash_api_key("cg_test_key"),
            "name": "Alice Example",
            "email": "alice@example.com",
            "user_id": 42,
            "tier": "starter",
            "is_active": True,
            "is_verified": True,
            "active_keys": 1,
            "subscription_max_users": 3,
        }
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection), \
         patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value={"burst_remaining": 1, "daily_remaining": 2, "rolling_7d_remaining": 3, "monthly_remaining": 4})):
        auth = await validate_api_key("cg_test_key")

    assert auth["key_id"] == 7
    assert auth["name"] == "Alice Example"
    assert auth["email"] == "alice@example.com"
    assert auth["user_id"] == 42
    assert auth["tier"] == "starter"


@pytest.mark.asyncio
async def test_validate_api_key_blocks_unverified_user():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 7,
            "key_hash": hash_api_key("cg_test_key"),
            "name": "Alice Example",
            "email": "alice@example.com",
            "user_id": 42,
            "tier": "starter",
            "is_active": True,
            "is_verified": False,
            "active_keys": 1,
            "subscription_max_users": 3,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await validate_api_key("cg_test_key")

    assert exc.value.status_code == 403
    assert "Verify your email" in exc.value.detail


@pytest.mark.asyncio
async def test_comparisons_get_user_id_uses_auth_payload():
    user_id = await _get_user_id({"user_id": 123})
    assert user_id == 123


@pytest.mark.asyncio
async def test_comparisons_get_user_id_requires_user_context():
    with pytest.raises(HTTPException) as exc:
        await _get_user_id({"name": "Duplicate Name"})
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_validate_api_key_rejects_key_outside_seat_limit():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 7,
            "key_hash": hash_api_key("cg_test_key"),
            "name": "Alice Example",
            "email": "alice@example.com",
            "user_id": 42,
            "tier": "pro",
            "is_active": True,
            "is_verified": True,
            "active_keys": 4,
            "subscription_max_users": 2,
        }
    )
    conn.fetch = AsyncMock(return_value=[{"id": 1}, {"id": 2}, {"id": 3}])
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection), \
         patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value={"burst_remaining": 1, "daily_remaining": 2, "rolling_7d_remaining": 3, "monthly_remaining": 4})):
        with pytest.raises(HTTPException) as exc:
            await validate_api_key("cg_test_key")

    assert exc.value.status_code == 403
    assert "seat limit" in exc.value.detail


@pytest.mark.asyncio
async def test_validate_api_key_honours_paid_tier_seat_floor_when_subscription_is_stale():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 7,
            "key_hash": hash_api_key("cg_test_key"),
            "name": "Alice Example",
            "email": "alice@example.com",
            "user_id": 42,
            "tier": "business",
            "is_active": True,
            "is_verified": True,
            "active_keys": 1,
            "subscription_max_users": 1,
        }
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection), \
         patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value={"burst_remaining": 1, "daily_remaining": 2, "rolling_7d_remaining": 3, "monthly_remaining": 4})):
        auth = await validate_api_key("cg_test_key")

    assert auth["tier"] == "business"
    conn.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_api_key_rejects_invalid_hash_match():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await validate_api_key("cg_wrong_key")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_active_session_cookie_returns_user_context():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 7,
            "key": None,
            "key_hash": hash_api_key("cg_backing_key"),
            "name": "Alice Example",
            "email": "alice@example.com",
            "user_id": 42,
            "tier": "starter",
            "is_active": True,
            "is_verified": True,
            "active_keys": 1,
            "subscription_max_users": 3,
        }
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection), \
         patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value={"burst_remaining": 1, "daily_remaining": 2, "rolling_7d_remaining": 3, "monthly_remaining": 4})):
        auth = await validate_api_key(api_key=None, caregist_session="cs_active_session")

    assert auth["key_id"] == 7
    assert auth["user_id"] == 42
    assert auth["tier"] == "starter"
    assert auth["api_key"] is None


@pytest.mark.asyncio
async def test_valid_session_cookie_wins_over_stale_header_key():
    session_row = {
        "id": 7,
        "key": None,
        "key_hash": hash_api_key("cg_backing_key"),
        "name": "Alice Example",
        "email": "alice@example.com",
        "user_id": 42,
        "tier": "business",
        "is_active": True,
        "is_verified": True,
        "active_keys": 1,
        "subscription_max_users": 10,
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[None, session_row])
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection), \
         patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value={"burst_remaining": 1, "daily_remaining": 2, "rolling_7d_remaining": 3, "monthly_remaining": 4})):
        auth = await validate_api_key(api_key="cg_stale_key", caregist_session="cs_active_session")

    assert auth["user_id"] == 42
    assert auth["tier"] == "business"
    assert auth["api_key"] is None


@pytest.mark.asyncio
async def test_legacy_api_key_session_cookie_still_authenticates():
    key_row = {
        "id": 7,
        "key": None,
        "key_hash": hash_api_key("cg_legacy_cookie_key"),
        "name": "Alice Example",
        "email": "alice@example.com",
        "user_id": 42,
        "tier": "starter",
        "is_active": True,
        "is_verified": True,
        "active_keys": 1,
        "subscription_max_users": 3,
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[None, key_row])
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection), \
         patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value={"burst_remaining": 1, "daily_remaining": 2, "rolling_7d_remaining": 3, "monthly_remaining": 4})):
        auth = await validate_api_key(api_key=None, caregist_session="cg_legacy_cookie_key")

    assert auth["user_id"] == 42
    assert auth["tier"] == "starter"
    assert auth["api_key"] == "cg_legacy_cookie_key"


@pytest.mark.asyncio
async def test_revoked_session_cookie_is_rejected():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await validate_api_key(api_key=None, caregist_session="cs_revoked_session")

    assert exc.value.status_code == 401
    assert "session" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_logout_revokes_presented_session_cookie():
    conn = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        response = await logout_session(caregist_session="cs_active_session", response=MagicMock())

    assert response == {"logged_out": True}
    query, token_hash = conn.execute.await_args.args
    assert "UPDATE user_sessions SET revoked_at" in query
    assert token_hash == hash_api_key("cs_active_session")


@pytest.mark.asyncio
async def test_create_team_key_blocks_when_capacity_reached():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"active_keys": 3, "max_users": 3})
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await create_team_key(
                TeamKeyCreateRequest(name="Ops Seat", email="ops@example.com"),
                {"user_id": 42, "tier": "pro", "is_verified": True},
            )

    assert exc.value.status_code == 403
    assert "named access seats" in exc.value.detail


@pytest.mark.asyncio
async def test_create_team_key_requires_verified_email():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await create_team_key(
                TeamKeyCreateRequest(name="Ops Seat", email="ops@example.com"),
                {"user_id": 42, "tier": "pro", "is_verified": False},
            )

    assert exc.value.status_code == 403
    assert "Verify your email" in exc.value.detail


@pytest.mark.asyncio
async def test_create_team_key_uses_paid_tier_capacity_when_subscription_row_is_stale():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"active_keys": 1, "max_users": 1})
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        result = await create_team_key(
            TeamKeyCreateRequest(name="Ops Seat", email="ops@example.com"),
            {"user_id": 42, "tier": "business", "is_verified": True},
        )

    assert result["email"] == "ops@example.com"
    conn.execute.assert_awaited()
    args = next(call.args for call in conn.execute.await_args_list if "key_hash" in call.args[0])
    assert "key_hash" in args[0]
    assert args[1] != result["api_key"]
    assert args[1] == hash_api_key(result["api_key"])
    audit_args = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_args[1] == "api_key.create"
    assert result["api_key"] not in repr(audit_args)


@pytest.mark.asyncio
async def test_reveal_key_does_not_return_hashed_key():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "password_hash": "salted:unused", "is_verified": True},
            {"key": None, "key_prefix": "cg_secret_", "tier": "free", "rate_limit": 2},
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._verify_password", return_value=True):
        result = await reveal_key(LoginRequest(email="alice@example.com", password="password123"))

    assert result["api_key"] is None
    assert result["masked_key"] == "cg_secret_…"
    assert "Rotate" in result["message"] or "rotate" in result["message"]


@pytest.mark.asyncio
async def test_rotate_key_stores_hash_and_returns_new_key_once():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "name": "Alice", "password_hash": "salted:unused", "is_verified": True},
            {"tier": "starter", "rate_limit": 10},
        ]
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._verify_password", return_value=True):
        result = await rotate_key(LoginRequest(email="alice@example.com", password="password123"))

    insert_call = next(call.args for call in conn.execute.await_args_list if "key_hash" in call.args[0])
    assert "key_hash" in insert_call[0]
    assert insert_call[1] == hash_api_key(result["api_key"])
    assert insert_call[1] != result["api_key"]
    assert result["tier"] == "starter"
    audit_args = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_args[1] == "api_key.rotate"
    assert result["api_key"] not in repr(audit_args)
