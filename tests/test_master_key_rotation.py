"""Tests for master-key rotation window + audit on use (F-18)."""

from unittest.mock import AsyncMock, patch

import pytest

from api.middleware import auth


@pytest.mark.asyncio
async def test_rotation_key_is_accepted_and_audited():
    with patch.object(type(auth.settings), "master_keys", lambda self: ("new-key", "old-key")), \
         patch.object(auth, "check_rate_limit", AsyncMock(return_value={})), \
         patch.object(auth, "write_audit_log", AsyncMock()) as audit:
        # The previous (rotation) key still authenticates during the overlap.
        result = await auth._validate_key("old-key")

    assert result["tier"] == "admin"
    assert result["name"] == "master"
    assert result["api_key"] is None
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "auth.master_key.use"
    # The raw key is never logged — only its prefix.
    assert "old-key"[:4] in audit.await_args.kwargs["metadata"]["key_prefix"]


@pytest.mark.asyncio
async def test_audit_failure_does_not_block_master_auth():
    with patch.object(type(auth.settings), "master_keys", lambda self: ("the-key",)), \
         patch.object(auth, "check_rate_limit", AsyncMock(return_value={})), \
         patch.object(auth, "write_audit_log", AsyncMock(side_effect=RuntimeError("db down"))):
        result = await auth._validate_key("the-key")

    assert result["tier"] == "admin"


@pytest.mark.asyncio
async def test_non_master_key_does_not_short_circuit_to_admin():
    # A non-master key must fall through to the DB lookup, not be treated as admin.
    with patch.object(type(auth.settings), "master_keys", lambda self: ("the-master",)), \
         patch.object(auth, "check_rate_limit", AsyncMock(return_value={})), \
         patch.object(auth, "get_connection") as get_conn:
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)  # key not found
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)
        get_conn.return_value = cm

        with pytest.raises(auth.HTTPException) as exc:
            await auth._validate_key("some-random-user-key")

    assert exc.value.status_code == 401
