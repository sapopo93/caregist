"""Disposable-PostgreSQL proof for the bounded reconciliation resume wave."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import psycopg2
import pytest

from incremental_update import (
    CqcActiveSnapshot,
    ChangesFetchError,
    _resume_batch,
    build_snapshot_manifest,
)
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio


async def test_resume_preserves_checkpoint_and_refuses_a_second_wave(fresh_db, tmp_path):
    async_conn = await asyncpg.connect(fresh_db)
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000", "1-10001", "1-10002", "1-10003"}),
    )
    manifest = build_snapshot_manifest(snapshot, batch_id, 1)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    try:
        await apply_full_schema(async_conn)
        pipeline_run_id = await async_conn.fetchval(
            """
            INSERT INTO pipeline_runs (
              run_type, status, source_total_count, source_provenance,
              checkpoint_state, counts_reconciled
            ) VALUES (
              'reconciliation', 'failed', 4, '{}'::jsonb,
              '{"resumeWaves":0,"restartable":true}'::jsonb, FALSE
            ) RETURNING id
            """
        )
        await async_conn.execute(
            """
            INSERT INTO reconciliation_batches (
              id, pipeline_run_id, source_uri, source_published_at, source_retrieved_at,
              source_checksum_sha256, manifest_checksum_sha256, location_count,
              shard_count, status, active_records_before
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 4, 1, 'failed', 4)
            """,
            batch_id,
            pipeline_run_id,
            snapshot.source_uri,
            date.fromisoformat(snapshot.source_published_at),
            snapshot.retrieved_at,
            snapshot.checksum_sha256,
            manifest["manifestChecksumSha256"],
        )
        await async_conn.execute(
            """
            INSERT INTO reconciliation_shards (
              batch_id, shard_index, status, manifest_checksum_sha256,
              expected_count, next_offset, processed_count
            ) VALUES ($1, 0, 'failed', $2, 4, 2, 2)
            """,
            batch_id,
            manifest["manifestChecksumSha256"],
        )
    finally:
        await async_conn.close()

    args = SimpleNamespace(
        batch_id=str(batch_id),
        snapshot_manifest=str(manifest_path),
        dry_run=False,
        release_sha="a" * 40,
        workflow_run_id="123",
        workflow_run_attempt="1",
    )
    lock_holder = psycopg2.connect(fresh_db)
    try:
        with lock_holder.cursor() as lock_cursor:
            lock_cursor.execute(
                "SELECT pg_advisory_lock(hashtextextended(%s, 0))",
                (f"cqc-reconciliation:{batch_id}:0",),
            )
        sync_conn = psycopg2.connect(fresh_db)
        try:
            with pytest.raises(ChangesFetchError, match="still running"):
                _resume_batch(args, sync_conn, sync_conn.cursor())
            sync_conn.rollback()
        finally:
            sync_conn.close()
    finally:
        with lock_holder.cursor() as lock_cursor:
            lock_cursor.execute(
                "SELECT pg_advisory_unlock(hashtextextended(%s, 0))",
                (f"cqc-reconciliation:{batch_id}:0",),
            )
        lock_holder.close()

    sync_conn = psycopg2.connect(fresh_db)
    try:
        assert _resume_batch(args, sync_conn, sync_conn.cursor()) == 0
    finally:
        sync_conn.close()

    async_conn = await asyncpg.connect(fresh_db)
    try:
        batch = await async_conn.fetchrow(
            "SELECT status, pipeline_run_id FROM reconciliation_batches WHERE id = $1", batch_id
        )
        run = await async_conn.fetchrow(
            "SELECT status, checkpoint_state FROM pipeline_runs WHERE id = $1",
            batch["pipeline_run_id"],
        )
        shard = await async_conn.fetchrow(
            """SELECT status, next_offset, processed_count
               FROM reconciliation_shards WHERE batch_id = $1 AND shard_index = 0""",
            batch_id,
        )
        assert batch["status"] == "prepared"
        assert run["status"] == "running"
        checkpoint_state = run["checkpoint_state"]
        if isinstance(checkpoint_state, str):
            checkpoint_state = json.loads(checkpoint_state)
        assert checkpoint_state["resumeWaves"] == 1
        assert tuple(shard.values()) == ("failed", 2, 2)

        await async_conn.execute(
            "UPDATE reconciliation_batches SET status = 'failed' WHERE id = $1", batch_id
        )
        await async_conn.execute(
            "UPDATE pipeline_runs SET status = 'failed' WHERE id = $1", batch["pipeline_run_id"]
        )
    finally:
        await async_conn.close()

    sync_conn = psycopg2.connect(fresh_db)
    try:
        with pytest.raises(ChangesFetchError, match="already used its single resume wave"):
            _resume_batch(args, sync_conn, sync_conn.cursor())
        sync_conn.rollback()
    finally:
        sync_conn.close()
