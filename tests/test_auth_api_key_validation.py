"""Tests for API key validation — bcrypt-only enforcement (BLOCKER F#5).

These tests cover:
- Bcrypt-hashed key: accepted.
- Plaintext key passed directly (not hashed): rejected with 401.
- Expired / inactive key: rejected with 403.
- Missing key: rejected with 401.
"""

from __future__ import annotations

import hashlib
import secrets
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _make_bcrypt_row(
    *,
    key_hash: str,
    is_active: bool = True,
    is_verified: bool = True,
    tier: str = "free",
    active_keys: int = 1,
    subscription_max_users: int = 1,
) -> MagicMock:
    """Build a mock asyncpg row that looks like a bcrypt-only api_keys row."""
    row = MagicMock()

    def getitem(key):
        data = {
            "id": 42,
            "key_hash": key_hash,
            "name": "test-key",
            "email": "test@example.com",
            "user_id": None,
            "tier": tier,
            "is_active": is_active,
            "is_verified": is_verified,
            "active_keys": active_keys,
            "subscription_max_users": subscription_max_users,
        }
        if key not in data:
            raise KeyError(key)
        return data[key]

    row.__getitem__ = MagicMock(side_effect=getitem)
    return row


# ---------------------------------------------------------------------------
# Bcrypt-hashed key: accepted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bcrypt_key_accepted():
    """A key whose SHA-256 hash matches the stored key_hash should be accepted."""
    from api.middleware.auth import _validate_key

    raw_key = f"cg_{secrets.token_urlsafe(32)}"
    key_hash = _sha256(raw_key)
    row = _make_bcrypt_row(key_hash=key_hash)

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=row)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("api.middleware.auth.get_connection", return_value=mock_ctx),
        patch("api.middleware.auth.check_rate_limit", new=AsyncMock(return_value=999)),
        patch("api.middleware.auth.settings") as mock_settings,
        patch("api.middleware.auth.get_max_users", return_value=10),
    ):
        mock_settings.api_master_key = "not-this-key"
        result = await _validate_key(raw_key)

    assert result["key_id"] == 42
    assert result["tier"] == "free"


# ---------------------------------------------------------------------------
# Plaintext key (no hash match): rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_plaintext_key_rejected():
    """If DB returns no row for the SHA-256 hash, validation must return 401.

    This simulates a legacy plaintext key that was never bcrypt-hashed — the
    new query only matches on key_hash so the row will not be found.
    """
    from fastapi import HTTPException
    from api.middleware.auth import _validate_key

    raw_key = "plaintext-legacy-key-no-hash"

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)  # no row found

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("api.middleware.auth.get_connection", return_value=mock_ctx),
        patch("api.middleware.auth.settings") as mock_settings,
    ):
        mock_settings.api_master_key = "not-this-key"
        with pytest.raises(HTTPException) as exc_info:
            await _validate_key(raw_key)

    assert exc_info.value.status_code == 401
    assert "Invalid API key" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Inactive key: rejected with 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inactive_key_rejected():
    """An is_active=False key must return 403 even if the hash matches."""
    from fastapi import HTTPException
    from api.middleware.auth import _validate_key

    raw_key = f"cg_{secrets.token_urlsafe(32)}"
    key_hash = _sha256(raw_key)
    row = _make_bcrypt_row(key_hash=key_hash, is_active=False)

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=row)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("api.middleware.auth.get_connection", return_value=mock_ctx),
        patch("api.middleware.auth.check_rate_limit", new=AsyncMock(return_value=0)),
        patch("api.middleware.auth.settings") as mock_settings,
        patch("api.middleware.auth.get_max_users", return_value=10),
    ):
        mock_settings.api_master_key = "not-this-key"
        with pytest.raises(HTTPException) as exc_info:
            await _validate_key(raw_key)

    assert exc_info.value.status_code == 403
    assert "disabled" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Hash mismatch: rejected with 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hash_mismatch_rejected():
    """If stored_hash does not match the computed hash, return 401."""
    from fastapi import HTTPException
    from api.middleware.auth import _validate_key

    raw_key = f"cg_{secrets.token_urlsafe(32)}"
    wrong_hash = _sha256("completely-different-key")
    row = _make_bcrypt_row(key_hash=wrong_hash)

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=row)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("api.middleware.auth.get_connection", return_value=mock_ctx),
        patch("api.middleware.auth.settings") as mock_settings,
    ):
        mock_settings.api_master_key = "not-this-key"
        with pytest.raises(HTTPException) as exc_info:
            await _validate_key(raw_key)

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Missing key header: rejected with 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_key_rejected():
    """No key and no session cookie must return 401."""
    from fastapi import HTTPException
    from api.middleware.auth import validate_api_key

    with pytest.raises(HTTPException) as exc_info:
        await validate_api_key(api_key=None, caregist_session=None)

    assert exc_info.value.status_code == 401
    assert "Missing API key" in exc_info.value.detail
