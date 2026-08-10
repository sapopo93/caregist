"""Disposable-PostgreSQL proof for CQC timing and freshness invariants."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from api.services.cqc_freshness import get_cqc_freshness
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio


async def test_three_clean_reconciliations_and_stable_first_observation(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute(
            """
            INSERT INTO care_providers (id, name, slug, status)
            VALUES ('LOC-1', 'Synthetic Care', 'synthetic-care', 'ACTIVE')
            """
        )

        # Three synthetic, fully reconciled journeys. These are database
        # evidence only and make no claim about production CQC freshness.
        for hours_ago, checksum_character in ((3, "a"), (2, "b"), (1, "c")):
            await conn.execute(
                """
                INSERT INTO pipeline_runs (
                  run_type, status, started_at, completed_at,
                  source_uri, source_published_at, source_retrieved_at,
                  source_checksum_sha256, source_record_count,
                  source_total_count, checked_count, success_count, failure_count,
                  active_records_after, reconciled_at, counts_reconciled,
                  source_provenance, checkpoint_state
                ) VALUES (
                  'reconciliation', 'completed',
                  NOW() - ($1::int * INTERVAL '1 hour') - INTERVAL '5 minutes',
                  NOW() - ($1::int * INTERVAL '1 hour'),
                  'https://api.service.cqc.org.uk/public/v1/locations', CURRENT_DATE,
                  NOW() - ($1::int * INTERVAL '1 hour'), $2, 1,
                  1, 1, 1, 0, 1,
                  NOW() - ($1::int * INTERVAL '1 hour'), TRUE,
                  '{"kind":"synthetic_test"}'::jsonb,
                  '{"fullCoverage":true,"restartable":false}'::jsonb
                )
                """,
                hours_ago,
                checksum_character * 64,
            )

        assert await conn.fetchval(
            """SELECT COUNT(*) FROM pipeline_runs
               WHERE run_type = 'reconciliation' AND status = 'completed'
                 AND counts_reconciled = TRUE AND checked_count = source_total_count
                 AND success_count = checked_count AND failure_count = 0"""
        ) == 3

        freshness = await get_cqc_freshness(conn, now=datetime.now(UTC))
        repeated = await get_cqc_freshness(conn, now=datetime.now(UTC))
        assert repeated == freshness
        assert freshness["status"] == "fresh"
        assert freshness["totalSourceLocations"] == 1
        assert freshness["checkedLocations"] == 1
        assert freshness["coveragePercentage"] == 100.0
        assert freshness["countsReconciled"] is True
        assert freshness["checksumSha256"] == "c" * 64

        event_id = await conn.fetchval(
            """
            INSERT INTO trusted_event_ledger (
              entity_type, entity_id, location_id, event_type,
              effective_date, effective_at, effective_date_source,
              old_value, new_value, source, dedupe_key
            ) VALUES (
              'care_provider', 'LOC-1', 'LOC-1', 'status_changed',
              NULL, NULL, NULL, '"ACTIVE"'::jsonb, '"INACTIVE"'::jsonb,
              'cqc_api', 'status_changed:LOC-1:synthetic'
            )
            RETURNING id
            """
        )
        first_observed_at = await conn.fetchval(
            "SELECT observed_at FROM trusted_event_ledger WHERE id = $1", event_id
        )
        # A no-change/replay journey cannot overwrite first observation.
        await conn.execute(
            """
            INSERT INTO trusted_event_ledger (
              entity_type, entity_id, location_id, event_type,
              effective_date, old_value, new_value, source, dedupe_key
            ) VALUES (
              'care_provider', 'LOC-1', 'LOC-1', 'status_changed',
              NULL, '"ACTIVE"'::jsonb, '"INACTIVE"'::jsonb,
              'cqc_api', 'status_changed:LOC-1:synthetic'
            ) ON CONFLICT (dedupe_key) DO NOTHING
            """
        )
        persisted = await conn.fetchrow(
            """SELECT COUNT(*) OVER () AS event_count, observed_at, effective_date,
                      effective_at, effective_date_source
               FROM trusted_event_ledger WHERE dedupe_key = $1""",
            "status_changed:LOC-1:synthetic",
        )
        assert persisted["event_count"] == 1
        assert persisted["observed_at"] == first_observed_at
        assert persisted["effective_date"] is None
        assert persisted["effective_at"] is None
        assert persisted["effective_date_source"] is None
    finally:
        await conn.close()


async def test_partial_reconciliation_does_not_advance_watermark(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        watermark_id = await conn.fetchval(
            """
            INSERT INTO pipeline_runs (
              run_type, status, started_at, completed_at, source_uri,
              source_retrieved_at, source_checksum_sha256,
              source_total_count, checked_count, success_count, failure_count,
              reconciled_at, counts_reconciled
            ) VALUES (
              'reconciliation', 'completed', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour',
              'https://api.service.cqc.org.uk/public/v1/locations', NOW() - INTERVAL '1 hour',
              $1, 2, 2, 2, 0, NOW() - INTERVAL '1 hour', TRUE
            ) RETURNING id
            """,
            "d" * 64,
        )
        await conn.execute(
            """
            INSERT INTO pipeline_runs (
              run_type, status, started_at, completed_at, source_uri,
              source_total_count, checked_count, success_count, failure_count,
              counts_reconciled, error_message
            ) VALUES (
              'reconciliation', 'partial', NOW() - INTERVAL '30 minutes', NOW() - INTERVAL '20 minutes',
              'https://api.service.cqc.org.uk/public/v1/locations',
              2, 1, 1, 0, FALSE, 'synthetic interruption'
            )
            """
        )

        result = await get_cqc_freshness(conn, now=datetime.now(UTC))
        assert result["status"] == "partial"
        assert result["reason"] == "latest_authoritative_attempt_incomplete"
        assert result["sourceRetrievedAt"] is not None
        assert result["latestAttempt"]["status"] == "partial"
        assert await conn.fetchval(
            "SELECT id FROM pipeline_runs WHERE counts_reconciled = TRUE ORDER BY source_retrieved_at DESC LIMIT 1"
        ) == watermark_id
    finally:
        await conn.close()
