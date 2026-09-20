"""Real-PostgreSQL discrimination test for the reconciliation finalize guard.

`tests/test_incremental_update.py` stubs the database cursor and serves canned
rows chosen by substring-matching the SQL text (`'COUNT(*)' in statement and
'ID = ANY(%S)' in statement`). That proves the statement is spelled the way the
stub expects; it does not prove the ACTIVE/INACTIVE FILTER predicates mean what
the positional unpacking assumes. Swapping the two FILTER branches — a
production inversion that counts active locations as inactive — still left
`pytest tests/test_incremental_update.py -k finaliz` green.

This module closes that gap. It applies db/init.sql plus every numbered
migration to a throwaway PostgreSQL database, seeds a manifest-covered estate
into care_providers, and executes the real `_finalize_batch` against the real
guard SQL. Every public-facing case is asserted on rows the guard actually read
and wrote, so the suite fails when the FILTER branches are swapped and passes
when they are not.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any

import psycopg2
import pytest

from incremental_update import (
    CqcActiveSnapshot,
    ChangesFetchError,
    _finalize_batch,
    _repair_missing_slugs,
    build_snapshot_manifest,
    partition_location_ids,
)
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio

# 100 manifest locations is small enough to stay fast and large enough to make
# the 5% divergence bound meaningful (its integer boundary sits at 5 of 100).
MANIFEST_IDS = [f"1-{10000 + index}" for index in range(100)]
# Rows the batch must deactivate: active in the database, absent from the manifest.
ROGUE_IDS = ["1-90001", "1-90002"]
SHARD_COUNT = 2
SOURCE_PUBLISHED_AT = "2026-08-01"
SOURCE_CHECKSUM_SHA256 = "a" * 64
RETRIEVED_AT = datetime(2026, 8, 2, tzinfo=timezone.utc)


def _estate(**overrides: str | None) -> dict[str, str | None]:
    """A manifest estate where every location is ACTIVE unless overridden."""
    statuses: dict[str, str | None] = {location_id: "ACTIVE" for location_id in MANIFEST_IDS}
    statuses.update(overrides)
    return statuses


async def _seed(conn, statuses: dict[str, str | None]) -> None:
    await conn.executemany(
        "INSERT INTO care_providers (id, name, slug, status) VALUES ($1, $2, $3, $4)",
        [
            (location_id, f"Provider {location_id}", f"provider-{location_id}", status)
            for location_id, status in statuses.items()
        ],
    )


async def _seed_batch(conn, tmp_path, *, statuses: dict[str, str | None]) -> uuid.UUID:
    """Create a complete, finalizable batch for the 100-location manifest."""
    batch_id = uuid.uuid4()
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at=SOURCE_PUBLISHED_AT,
        retrieved_at=RETRIEVED_AT,
        checksum_sha256=SOURCE_CHECKSUM_SHA256,
        location_ids=frozenset(MANIFEST_IDS),
    )
    manifest = build_snapshot_manifest(snapshot, batch_id, SHARD_COUNT)
    manifest_path = tmp_path / f"manifest-{batch_id}.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    active_before = sum(1 for status in statuses.values() if status == "ACTIVE")
    pipeline_run_id = await conn.fetchval(
        """
        INSERT INTO pipeline_runs (run_type, status, source_total_count, checkpoint_state, counts_reconciled)
        VALUES ('reconciliation', 'running', $1, '{}'::jsonb, FALSE)
        RETURNING id
        """,
        len(MANIFEST_IDS),
    )
    await conn.execute(
        """
        INSERT INTO reconciliation_batches (
          id, pipeline_run_id, source_uri, source_published_at, source_retrieved_at,
          source_checksum_sha256, manifest_checksum_sha256, location_count, shard_count,
          status, active_records_before
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'running', $10)
        """,
        batch_id,
        pipeline_run_id,
        snapshot.source_uri,
        date.fromisoformat(SOURCE_PUBLISHED_AT),
        RETRIEVED_AT,
        SOURCE_CHECKSUM_SHA256,
        manifest["manifestChecksumSha256"],
        len(MANIFEST_IDS),
        SHARD_COUNT,
        active_before,
    )
    for shard_index, partition in enumerate(partition_location_ids(MANIFEST_IDS, SHARD_COUNT)):
        await conn.execute(
            """
            INSERT INTO reconciliation_shards (
              batch_id, shard_index, status, manifest_checksum_sha256,
              expected_count, next_offset, processed_count, records_inserted, records_updated
            ) VALUES ($1, $2, 'completed', $3, $4, $4, $4, $4, 0)
            """,
            batch_id,
            shard_index,
            manifest["manifestChecksumSha256"],
            len(partition),
        )
    return batch_id


def _run_finalize(fresh_db: str, batch_id: uuid.UUID, tmp_path, *, dry_run: bool, **extra) -> int:
    args = SimpleNamespace(
        batch_id=str(batch_id),
        snapshot_manifest=str(tmp_path / f"manifest-{batch_id}.json"),
        dry_run=dry_run,
        **extra,
    )
    conn = psycopg2.connect(fresh_db)
    try:
        return _finalize_batch(args, conn, conn.cursor())
    finally:
        conn.close()


async def _batch_row(conn, batch_id: uuid.UUID):
    return await conn.fetchrow(
        """
        SELECT b.status, b.active_records_before, b.active_records_after, b.records_deactivated,
               p.status AS run_status, p.counts_reconciled,
               p.active_records_before AS run_active_before, p.active_records_after AS run_active_after
        FROM reconciliation_batches AS b
        JOIN pipeline_runs AS p ON p.id = b.pipeline_run_id
        WHERE b.id = $1
        """,
        batch_id,
    )


async def _active_count(conn) -> int:
    return int(await conn.fetchval("SELECT COUNT(*) FROM care_providers WHERE UPPER(status) = 'ACTIVE'"))


async def test_finalizer_accepts_a_manifest_location_the_poll_deactivated(
    tmp_path, fresh_db, capsys, monkeypatch
):
    """One of 100 manifest locations is inactive: a genuinely attributed loss inside the bound.

    The two rogue candidates are confirmed deregistered by the injected detail
    fetcher, so the deactivations are real API-confirmed writes rather than a
    side effect of an unreachable API.
    """
    async_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(async_conn)
        statuses = _estate(**{MANIFEST_IDS[7]: "INACTIVE"})
        statuses.update({rogue: "ACTIVE" for rogue in ROGUE_IDS})
        await _seed(async_conn, statuses)
        batch_id = await _seed_batch(async_conn, tmp_path, statuses=statuses)
        assert await _active_count(async_conn) == 101
    finally:
        await async_conn.close()
    monkeypatch.setattr(
        "incremental_update.fetch_location_detail",
        _detail_fetcher({rogue: {"registrationStatus": "Deregistered"} for rogue in ROGUE_IDS}),
    )
    capsys.readouterr()

    assert _run_finalize(fresh_db, batch_id, tmp_path, dry_run=False) == 0
    success_line = capsys.readouterr().out

    async_conn = await asyncpg.connect(fresh_db)
    try:
        row = await _batch_row(async_conn, batch_id)
        assert row["status"] == "completed"
        assert row["run_status"] == "completed"
        assert row["counts_reconciled"] is True
        assert row["active_records_after"] == 99
        assert row["run_active_before"] == 101
        assert row["run_active_after"] == 99
        assert row["records_deactivated"] == len(ROGUE_IDS)
        assert await _active_count(async_conn) == 99
        assert await async_conn.fetchval(
            "SELECT COUNT(*) FROM care_providers WHERE id = ANY($1) AND UPPER(status) = 'INACTIVE'",
            [MANIFEST_IDS[7]],
        ) == 1
    finally:
        await async_conn.close()

    # The tolerated stock is observable instead of appearing only in a refusal.
    assert f"Finalized batch {batch_id}: active=99, deactivated=2" in success_line
    assert "inactive_in_manifest=1" in success_line
    assert "1.00% of 100 manifest locations" in success_line


async def test_finalizer_accepts_divergence_at_the_drop_ratio_boundary(tmp_path, fresh_db, capsys):
    """5 of 100 inactive is exactly the bound and must still finalize."""
    async_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(async_conn)
        statuses = _estate(**{location_id: "INACTIVE" for location_id in MANIFEST_IDS[:5]})
        await _seed(async_conn, statuses)
        batch_id = await _seed_batch(async_conn, tmp_path, statuses=statuses)
    finally:
        await async_conn.close()

    assert _run_finalize(fresh_db, batch_id, tmp_path, dry_run=False) == 0

    async_conn = await asyncpg.connect(fresh_db)
    try:
        row = await _batch_row(async_conn, batch_id)
        assert row["status"] == "completed"
        assert row["active_records_after"] == 95
        assert await _active_count(async_conn) == 95
    finally:
        await async_conn.close()


async def test_finalizer_refuses_a_manifest_location_the_active_filter_should_have_counted(tmp_path, fresh_db):
    """6 of 100 inactive exceeds the bound by exactly one location."""
    async_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(async_conn)
        statuses = _estate(**{location_id: "INACTIVE" for location_id in MANIFEST_IDS[:6]})
        await _seed(async_conn, statuses)
        batch_id = await _seed_batch(async_conn, tmp_path, statuses=statuses)
    finally:
        await async_conn.close()

    with pytest.raises(ChangesFetchError, match="6 of 100 manifest locations are not active"):
        _run_finalize(fresh_db, batch_id, tmp_path, dry_run=True)


@pytest.mark.parametrize(
    ("label", "overrides", "dropped_id"),
    [
        ("missing row", {}, MANIFEST_IDS[3]),
        ("NULL status", {MANIFEST_IDS[3]: None}, None),
        ("unexpected status", {MANIFEST_IDS[3]: "SUSPENDED"}, None),
    ],
)
async def test_finalizer_fails_closed_on_unattributable_manifest_state(
    tmp_path, fresh_db, label, overrides, dropped_id
):
    """A missing row, a NULL status and any non-ACTIVE/INACTIVE status fail closed."""
    async_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(async_conn)
        statuses = _estate(**overrides)
        if dropped_id is not None:
            statuses.pop(dropped_id)
        await _seed(async_conn, statuses)
        batch_id = await _seed_batch(async_conn, tmp_path, statuses=statuses)
    finally:
        await async_conn.close()

    with pytest.raises(ChangesFetchError, match="1 manifest locations are missing or carry a status"):
        _run_finalize(fresh_db, batch_id, tmp_path, dry_run=True)


# --------------------------------------------------------------------------
# FIX 3: the API-confirmation path, driven for real against PostgreSQL.
#
# ROGUE_IDS are ACTIVE rows absent from the manifest, so they are the
# deactivation candidates the finalizer must confirm against the live CQC API.
# ``fetch_location_detail`` is replaced at the transport level only: the real
# ``confirm_deactivation_candidates`` classifier and the real ``_finalize_batch``
# guard run unchanged.
# --------------------------------------------------------------------------


def _detail_fetcher(payloads: dict[str, Any]):
    """Answer a candidate lookup from ``payloads`` (an Exception raises)."""

    def _fetch(base_url, api_key, location_id):
        outcome = payloads.get(location_id, {"registrationStatus": "Registered"})
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return _fetch


async def _seed_rogue_candidates(tmp_path, fresh_db, statuses: dict[str, Any]):
    async_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(async_conn)
        estate = _estate()
        estate.update({rogue: "ACTIVE" for rogue in statuses})
        await _seed(async_conn, estate)
        batch_id = await _seed_batch(async_conn, tmp_path, statuses=estate)
        assert await _active_count(async_conn) == 100 + len(statuses)
    finally:
        await async_conn.close()
    return batch_id


async def test_finalizer_refuses_while_candidate_details_cannot_be_confirmed(
    tmp_path, fresh_db, monkeypatch
):
    """An unreadable detail and an unfamiliar status both refuse the batch.

    Nothing is absorbed into the expected active count, and no candidate is
    deactivated, so an API failure can never masquerade as a real loss.
    """
    payloads = {
        ROGUE_IDS[0]: ChangesFetchError("CQC API returned 503"),
        ROGUE_IDS[1]: {"registrationStatus": "Suspended"},
    }
    batch_id = await _seed_rogue_candidates(tmp_path, fresh_db, payloads)
    monkeypatch.setattr(
        "incremental_update.fetch_location_detail", _detail_fetcher(payloads)
    )

    with pytest.raises(ChangesFetchError, match="could not be confirmed"):
        _run_finalize(
            fresh_db,
            batch_id,
            tmp_path,
            dry_run=False,
            api_key="integration-test-key",
        )

    async_conn = await asyncpg.connect(fresh_db)
    try:
        row = await _batch_row(async_conn, batch_id)
        assert row["status"] == "running"
        assert row["run_status"] == "running"
        assert row["counts_reconciled"] is False
        assert await async_conn.fetchval(
            "SELECT COUNT(*) FROM care_providers WHERE id = ANY($1) AND UPPER(status) = 'ACTIVE'",
            ROGUE_IDS,
        ) == len(ROGUE_IDS)
    finally:
        await async_conn.close()


async def test_finalizer_records_acknowledged_unconfirmed_candidates_on_the_batch_row(
    tmp_path, fresh_db, monkeypatch
):
    """The explicit operator acknowledgement is recorded, not silently absorbed."""
    payloads = {
        ROGUE_IDS[0]: ChangesFetchError("CQC API returned 503"),
        ROGUE_IDS[1]: {"registrationStatus": "Suspended"},
    }
    batch_id = await _seed_rogue_candidates(tmp_path, fresh_db, payloads)
    monkeypatch.setattr(
        "incremental_update.fetch_location_detail", _detail_fetcher(payloads)
    )

    assert _run_finalize(
        fresh_db,
        batch_id,
        tmp_path,
        dry_run=False,
        api_key="integration-test-key",
        acknowledge_unconfirmed_deactivations=True,
    ) == 0

    async_conn = await asyncpg.connect(fresh_db)
    try:
        row = await async_conn.fetchrow(
            """
            SELECT status, active_records_after, records_deactivated,
                   deactivation_unconfirmed_count, deactivation_confirmation
            FROM reconciliation_batches WHERE id = $1
            """,
            batch_id,
        )
        assert row["status"] == "completed"
        assert row["records_deactivated"] == 0
        assert row["active_records_after"] == 102
        assert row["deactivation_unconfirmed_count"] == len(ROGUE_IDS)
        confirmation = json.loads(row["deactivation_confirmation"])
        assert sorted(confirmation["unconfirmed_ids"]) == sorted(ROGUE_IDS)
        assert confirmation["acknowledged"] is True
        assert confirmation["unconfirmed_count"] == len(ROGUE_IDS)
        assert confirmation["expected_active_after"] == 102
        assert confirmation["active_after"] == 102
        assert await _active_count(async_conn) == 102
    finally:
        await async_conn.close()


async def test_finalizer_deactivates_only_allow_listed_deregistration(
    tmp_path, fresh_db, monkeypatch
):
    """'Deregistered' deactivates; 'Suspended' is kept and recorded as unconfirmed."""
    payloads = {
        ROGUE_IDS[0]: {"registrationStatus": "Deregistered"},
        ROGUE_IDS[1]: {"registrationStatus": "Suspended"},
    }
    batch_id = await _seed_rogue_candidates(tmp_path, fresh_db, payloads)
    monkeypatch.setattr(
        "incremental_update.fetch_location_detail", _detail_fetcher(payloads)
    )

    assert _run_finalize(
        fresh_db,
        batch_id,
        tmp_path,
        dry_run=False,
        api_key="integration-test-key",
        acknowledge_unconfirmed_deactivations=True,
    ) == 0

    async_conn = await asyncpg.connect(fresh_db)
    try:
        assert await async_conn.fetchval(
            "SELECT UPPER(status) FROM care_providers WHERE id = $1", ROGUE_IDS[0]
        ) == "INACTIVE"
        assert await async_conn.fetchval(
            "SELECT UPPER(status) FROM care_providers WHERE id = $1", ROGUE_IDS[1]
        ) == "ACTIVE"
        row = await async_conn.fetchrow(
            """
            SELECT records_deactivated, active_records_after,
                   deactivation_unconfirmed_count, deactivation_confirmation
            FROM reconciliation_batches WHERE id = $1
            """,
            batch_id,
        )
        assert row["records_deactivated"] == 1
        assert row["active_records_after"] == 101
        assert row["deactivation_unconfirmed_count"] == 1
        confirmation = json.loads(row["deactivation_confirmation"])
        assert confirmation["unconfirmed_ids"] == [ROGUE_IDS[1]]
        assert confirmation["deregistered"] == 1
    finally:
        await async_conn.close()


async def test_finalizer_acknowledgement_still_fails_on_an_unexplained_mismatch(
    tmp_path, fresh_db, monkeypatch
):
    """Acknowledging unconfirmed candidates must not absorb a real divergence.

    One extra ACTIVE location appears that was neither in the manifest nor a
    candidate; the guard must still refuse.
    """
    payloads = {ROGUE_IDS[0]: {"registrationStatus": "Suspended"}}
    batch_id = await _seed_rogue_candidates(tmp_path, fresh_db, payloads)
    monkeypatch.setattr(
        "incremental_update.fetch_location_detail", _detail_fetcher(payloads)
    )

    # A location goes ACTIVE after the candidate probe has already run: it was
    # never a candidate, so it cannot be acknowledged away and the guard must
    # still see the unexplained extra row.
    real_repair = _repair_missing_slugs

    def _repair_with_drift(cur):
        with psycopg2.connect(fresh_db) as drift_conn, drift_conn.cursor() as drift_cur:
            drift_cur.execute(
                """
                INSERT INTO care_providers (id, name, slug, status)
                VALUES (%s, %s, %s, 'ACTIVE')
                ON CONFLICT (id) DO NOTHING
                """,
                ("1-96001", "Drift Provider", "provider-drift"),
            )
        real_repair(cur)

    monkeypatch.setattr("incremental_update._repair_missing_slugs", _repair_with_drift)

    with pytest.raises(ChangesFetchError, match="does not match the authoritative manifest"):
        _run_finalize(
            fresh_db,
            batch_id,
            tmp_path,
            dry_run=False,
            api_key="integration-test-key",
            acknowledge_unconfirmed_deactivations=True,
        )
