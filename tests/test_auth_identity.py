"""Tests for stable auth identity derived from API keys."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.middleware.auth import validate_api_key
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
        }
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.middleware.auth.get_connection", mock_get_connection), \
         patch("api.middleware.auth.check_rate_limit", return_value={"burst_remaining": 1, "daily_remaining": 2, "rolling_7d_remaining": 3, "monthly_remaining": 4}):
        auth = await validate_api_key("cg_test_key")

    assert auth["key_id"] == 7
    assert auth["name"] == "Alice Example"
    assert auth["email"] == "alice@example.com"
    assert auth["user_id"] == 42
    assert auth["tier"] == "starter"


@pytest.mark.asyncio
async def test_comparisons_get_user_id_uses_auth_payload():
    user_id = await _get_user_id({"user_id": 123})
    assert user_id == 123


@pytest.mark.asyncio
async def test_comparisons_get_user_id_requires_user_context():
    with pytest.raises(HTTPException) as exc:
        await _get_user_id({"name": "Duplicate Name"})
    assert exc.value.status_code == 401
