"""Tests for stable auth identity derived from API keys."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.middleware.auth import validate_api_key
from api.routers.auth import TeamKeyCreateRequest, create_team_key
from api.routers.comparisons import _get_user_id


@pytest.mark.asyncio
async def test_validate_api_key_returns_user_context():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 7,
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
