from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from api.services import delivery_outbox


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _Connection:
    def __init__(self):
        self.executions: list[tuple[str, tuple]] = []
        self.closed = False

    def transaction(self):
        return _Transaction()

    async def execute(self, query: str, *args):
        self.executions.append((query, args))
        return "UPDATE 0"

    async def fetch(self, query: str, *_args):
        assert "FOR UPDATE OF outbox SKIP LOCKED" in query
        return []

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_claim_batch_reclaims_expired_processing_leases_before_claiming():
    conn = _Connection()

    async def connect(_database_url: str):
        return conn

    with patch.object(delivery_outbox.asyncpg, "connect", connect):
        assert await delivery_outbox._claim_batch("postgresql://test", 25) == []

    reclaim_query, reclaim_args = conn.executions[1]
    assert "status = 'processing'" in reclaim_query
    assert "SET status = 'pending'" in reclaim_query
    assert reclaim_args == (timedelta(minutes=15),)
    assert conn.closed is True


@pytest.mark.asyncio
async def test_delivery_worker_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(delivery_outbox.settings, "radar_delivery_enabled", False)

    async def must_not_claim(*_args, **_kwargs):
        raise AssertionError("disabled delivery must not connect to the database")

    monkeypatch.setattr(delivery_outbox, "_claim_batch", must_not_claim)
    assert await delivery_outbox.process_delivery_outbox("postgresql://unused") == {
        "claimed": 0,
        "delivered": 0,
        "failed": 0,
        "filtered": 0,
    }
