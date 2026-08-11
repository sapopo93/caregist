from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
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


def test_delivery_payload_preserves_date_and_timestamp_semantics():
    row = {
        "public_event_id": "11111111-1111-1111-1111-111111111111",
        "schema_version": 1,
        "event_type": "new_registration",
        "location_id": "1-12345",
        "provider_id": "1-99999",
        "effective_date": date(2026, 8, 8),
        "effective_at": None,
        "effective_date_source": "cqc.registrationDate",
        "observed_at": datetime(2026, 8, 9, 10, tzinfo=UTC),
        "source_published_at": None,
        "source_checked_at": datetime(2026, 8, 9, 9, tzinfo=UTC),
    }

    payload = delivery_outbox._payload(row)

    assert payload["effective_date"] == "2026-08-08"
    assert payload["effective_at"] is None
    assert payload["effective_date_source"] == "cqc.registrationDate"
    assert payload["first_observed_at"] == "2026-08-09T10:00:00+00:00"
    assert payload["effective_timing_statement"] == (
        "CQC published the effective date as 2026-08-08."
    )


def test_delivery_payload_keeps_unknown_effective_time_null():
    row = {
        "public_event_id": "11111111-1111-1111-1111-111111111111",
        "event_type": "status_changed",
        "location_id": "1-12345",
        "effective_date": None,
        "effective_at": None,
        "effective_date_source": None,
        "observed_at": datetime(2026, 8, 9, 10, tzinfo=UTC),
    }

    payload = delivery_outbox._payload(row)

    assert payload["effective_date"] is None
    assert payload["effective_at"] is None
    assert payload["effective_date_source"] is None
    assert payload["effective_timing_statement"] == (
        "CQC did not publish an effective timestamp; CareGist first observed "
        "this change at 2026-08-09T10:00:00+00:00."
    )


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
