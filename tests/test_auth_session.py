"""Tests for opaque server-side session management (F#1 fix).

Covers: creation, validation, expiry rejection, revocation, tampered ID rejection,
and cookie attributes on login/logout.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import Response as FastAPIResponse

from api.utils.sessions import create_session, revoke_session, touch_session, validate_session


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_session_returns_urlsafe_token():
    """create_session returns a string that looks like a 43-char URL-safe-base64 token."""
    conn = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        sid = await create_session(user_id=1)

    assert isinstance(sid, str)
    # secrets.token_urlsafe(32) produces 43 base64url characters
    assert len(sid) == 43
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert set(sid) <= allowed, f"Non-URL-safe chars in session_id: {sid!r}"


@pytest.mark.asyncio
async def test_create_session_inserts_row_with_correct_fields():
    """create_session inserts a row binding user_id and captures user_agent / ip."""
    conn = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        sid = await create_session(user_id=42, user_agent="pytest/1.0", ip="127.0.0.1")

    call_args = conn.execute.await_args.args
    sql, session_id, user_id, expires_at, user_agent, ip = call_args
    assert "INSERT INTO sessions" in sql
    assert session_id == sid
    assert user_id == 42
    assert user_agent == "pytest/1.0"
    assert ip == "127.0.0.1"
    # expires_at should be ~30 days from now
    now = datetime.now(timezone.utc)
    assert timedelta(days=29) < (expires_at - now) < timedelta(days=31)


# ---------------------------------------------------------------------------
# validate_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_session_returns_user_id_for_valid_session():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"user_id": 99})

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        result = await validate_session("valid-session-id")

    assert result == 99
    query = conn.fetchrow.await_args.args[0]
    assert "expires_at > NOW()" in query
    assert "revoked_at IS NULL" in query


@pytest.mark.asyncio
async def test_validate_session_returns_none_when_not_found():
    """A tampered or unknown session_id returns None (not an exception)."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        result = await validate_session("tampered-or-unknown")

    assert result is None


@pytest.mark.asyncio
async def test_validate_session_returns_none_for_expired_session():
    """Expired sessions are filtered by the SQL WHERE clause — DB returns None."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)  # DB returns nothing for expired rows

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        result = await validate_session("expired-session-id")

    assert result is None


@pytest.mark.asyncio
async def test_validate_session_returns_none_for_revoked_session():
    """Revoked sessions are filtered by revoked_at IS NULL — DB returns None."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        result = await validate_session("revoked-session-id")

    assert result is None


# ---------------------------------------------------------------------------
# revoke_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_revoke_session_sets_revoked_at():
    conn = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        await revoke_session("session-abc")

    query, session_id = conn.execute.await_args.args
    assert "revoked_at = NOW()" in query
    assert session_id == "session-abc"


# ---------------------------------------------------------------------------
# touch_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_touch_session_updates_last_used_at():
    conn = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.sessions.get_connection", mock_get_connection):
        await touch_session("session-xyz")

    query, session_id = conn.execute.await_args.args
    assert "last_used_at = NOW()" in query
    assert session_id == "session-xyz"


# ---------------------------------------------------------------------------
# Login endpoint: cookie attributes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_sets_httponly_secure_samesite_cookie():
    """Login must set caregist_session with HttpOnly, Secure, SameSite=Lax.

    The cookie value must NOT be the bearer token (F#1 fix).
    """
    from api.routers.auth import LoginRequest, login, _hash_password

    user = {
        "id": 1,
        "email": "alice@example.com",
        "name": "Alice",
        "password_hash": "$2b$already-bcrypt",
        "is_verified": True,
    }
    key_row = {"id": 7, "key": None, "tier": "free", "rate_limit": 2}

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[user, key_row])
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    fake_request = MagicMock()
    fake_request.headers.get = MagicMock(side_effect=lambda k, d="": "Mozilla" if k == "user-agent" else d)
    fake_request.client = MagicMock(host="127.0.0.1")

    response = FastAPIResponse()
    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._verify_password", return_value=True), \
         patch("api.routers.auth.write_audit_log", AsyncMock()), \
         patch("api.routers.auth.create_session", AsyncMock(return_value="opaque-session-id-43chars00000")):
        await login(LoginRequest(email="alice@example.com", password="pw"), response, fake_request)

    cookie_header = response.headers.get("set-cookie", "")
    assert "caregist_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header
    assert "SameSite=lax" in cookie_header

    # CRITICAL: cookie value must be the opaque session ID, not the bearer token
    cookie_value = cookie_header.split("caregist_session=", 1)[1].split(";", 1)[0]
    assert cookie_value == "opaque-session-id-43chars00000"
    # Sanity: must not be a bearer token (starts with cg_)
    assert not cookie_value.startswith("cg_")


# ---------------------------------------------------------------------------
# Logout endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie():
    from api.routers.auth import logout_session

    conn = AsyncMock()
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    response = FastAPIResponse()
    with patch("api.utils.sessions.get_connection", mock_get_connection):
        result = await logout_session(response, caregist_session="some-session-id")

    assert result == {"logged_out": True}

    revoke_query, revoke_sid = conn.execute.await_args.args
    assert "revoked_at = NOW()" in revoke_query
    assert revoke_sid == "some-session-id"

    cookie_header = response.headers.get("set-cookie", "")
    # Cookie should be cleared (max-age=0 or expires in past)
    assert "caregist_session" in cookie_header


@pytest.mark.asyncio
async def test_logout_without_cookie_still_returns_ok():
    """Logout without a session cookie returns {logged_out: True} without erroring."""
    from api.routers.auth import logout_session

    response = FastAPIResponse()
    result = await logout_session(response, caregist_session=None)
    assert result == {"logged_out": True}
