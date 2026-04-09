"""Tests for email verification and gated authentication flows."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.routers.auth import (
    LoginRequest,
    RegisterRequest,
    VerifyEmailRequest,
    _hash_password,
    login,
    register,
    verify_email,
)


@asynccontextmanager
async def _noop_transaction():
    yield


@pytest.mark.asyncio
async def test_register_requires_email_verification_and_sends_email():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": 1, "email": "alice@example.com", "name": "Alice"},
        ]
    )
    conn.execute = AsyncMock()
    conn.transaction = lambda: _noop_transaction()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._send_verification_email", AsyncMock()) as send_email:
        response = await register(
            RegisterRequest(
                email="alice@example.com",
                name="Alice",
                password="SuperSecret123",
            )
        )

    assert response["tier"] == "free"
    assert response["verification_required"] is True
    assert "verify your email" in response["message"].lower()
    send_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_blocks_unverified_user():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "email": "alice@example.com",
            "name": "Alice",
            "password_hash": _hash_password("SuperSecret123"),
            "is_verified": False,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await login(LoginRequest(email="alice@example.com", password="SuperSecret123"))

    assert exc.value.status_code == 403
    assert "Verify your email" in exc.value.detail


@pytest.mark.asyncio
async def test_verify_email_activates_account():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": 1, "email": "alice@example.com"})
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        response = await verify_email(VerifyEmailRequest(token="verify-token"))

    assert response["email"] == "alice@example.com"
    assert "verified" in response["message"].lower()
    conn.execute.assert_awaited_once()
