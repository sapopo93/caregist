"""Real shard, finalize and freshness evidence on disposable local PostGIS."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import psycopg2
import pytest

import incremental_update as iu
from api.queries.public_tools import CHANGE_FREQUENCY_COLLECTION_COVERAGE
from api.services.cqc_freshness import get_cqc_freshness
from tests.integration.conftest import apply_full_schema
from tests.integration.test_finalize_guard_pg import (
    MANIFEST_IDS, SHARD_COUNT, _estate, _seed, _seed_batch, _run_finalize,
)

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio


async def _save_unavailable(conn, batch_id, unavailable):
    partitions = iu.partition_location_ids(MANIFEST_IDS, SHARD_COUNT)
    evidence = {str(index): [value for value in partition if value in unavailable]
                for index, partition in enumerate(partitions)}
    await conn.execute(
        "UPDATE pipeline_runs SET checkpoint_state = $1::jsonb "
        "WHERE id = (SELECT pipeline_run_id FROM reconciliation_batches WHERE id = $2)",
        json.dumps({"detailUnavailableShards": evidence}), batch_id,
    )
    for index, partition in enumerate(partitions):
        await conn.execute(
            "UPDATE reconciliation_shards SET records_inserted = $1 "
            "WHERE batch_id = $2 AND shard_index = $3",
            len(partition) - len(evidence[str(index)]), batch_id, index,
        )


@pytest.mark.parametrize("count", [25, 26])
async def test_finalize_cap_and_row_preservation(fresh_db, tmp_path, monkeypatch, count):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        statuses = _estate()
        unavailable = MANIFEST_IDS[:count]
        del statuses[unavailable[0]]
        statuses[unavailable[1]] = "INACTIVE"
        statuses[unavailable[2]] = None
        await _seed(conn, statuses)
        before = await conn.fetch("SELECT * FROM care_providers WHERE id = ANY($1) ORDER BY id", unavailable)
        batch_id = await _seed_batch(conn, tmp_path, statuses=statuses)
        await _save_unavailable(conn, batch_id, unavailable)
        monkeypatch.setattr(iu, "confirm_deactivation_candidates", lambda *a, **k: pytest.fail("directory member became candidate"))
        if count > 25:
            with pytest.raises(iu.ChangesFetchError, match="detail_unavailable=26 exceeds cap=25"):
                _run_finalize(fresh_db, batch_id, tmp_path, dry_run=False)
            assert not await conn.fetchval("SELECT counts_reconciled FROM pipeline_runs")
        else:
            assert _run_finalize(fresh_db, batch_id, tmp_path, dry_run=False) == 0
            row = await conn.fetchrow("SELECT * FROM pipeline_runs")
            state = json.loads(row["checkpoint_state"])
            assert row["checked_count"] == 100
            assert row["success_count"] == 75
            assert row["failure_count"] == 25
            assert state["detailUnavailableIds"] == sorted(unavailable)
            assert state["detail_unavailable"] == 25
            batch = await conn.fetchrow("SELECT * FROM reconciliation_batches WHERE id = $1", batch_id)
            assert batch["records_inserted"] == 75
            assert json.loads(batch["deactivation_confirmation"])["detailUnavailableIds"] == sorted(unavailable)
            assert batch["records_deactivated"] == 0
            # Fixture publication/retrieval is historical; use now at that source
            # to test freshness validation independently of the eight-day SLA.
            result = await get_cqc_freshness(conn, now=datetime(2026, 8, 2, 1, tzinfo=UTC))
            assert result["status"] == "fresh"
            coverage = await conn.fetch(CHANGE_FREQUENCY_COLLECTION_COVERAGE, 3)
            assert sum(row["runs"] for row in coverage if row["status"] == "completed") == 1
        after = await conn.fetch("SELECT * FROM care_providers WHERE id = ANY($1) ORDER BY id", unavailable)
        assert before == after
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM care_providers WHERE id = $1)", unavailable[0])
    finally:
        await conn.close()


@pytest.mark.parametrize("defect", ["missing_shard", "foreign_id", "wrong_written_count", "duplicate_id"])
async def test_exception_evidence_cannot_mask_inconsistent_coverage(fresh_db, tmp_path, defect):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await _seed(conn, _estate())
        batch_id = await _seed_batch(conn, tmp_path, statuses=_estate())
        await _save_unavailable(conn, batch_id, [MANIFEST_IDS[0]])
        if defect == "missing_shard":
            await conn.execute("DELETE FROM reconciliation_shards WHERE batch_id = $1 AND shard_index = 1", batch_id)
        elif defect == "wrong_written_count":
            await conn.execute("UPDATE reconciliation_shards SET records_inserted = 0 WHERE batch_id = $1", batch_id)
        else:
            state = {"detailUnavailableShards": {"0": ["1-99999"] if defect == "foreign_id" else [MANIFEST_IDS[0]] * 2}}
            await conn.execute("UPDATE pipeline_runs SET checkpoint_state = $1::jsonb", json.dumps(state))
        with pytest.raises(iu.ChangesFetchError, match="coverage is incomplete|Invalid detail-unavailable"):
            _run_finalize(fresh_db, batch_id, tmp_path, dry_run=False)
        assert not await conn.fetchval("SELECT counts_reconciled FROM pipeline_runs")
    finally:
        await conn.close()


async def test_shard_checkpoints_unavailable_without_writing_and_resumes(fresh_db, tmp_path, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await _seed(conn, _estate())
        batch_id = await _seed_batch(conn, tmp_path, statuses=_estate())
        partition = iu.partition_location_ids(MANIFEST_IDS, SHARD_COUNT)[0]
        unavailable, unavailable_absent, fail_once = partition[:3]
        await conn.execute("DELETE FROM care_providers WHERE id = $1", unavailable_absent)
        before = await conn.fetchrow("SELECT * FROM care_providers WHERE id = $1", unavailable)
        await conn.execute(
            "UPDATE reconciliation_shards SET status = 'running', next_offset = 0, processed_count = 0, "
            "records_inserted = 0, records_updated = 0 WHERE batch_id = $1 AND shard_index = 0", batch_id,
        )
        calls = []
        failing = [True]
        def fetch(base_url, api_key, location_id, *, directory_member):
            assert directory_member
            calls.append(location_id)
            if location_id in (unavailable, unavailable_absent):
                raise iu.DetailUnavailableError("persistent 404")
            if location_id == fail_once and failing[0]:
                raise iu.ChangesFetchError("Detail fetch failed: 502")
            return {"locationId": location_id, "name": "Updated synthetic provider", "registrationStatus": "Registered"}
        monkeypatch.setattr(iu, "fetch_location_detail", fetch)
        monkeypatch.setattr(iu.time, "sleep", lambda _: None)
        args = SimpleNamespace(batch_id=str(batch_id), snapshot_manifest=str(tmp_path / f"manifest-{batch_id}.json"),
                               shard_count=SHARD_COUNT, shard_index=0, dry_run=False,
                               checkpoint_size=2, base_url=iu.DEFAULT_BASE_URL, sleep=0)
        sync = psycopg2.connect(fresh_db)
        try:
            with pytest.raises(iu.ChangesFetchError, match="502"):
                iu._run_shard(args, sync, sync.cursor(), None)
            row = await conn.fetchrow("SELECT * FROM pipeline_runs")
            assert row["success_count"] == len(iu.partition_location_ids(MANIFEST_IDS, SHARD_COUNT)[1])
            assert row["failure_count"] == 3  # two unavailable plus failed shard
            saved = json.loads(row["checkpoint_state"])["detailUnavailableShards"]["0"]
            assert saved == [unavailable, unavailable_absent]
            failing[0] = False
            assert iu._run_shard(args, sync, sync.cursor(), None) == 0
        finally:
            sync.close()
        assert calls.count(unavailable) == calls.count(unavailable_absent) == 1
        shard = await conn.fetchrow("SELECT * FROM reconciliation_shards WHERE batch_id = $1 AND shard_index = 0", batch_id)
        assert shard["status"] == "completed"
        assert shard["processed_count"] == len(partition)
        assert shard["records_updated"] == len(partition) - 2
        assert before == await conn.fetchrow("SELECT * FROM care_providers WHERE id = $1", unavailable)
        assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM care_providers WHERE id = $1)", unavailable_absent)
        assert await conn.fetchval("SELECT name FROM care_providers WHERE id = $1", partition[-1]) == "Updated synthetic provider"
        # Consume the committed shard evidence through real finalization too.
        assert _run_finalize(fresh_db, batch_id, tmp_path, dry_run=False) == 0
        row = await conn.fetchrow("SELECT success_count, failure_count FROM pipeline_runs")
        assert tuple(row.values()) == (98, 2)
    finally:
        await conn.close()


@pytest.mark.parametrize("count,overrides,accepted", [
    (1, {}, True), (25, {}, True), (26, {}, False),
    (1, {"detail_unavailable": 1.0}, False),
    (1, {"detailUnavailableCap": 25.5}, False),
    (1, {"detailUnavailableCap": "25"}, False),
    (1, {"detailUnavailableIds": [None]}, False),
    (1, {"detailUnavailableIds": [""]}, False),
    (1, {"detailUnavailableIds": {}}, False),
    (2, {"detailUnavailableIds": ["1-10000"] * 2}, False),
    (1, {"fullCoverage": False}, False),
    (1, {"detail_unavailable": True}, False),
])
async def test_python_and_public_sql_validate_the_same_evidence(fresh_db, count, overrides, accepted):
    from api.services.cqc_reconciliation_evidence import BOUNDED_DETAIL_UNAVAILABLE_SQL, bounded_detail_unavailable
    state = {
        "fullCoverage": True, "detail_unavailable": count, "detailUnavailableCap": 25,
        "detailUnavailableIds": [f"1-{10000 + index}" for index in range(count)],
    }
    state.update(overrides)
    conn = await asyncpg.connect(fresh_db)
    try:
        result = await conn.fetchval(
            f"SELECT COALESCE(({BOUNDED_DETAIL_UNAVAILABLE_SQL}), FALSE) "
            "FROM (SELECT $1::int AS failure_count, $2::jsonb AS checkpoint_state) evidence",
            count, json.dumps(state),
        )
        assert bool(result) is accepted
        assert bounded_detail_unavailable({"failure_count": count, "checkpoint_state": state}) is accepted
    finally:
        await conn.close()


async def test_parallel_shards_preserve_both_exception_checkpoints(fresh_db, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await _seed(conn, _estate())
        batch_id = await _seed_batch(conn, tmp_path, statuses=_estate())
        partitions = iu.partition_location_ids(MANIFEST_IDS, SHARD_COUNT)
        unavailable = [partition[0] for partition in partitions]
        await conn.execute(
            "UPDATE reconciliation_shards SET status = 'running', next_offset = 0, "
            "processed_count = 0, records_inserted = 0, records_updated = 0 WHERE batch_id = $1", batch_id,
        )
        rendezvous = Barrier(2)
        def fetch(base_url, api_key, location_id, *, directory_member):
            if location_id in unavailable:
                rendezvous.wait(timeout=10)
                raise iu.DetailUnavailableError("persistent 404")
            return {"locationId": location_id, "name": "Parallel synthetic provider", "registrationStatus": "Registered"}
        monkeypatch.setattr(iu, "fetch_location_detail", fetch)
        monkeypatch.setattr(iu.time, "sleep", lambda _: None)
        def run(index):
            args = SimpleNamespace(batch_id=str(batch_id), snapshot_manifest=str(tmp_path / f"manifest-{batch_id}.json"),
                                   shard_count=SHARD_COUNT, shard_index=index, dry_run=False,
                                   checkpoint_size=100, base_url=iu.DEFAULT_BASE_URL, sleep=0)
            sync = psycopg2.connect(fresh_db)
            try:
                return iu._run_shard(args, sync, sync.cursor(), None)
            finally:
                sync.close()
        with ThreadPoolExecutor(max_workers=2) as workers:
            assert list(workers.map(run, range(SHARD_COUNT))) == [0, 0]
        row = await conn.fetchrow("SELECT * FROM pipeline_runs")
        evidence = json.loads(row["checkpoint_state"])
        assert evidence["detailUnavailableShards"] == {"0": [unavailable[0]], "1": [unavailable[1]]}
        assert row["success_count"] == 98
        assert row["failure_count"] == 2
        assert _run_finalize(fresh_db, batch_id, tmp_path, dry_run=False) == 0
        completed = await conn.fetchrow("SELECT success_count, failure_count FROM pipeline_runs")
        assert tuple(completed.values()) == (98, 2)
    finally:
        await conn.close()
