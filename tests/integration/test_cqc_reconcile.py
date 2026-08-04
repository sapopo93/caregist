from __future__ import annotations

import uuid
import threading
import time
from datetime import date, datetime, timezone
from types import SimpleNamespace

import asyncpg
import psycopg2
import psycopg2.extras
import pytest

from api.services.pipeline_health import get_pipeline_health
from incremental_update import INCREMENTAL_UPDATE_LOCK_ID
from tools import cqc_reconcile as reconcile
from tools.cqc_reconcile import CONFIRM_PHRASE, CqcSnapshot, ReconciliationError

from .conftest import MIGRATIONS_DIR, apply_full_schema, apply_schema_through


def _details(location_id: str) -> dict:
    return {
        "locationId": location_id,
        "providerId": f"P-{location_id}",
        "name": f"Provider {location_id}",
        "registrationStatus": "Registered",
        "registrationDate": "2026-07-01",
        "postalAddressTownCity": "Test Town",
        "postalCode": "AA1 1AA",
        "region": "Test Region",
        "lastUpdated": "2026-08-04T08:00:00Z",
    }


def _args(batch_id: uuid.UUID, manifest_path, counts: dict[str, int], **overrides):
    values = {
        "batch_id": str(batch_id),
        "manifest": str(manifest_path) if manifest_path is not None else None,
        "data_page_url": reconcile.DEFAULT_DATA_PAGE_URL,
        "api_base_url": reconcile.DEFAULT_API_BASE_URL,
        "shard_count": 2,
        "shard_index": None,
        "checkpoint_size": 1,
        "sleep": 0,
        "max_deactivations": counts["deactivationCount"],
        "dry_run": False,
        "confirm_phrase": CONFIRM_PHRASE,
        "confirm_source_sha256": "a" * 64,
        "confirm_source_published_at": date.today().isoformat(),
        "confirm_source_count": counts["sourceCount"],
        "confirm_current_count": counts["currentCount"],
        "confirm_intersection_count": counts["intersectionCount"],
        "confirm_addition_count": counts["additionCount"],
        "confirm_reactivation_count": counts["reactivationCount"],
        "confirm_deactivation_count": counts["deactivationCount"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_schema_at_046_upgrades_cleanly_to_durable_reconciliation(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        applied = await apply_schema_through(conn, 46)
        assert "046_billing_operations.sql" in applied
        assert not await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cqc_reconciliation_batches')"
        )
        for migration in ("047_cqc_source_watermarks.sql", "048_cqc_reconciliation_batches.sql"):
            await conn.execute((MIGRATIONS_DIR / migration).read_text(encoding="utf-8"))
        assert await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'cqc_reconciliation_batches' AND column_name = 'manifest')"
        )
        assert await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_cqc_reconciliation_record_immutability' AND NOT tgisinternal)"
        )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_prepare_resume_finalize_and_replay_are_atomic(fresh_db, tmp_path, monkeypatch):
    async_conn = await asyncpg.connect(fresh_db)
    try:
        applied = await apply_full_schema(async_conn)
        assert "047_cqc_source_watermarks.sql" in applied
        assert "048_cqc_reconciliation_batches.sql" in applied
        await async_conn.executemany(
            """
            INSERT INTO care_providers (id, name, slug, status, registration_date)
            VALUES ($1, $2, $3, $4, $5)
            """,
            [
                ("LOC-A", "Old A", "old-a", "ACTIVE", date(2026, 7, 1)),
                ("LOC-OLD", "Old", "old", "ACTIVE", date(2025, 1, 1)),
                ("LOC-RE", "Re", "re", "INACTIVE", date(2026, 7, 1)),
            ],
        )
    finally:
        await async_conn.close()

    snapshot = CqcSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at=date.today(),
        source_retrieved_at=datetime.now(timezone.utc),
        source_checksum_sha256="a" * 64,
        location_ids=frozenset({"LOC-A", "LOC-NEW", "LOC-RE"}),
    )
    counts = {
        "sourceCount": 3,
        "currentCount": 2,
        "intersectionCount": 1,
        "additionCount": 1,
        "reactivationCount": 1,
        "deactivationCount": 1,
    }
    batch_id = uuid.uuid4()
    manifest_path = tmp_path / "manifest.json"
    args = _args(batch_id, manifest_path, counts)
    monkeypatch.setattr(reconcile, "fetch_snapshot", lambda *_args, **_kwargs: snapshot)

    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    reconcile._prepare(args, conn, cur)
    cur.execute(
        "SELECT manifest FROM cqc_reconciliation_batches WHERE id = %s",
        (str(batch_id),),
    )
    assert cur.fetchone()[0]["manifestChecksumSha256"]
    cur.execute("SELECT status FROM care_providers WHERE id = 'LOC-OLD'")
    assert cur.fetchone()[0] == "ACTIVE"
    cur.execute("SELECT COUNT(*) FROM care_providers WHERE id = 'LOC-NEW'")
    assert cur.fetchone()[0] == 0
    cur.close()
    conn.close()
    manifest_path.unlink()
    durable_args = _args(batch_id, None, counts)

    partitions = reconcile.partition_location_ids(snapshot.location_ids, 2)
    failing_shard = next(index for index, values in enumerate(partitions) if len(values) > 1)
    fail_id = partitions[failing_shard][1]
    failed_once = False

    def interrupted_fetch(_base_url, _api_key, location_id):
        nonlocal failed_once
        if location_id == fail_id and not failed_once:
            failed_once = True
            raise ReconciliationError("simulated interruption")
        return _details(location_id)

    monkeypatch.setattr(reconcile, "_fetch_detail", interrupted_fetch)
    shard_args = _args(batch_id, None, counts, shard_index=failing_shard)
    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    with pytest.raises(ReconciliationError, match="simulated interruption"):
        reconcile._run_shard(shard_args, conn, cur, "test-key")
    cur.execute(
        "SELECT next_offset, status FROM cqc_reconciliation_shards WHERE batch_id = %s AND shard_index = %s",
        (str(batch_id), failing_shard),
    )
    assert cur.fetchone() == (1, "failed")
    cur.close()
    conn.close()

    monkeypatch.setattr(reconcile, "_fetch_detail", lambda _base, _key, location_id: _details(location_id))
    for shard_index in range(2):
        shard_args = _args(batch_id, None, counts, shard_index=shard_index)
        conn = psycopg2.connect(fresh_db)
        cur = conn.cursor()
        reconcile._run_shard(shard_args, conn, cur, "test-key")
        cur.close()
        conn.close()

    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    cur.execute("SELECT status FROM care_providers WHERE id = 'LOC-OLD'")
    assert cur.fetchone()[0] == "ACTIVE"
    cur.execute("SELECT COUNT(*) FROM care_providers WHERE id = 'LOC-NEW'")
    assert cur.fetchone()[0] == 0
    with pytest.raises(psycopg2.Error, match="records are immutable"):
        cur.execute(
            "UPDATE cqc_reconciliation_records SET record = record WHERE batch_id = %s",
            (str(batch_id),),
        )
    conn.rollback()
    with pytest.raises(psycopg2.Error, match="records are immutable"):
        cur.execute(
            "DELETE FROM cqc_reconciliation_records WHERE batch_id = %s",
            (str(batch_id),),
        )
    conn.rollback()
    with pytest.raises(psycopg2.Error, match="batch plan and manifest are immutable"):
        cur.execute(
            "UPDATE cqc_reconciliation_batches SET source_count = source_count + 1 WHERE id = %s",
            (str(batch_id),),
        )
    conn.rollback()

    cur.execute("ALTER TABLE cqc_reconciliation_records DISABLE TRIGGER trg_cqc_reconciliation_record_immutability")
    cur.execute(
        "UPDATE cqc_reconciliation_records SET record_sha256 = %s WHERE batch_id = %s AND location_id = 'LOC-A'",
        ("b" * 64, str(batch_id)),
    )
    cur.execute("ALTER TABLE cqc_reconciliation_records ENABLE TRIGGER trg_cqc_reconciliation_record_immutability")
    conn.commit()
    with pytest.raises(ReconciliationError, match="payload hash mismatch"):
        reconcile._finalize(durable_args, conn, cur)
    conn.rollback()
    cur.execute("ALTER TABLE cqc_reconciliation_records DISABLE TRIGGER trg_cqc_reconciliation_record_immutability")
    cur.execute(
        """
        UPDATE cqc_reconciliation_records
        SET record_sha256 = encode(digest(convert_to(record::text, 'UTF8'), 'sha256'), 'hex')
        WHERE batch_id = %s AND location_id = 'LOC-A'
        """,
        (str(batch_id),),
    )
    cur.execute("ALTER TABLE cqc_reconciliation_records ENABLE TRIGGER trg_cqc_reconciliation_record_immutability")
    conn.commit()
    cur.close()
    conn.close()

    legacy = psycopg2.connect(fresh_db)
    legacy.autocommit = True
    legacy_cur = legacy.cursor()
    legacy_cur.execute("SELECT pg_advisory_lock(%s)", (INCREMENTAL_UPDATE_LOCK_ID,))
    legacy_cur.execute("UPDATE care_providers SET name = 'Legacy stale A' WHERE id = 'LOC-A'")
    finalized = threading.Event()
    worker_connected = threading.Event()
    worker_pids: list[int] = []
    finalize_errors: list[BaseException] = []

    def finalize_while_legacy_lock_is_held():
        worker = psycopg2.connect(
            fresh_db, application_name="cqc_finalize_concurrency_test"
        )
        worker_pids.append(worker.get_backend_pid())
        worker_connected.set()
        worker_cur = worker.cursor()
        try:
            reconcile._finalize(durable_args, worker, worker_cur)
        except BaseException as exc:  # surfaced in the owning test thread
            finalize_errors.append(exc)
        finally:
            worker_cur.close()
            worker.close()
            finalized.set()

    worker = threading.Thread(target=finalize_while_legacy_lock_is_held, daemon=True)
    worker.start()
    assert worker_connected.wait(timeout=5)
    wait_state = None
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        legacy_cur.execute(
            """
            SELECT wait_event_type, wait_event
            FROM pg_stat_activity
            WHERE pid = %s
            """,
            (worker_pids[0],),
        )
        wait_state = legacy_cur.fetchone()
        if wait_state == ("Lock", "advisory"):
            break
        time.sleep(0.05)
    assert wait_state == ("Lock", "advisory")
    assert finalized.is_set() is False
    legacy_cur.execute("SELECT pg_advisory_unlock(%s)", (INCREMENTAL_UPDATE_LOCK_ID,))
    legacy_cur.close()
    legacy.close()
    worker.join(timeout=10)
    assert finalized.is_set() is True
    assert finalize_errors == []

    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    cur.execute("SELECT id FROM care_providers WHERE UPPER(status) = 'ACTIVE' ORDER BY id")
    assert [row[0] for row in cur.fetchall()] == ["LOC-A", "LOC-NEW", "LOC-RE"]
    cur.execute("SELECT name FROM care_providers WHERE id = 'LOC-A'")
    assert cur.fetchone()[0] == "Provider LOC-A"
    cur.execute("SELECT status FROM care_providers WHERE id = 'LOC-OLD'")
    assert cur.fetchone()[0] == "INACTIVE"
    cur.execute(
        "SELECT run_type, source_checksum_sha256, source_record_count FROM pipeline_runs WHERE id = (SELECT pipeline_run_id FROM cqc_reconciliation_batches WHERE id = %s)",
        (str(batch_id),),
    )
    assert cur.fetchone() == ("reconciliation", "a" * 64, 3)
    cur.execute("SELECT COUNT(*) FROM trusted_event_ledger WHERE event_type = 'new_registration'")
    assert cur.fetchone()[0] >= 3
    with pytest.raises(psycopg2.Error, match="batch is terminal"):
        cur.execute(
            "UPDATE cqc_reconciliation_batches SET status = 'running' WHERE id = %s",
            (str(batch_id),),
        )
    conn.rollback()
    with pytest.raises(psycopg2.Error, match="shard is terminal"):
        cur.execute(
            """
            UPDATE cqc_reconciliation_shards
            SET status = 'running', completed_at = NULL
            WHERE batch_id = %s AND shard_index = 0
            """,
            (str(batch_id),),
        )
    conn.rollback()
    with pytest.raises(psycopg2.Error, match="non-running shard"):
        cur.execute(
            """
            INSERT INTO cqc_reconciliation_records (
              batch_id, location_id, shard_index, record, record_sha256
            ) VALUES (
              %s, 'LOC-AFTER', %s, '{"id":"LOC-AFTER"}'::jsonb,
              encode(digest(convert_to('{"id":"LOC-AFTER"}'::jsonb::text, 'UTF8'), 'sha256'), 'hex')
            )
            """,
            (str(batch_id), reconcile.shard_for_location("LOC-AFTER", 2)),
        )
    conn.rollback()
    for shard_index in range(2):
        reconcile._run_shard(
            _args(batch_id, None, counts, shard_index=shard_index),
            conn,
            cur,
            "test-key",
        )
    reconcile._finalize(durable_args, conn, cur)
    cur.close()
    conn.close()

    health_conn = await asyncpg.connect(fresh_db)
    try:
        health = await get_pipeline_health(health_conn)
        assert health["freshness_ok"] is True
        assert health["source"]["sourceRunType"] == "reconciliation"
        assert health["units"]["countsReconciled"] is True
    finally:
        await health_conn.close()

    replay_id = uuid.uuid4()
    replay_path = tmp_path / "replay.json"
    replay_counts = {
        "sourceCount": 3,
        "currentCount": 3,
        "intersectionCount": 3,
        "additionCount": 0,
        "reactivationCount": 0,
        "deactivationCount": 0,
    }
    replay_args = _args(replay_id, replay_path, replay_counts)
    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    reconcile._prepare(replay_args, conn, cur)
    partitions = reconcile.partition_location_ids(snapshot.location_ids, 2)
    nested_shard = next(index for index, values in enumerate(partitions) if values)
    nested_id = partitions[nested_shard][0]
    cur.execute(
        """
        INSERT INTO cqc_reconciliation_shards (
          batch_id, shard_index, status, manifest_checksum_sha256, expected_count
        ) SELECT id, %s, 'running', manifest_checksum_sha256, %s
          FROM cqc_reconciliation_batches WHERE id = %s
        """,
        (nested_shard, len(partitions[nested_shard]), str(replay_id)),
    )
    nested = {"id": nested_id, "nested": {"list": [1, None, {"key": "value"}]}, "nullable": None}
    cur.execute(
        """
        INSERT INTO cqc_reconciliation_records (
          batch_id, location_id, shard_index, record, record_sha256
        ) VALUES (
          %s, %s, %s, %s,
          encode(digest(convert_to((%s::jsonb)::text, 'UTF8'), 'sha256'), 'hex')
        )
        RETURNING record_sha256 = encode(digest(convert_to(record::text, 'UTF8'), 'sha256'), 'hex')
        """,
        (str(replay_id), nested_id, nested_shard, psycopg2.extras.Json(nested), psycopg2.extras.Json(nested)),
    )
    assert cur.fetchone()[0] is True
    conn.rollback()
    cur.close()
    conn.close()
    for shard_index in range(2):
        replay_shard = _args(replay_id, None, replay_counts, shard_index=shard_index)
        conn = psycopg2.connect(fresh_db)
        cur = conn.cursor()
        reconcile._run_shard(replay_shard, conn, cur, "test-key")
        cur.close()
        conn.close()
    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    reconcile._finalize(_args(replay_id, None, replay_counts), conn, cur)
    cur.execute(
        "SELECT records_inserted, records_updated, records_unchanged, records_deactivated FROM cqc_reconciliation_batches WHERE id = %s",
        (str(replay_id),),
    )
    assert cur.fetchone() == (0, 0, 3, 0)
    cur.close()
    conn.close()

    aborted_id = uuid.uuid4()
    aborted_path = tmp_path / "aborted.json"
    aborted_args = _args(aborted_id, aborted_path, replay_counts)
    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    reconcile._prepare(aborted_args, conn, cur)
    reconcile._abort(_args(aborted_id, None, replay_counts), conn, cur)
    reconcile._abort(_args(aborted_id, None, replay_counts), conn, cur)
    cur.close()
    conn.close()

    aborted_shard = _args(
        aborted_id, aborted_path, replay_counts, shard_index=0
    )
    conn = psycopg2.connect(fresh_db)
    cur = conn.cursor()
    with pytest.raises(ReconciliationError, match="not eligible for shard execution"):
        reconcile._run_shard(aborted_shard, conn, cur, "test-key")
    cur.execute(
        "SELECT status FROM cqc_reconciliation_batches WHERE id = %s",
        (str(aborted_id),),
    )
    assert cur.fetchone()[0] == "failed"
    cur.close()
    conn.close()
