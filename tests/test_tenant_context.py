"""Tenant workspace provisioning tests."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from api.services.tenant_context import resolve_organization_context


@asynccontextmanager
async def _noop_transaction():
    yield


@pytest.mark.asyncio
async def test_existing_membership_is_returned_without_writes():
    row = {
        "organization_id": UUID("00000000-0000-0000-0000-000000000001"),
        "role": "owner",
        "plan_tier": "free",
        "scope_config": {},
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=row)
    conn.transaction = lambda: _noop_transaction()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.services.tenant_context.get_connection", mock_get_connection):
        context = await resolve_organization_context(12, "free")

    assert context.organization_id == row["organization_id"]
    assert context.user_id == 12
    conn.fetchval.assert_not_awaited()
    conn.execute.assert_not_awaited()


def test_shared_workspace_is_preferred_over_personal_sandbox():
    from pathlib import Path

    source = (Path(__file__).parents[1] / "api/services/tenant_context.py").read_text(encoding="utf-8")
    assert "o.created_by_user_id IS DISTINCT FROM $1" in source


@pytest.mark.asyncio
async def test_missing_membership_is_provisioned_idempotently():
    row = {
        "organization_id": UUID("00000000-0000-0000-0000-000000000012"),
        "role": "owner",
        "plan_tier": "free",
        "scope_config": {},
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[None, row])
    conn.fetchval = AsyncMock(return_value=row["organization_id"])
    conn.execute = AsyncMock()
    conn.transaction = lambda: _noop_transaction()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.services.tenant_context.get_connection", mock_get_connection):
        context = await resolve_organization_context(12, "free")

    assert context.organization_id == row["organization_id"]
    assert conn.fetchrow.await_count == 2
    assert any("INSERT INTO organization_members" in call.args[0] for call in conn.execute.await_args_list)
    assert any("INSERT INTO organization_subscriptions" in call.args[0] for call in conn.execute.await_args_list)


@pytest.mark.asyncio
async def test_unknown_user_fails_without_creating_membership():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    conn.transaction = lambda: _noop_transaction()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.services.tenant_context.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await resolve_organization_context(999, "free")

    assert exc.value.status_code == 409
    assert not any("INSERT INTO organization_members" in call.args[0] for call in conn.execute.await_args_list)
