"""Execute public CQC change-frequency queries against current PostgreSQL migrations."""

from __future__ import annotations

import pytest

from api.queries.public_tools import (
    CHANGE_FREQUENCY_COLLECTION_COVERAGE,
    CHANGE_FREQUENCY_DAILY,
)
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio


async def test_change_frequency_queries_use_only_complete_authoritative_reconciliations(
    fresh_db,
):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute(
            """
            INSERT INTO trusted_event_ledger (
              entity_type, entity_id, event_type, effective_date,
              observed_at, source, dedupe_key
            ) VALUES
              ('location', 'LOC-1', 'rating_changed', CURRENT_DATE,
               CURRENT_TIMESTAMP, 'integration-test', 'frequency-event-1'),
              ('location', 'LOC-2', 'status_changed', CURRENT_DATE - 1,
               CURRENT_TIMESTAMP - INTERVAL '1 day', 'integration-test', 'frequency-event-2')
            """
        )
        await conn.execute(
            """
            INSERT INTO pipeline_runs (
              run_type, status, started_at, completed_at,
              source_uri, source_retrieved_at, source_checksum_sha256,
              source_total_count, checked_count, success_count, failure_count,
              reconciled_at, counts_reconciled
            ) VALUES
              ('reconciliation', 'completed', CURRENT_TIMESTAMP - INTERVAL '2 hours',
               CURRENT_TIMESTAMP - INTERVAL '1 hour', 'https://example.test/cqc.csv',
               CURRENT_TIMESTAMP - INTERVAL '90 minutes', repeat('a', 64),
               2, 2, 2, 0, CURRENT_TIMESTAMP - INTERVAL '1 hour', TRUE),
              ('reconciliation', 'completed', CURRENT_TIMESTAMP - INTERVAL '1 day',
               CURRENT_TIMESTAMP - INTERVAL '23 hours', 'https://example.test/cqc.csv',
               CURRENT_TIMESTAMP - INTERVAL '1 day', repeat('b', 64),
               2, 1, 1, 0, NULL, FALSE),
              ('reconciliation', 'failed', CURRENT_TIMESTAMP - INTERVAL '1 day',
               CURRENT_TIMESTAMP - INTERVAL '23 hours', 'https://example.test/cqc.csv',
               NULL, NULL, 2, 1, 0, 1, NULL, FALSE),
              ('signal_poll', 'completed', CURRENT_TIMESTAMP - INTERVAL '1 day',
               CURRENT_TIMESTAMP - INTERVAL '23 hours', 'https://example.test/cqc-api',
               CURRENT_TIMESTAMP - INTERVAL '1 day', repeat('c', 64),
               2, 2, 2, 0, NULL, FALSE)
            """
        )

        daily = await conn.fetch(CHANGE_FREQUENCY_DAILY, 3)
        coverage = await conn.fetch(CHANGE_FREQUENCY_COLLECTION_COVERAGE, 3)

        assert len(daily) == 3
        assert sum(int(row["events"]) for row in daily) == 2
        assert sum(int(row["rating_changes"]) for row in daily) == 1
        assert sum(int(row["status_changes"]) for row in daily) == 1

        completed = [row for row in coverage if row["status"] == "completed"]
        failed = [row for row in coverage if row["status"] == "failed"]
        assert len(completed) == 1
        assert int(completed[0]["runs"]) == 1
        assert completed[0]["run_type"] == "reconciliation"
        assert len(failed) == 1
        assert int(failed[0]["runs"]) == 1
        assert failed[0]["run_type"] == "reconciliation"
    finally:
        await conn.close()
