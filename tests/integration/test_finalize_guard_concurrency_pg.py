"""Concurrency regression for the reconciliation finalize end-state guard.

The guard at `incremental_update.py` verifies the *exact ACTIVE id set* after
this batch's own writes and refuses separately on missing and extra ids. Read
alone (READ COMMITTED, no lock, no predicate protection), that verification is
defeated by any transaction that commits an identity substitution **after the
verification read and before the finalizer's own commit**: the substitution is
invisible to the read, survives the finalizer's commit, and is certified by the
`active_identity_verified: true` row the finalizer writes into
`reconciliation_batches.deactivation_confirmation`.

This module pins that window deterministically (no race): the success path
makes exactly one `json.dumps({"fullCoverage": True, ...})` call while building
the `UPDATE pipeline_runs` arguments, which lies strictly after the end-state
read and strictly before `conn.commit()`. Wrapping that call parks the real
`_finalize_batch` inside the window while a second connection attempts a
count-neutral substitution -- one manifest location leaves the ACTIVE set, one
unexplained location joins it, so the total is 100 before and after and nothing
a count can compare separates the two estates.

Two assertions are made, deliberately:

1. Mechanism: the substitution attempt inside the window is *refused* (it waits
   on the finalizer's lock and hits `lock_timeout`). This is the assertion that
   fails if the verification read is left unprotected.
2. Invariant (mechanism-independent): the committed attestation is never green
   while the ACTIVE estate disagrees with it. A green `active_identity_verified`
   with empty missing/extra lists must describe the estate that actually
   committed.

Both fail against the unprotected guard; the reason is that the substitution is
neither prevented nor recorded.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any

import psycopg2
import pytest

from incremental_update import (
    CqcActiveSnapshot,
    _finalize_batch,
    build_snapshot_manifest,
    partition_location_ids,
)
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio

# 100 manifest locations, matching the estate shape the guard suite uses, so the
# 5% divergence bound has a meaningful integer boundary and the substitution is
# exactly count-neutral.
MANIFEST_IDS = [f"1-{10000 + index}" for index in range(100)]
#: ACTIVE rows absent from the manifest: API-confirmed deregistered, so the
#: batch deactivates them and the expected ACTIVE set is exactly the manifest.
ROGUE_IDS = ["1-90001", "1-90002"]
#: The manifest location the substitution takes out of the ACTIVE set.
SUBSTITUTED_OUT_ID = MANIFEST_IDS[7]
#: The unexplained location the substitution puts into the ACTIVE set.
SUBSTITUTED_IN_ID = "1-97001"
SHARD_COUNT = 2
SOURCE_PUBLISHED_AT = "2026-08-01"
SOURCE_CHECKSUM_SHA256 = "a" * 64
RETRIEVED_AT = datetime(2026, 8, 2, tzinfo=timezone.utc)

#: Bounded wait for the refused substitution. The window is held open by the pin
#: until this attempt returns, so the wait is guaranteed to outlast the timeout:
#: the refusal is deterministic, not a race that was won.
WINDOW_LOCK_TIMEOUT_MS = 2_000
#: Generous ceiling for reaching the window and for the finalizer to finish.
PIN_TIMEOUT_S = 60.0


def _estate(statuses: dict[str, str | None]) -> dict[str, str | None]:
    return dict(statuses)


async def _seed_estate(conn, statuses: dict[str, str | None]) -> None:
    await conn.executemany(
        "INSERT INTO care_providers (id, name, slug, status) VALUES ($1, $2, $3, $4)",
        [
            (location_id, f"Provider {location_id}", f"provider-{location_id}", status)
            for location_id, status in statuses.items()
        ],
    )


async def _seed_rogue_candidates(fresh_db: str, tmp_path, payloads: dict[str, Any]) -> uuid.UUID:
    """Seed the manifest estate plus ACTIVE rogue candidates, and a finalizable batch."""
    async_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(async_conn)
        statuses: dict[str, str | None] = {
            location_id: "ACTIVE" for location_id in MANIFEST_IDS
        }
        statuses.update({rogue: "ACTIVE" for rogue in payloads})
        await _seed_estate(async_conn, _estate(statuses))

        batch_id = uuid.uuid4()
        snapshot = CqcActiveSnapshot(
            source_uri="https://www.cqc.org.uk/current.csv",
            source_published_at=SOURCE_PUBLISHED_AT,
            retrieved_at=RETRIEVED_AT,
            checksum_sha256=SOURCE_CHECKSUM_SHA256,
            location_ids=frozenset(MANIFEST_IDS),
        )
        manifest = build_snapshot_manifest(snapshot, batch_id, SHARD_COUNT)
        (tmp_path / f"manifest-{batch_id}.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        active_before = sum(1 for status in statuses.values() if status == "ACTIVE")
        pipeline_run_id = await async_conn.fetchval(
            """
            INSERT INTO pipeline_runs (run_type, status, source_total_count, checkpoint_state, counts_reconciled)
            VALUES ('reconciliation', 'running', $1, '{}'::jsonb, FALSE)
            RETURNING id
            """,
            len(MANIFEST_IDS),
        )
        await async_conn.execute(
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
        for shard_index, partition in enumerate(
            partition_location_ids(MANIFEST_IDS, SHARD_COUNT)
        ):
            await async_conn.execute(
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
    finally:
        await async_conn.close()


def _detail_fetcher(payloads: dict[str, Any]):
    def _fetch(base_url, api_key, location_id):
        return payloads.get(location_id, {"registrationStatus": "Registered"})

    return _fetch


def _run_finalize(fresh_db: str, batch_id: uuid.UUID, tmp_path, **extra) -> int:
    args = SimpleNamespace(
        batch_id=str(batch_id),
        snapshot_manifest=str(tmp_path / f"manifest-{batch_id}.json"),
        dry_run=False,
        **extra,
    )
    conn = psycopg2.connect(fresh_db)
    try:
        return _finalize_batch(args, conn, conn.cursor())
    finally:
        conn.close()


async def _active_ids(conn) -> set[str]:
    rows = await conn.fetch("SELECT id FROM care_providers WHERE UPPER(status) = 'ACTIVE'")
    return {str(record["id"]) for record in rows}


async def test_guard_window_refuses_a_substitution_committed_after_the_verification_read(
    tmp_path, fresh_db, monkeypatch
):
    """A substitution committed inside the verification window must not be certified.

    The finalizer is parked between its end-state read and its commit while a
    second connection attempts to take one manifest location out of the ACTIVE
    set and put an unexplained location into it. Against an unprotected guard the
    substitution commits, the finalize returns 0, and the batch is left
    `completed` with `active_identity_verified: true`, `missing_active_ids: []`
    and `extra_active_ids: []` while the estate no longer matches the manifest.
    """
    payloads = {rogue: {"registrationStatus": "Deregistered"} for rogue in ROGUE_IDS}
    batch_id = await _seed_rogue_candidates(fresh_db, tmp_path, payloads)
    monkeypatch.setattr(
        "incremental_update.fetch_location_detail", _detail_fetcher(payloads)
    )

    import incremental_update as iu

    real_dumps = iu.json.dumps
    reached_window = threading.Event()
    release_window = threading.Event()

    def _pinned_dumps(obj, *args, **kwargs):
        # The one call the success path makes between the verification read and
        # conn.commit(): the `fullCoverage` payload for the pipeline_runs update.
        if (
            isinstance(obj, dict)
            and obj.get("fullCoverage") is True
            and not reached_window.is_set()
        ):
            reached_window.set()
            release_window.wait(PIN_TIMEOUT_S)
        return real_dumps(obj, *args, **kwargs)

    monkeypatch.setattr(iu.json, "dumps", _pinned_dumps)

    outcome: dict[str, Any] = {}

    def _target() -> None:
        try:
            outcome["rc"] = _run_finalize(fresh_db, batch_id, tmp_path)
        except BaseException as exc:  # a refusal is a sound outcome for this batch
            outcome["exc"] = exc

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()

    substituted = False
    refusals: list[psycopg2.Error] = []
    try:
        assert reached_window.wait(PIN_TIMEOUT_S), (
            "the finalizer never reached the verification window, so no interleaving "
            "was established and this run proves nothing"
        )
        drift = psycopg2.connect(fresh_db)
        drift.autocommit = True
        try:
            for statement, parameters in (
                (
                    "UPDATE care_providers SET status = 'INACTIVE' WHERE id = %s",
                    (SUBSTITUTED_OUT_ID,),
                ),
                (
                    """
                    INSERT INTO care_providers (id, name, slug, status)
                    VALUES (%s, %s, %s, 'ACTIVE')
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (SUBSTITUTED_IN_ID, "Unexplained Provider", "provider-unexplained"),
                ),
            ):
                with drift.cursor() as drift_cur:
                    drift_cur.execute("SET lock_timeout = %s", (WINDOW_LOCK_TIMEOUT_MS,))
                    try:
                        drift_cur.execute(statement, parameters)
                    except psycopg2.errors.LockNotAvailable as exc:  # lock_timeout
                        refusals.append(exc)
                    else:
                        substituted = True
        finally:
            drift.close()
    finally:
        release_window.set()
        worker.join(timeout=PIN_TIMEOUT_S)

    # (1) Mechanism: the substitution could not commit inside the window.
    # (2) Invariant: the committed attestation must not be green while the ACTIVE
    # estate disagrees with it (whichever mechanism is used to close the window).
    assert not worker.is_alive(), "the finalizer was still running after its window was released"

    async_conn = await asyncpg.connect(fresh_db)
    try:
        row = await async_conn.fetchrow(
            """
            SELECT b.status, b.active_records_after, p.status AS run_status,
                   p.counts_reconciled, b.deactivation_confirmation
            FROM reconciliation_batches AS b
            JOIN pipeline_runs AS p ON p.id = b.pipeline_run_id
            WHERE b.id = $1
            """,
            batch_id,
        )
        recorded = json.loads(row["deactivation_confirmation"])
        certified_green = (
            row["status"] == "completed"
            and row["run_status"] == "completed"
            and row["counts_reconciled"] is True
            and recorded["active_identity_verified"] is True
        )
        # Every rogue candidate was confirmed deregistered, so the batch's own
        # expectation is exactly the manifest's ACTIVE set. Read immediately after
        # the finalizer returned: this is the state its commit left behind.
        expected_active_ids = set(MANIFEST_IDS)
        estate = await _active_ids(async_conn)
        missing_from_estate = sorted(expected_active_ids - estate)
        unexplained_in_estate = sorted(estate - expected_active_ids)

        violations: list[str] = []
        if substituted:
            violations.append(
                "substitution not prevented: a count-neutral identity substitution "
                "committed inside the verification window (the guard read the ACTIVE set "
                f"before {SUBSTITUTED_OUT_ID} left it and {SUBSTITUTED_IN_ID} joined it)"
            )
        if len(refusals) != 2:
            violations.append(
                f"substitution only partly prevented: {len(refusals)} of 2 of the "
                "identity-substituting statements (the UPDATE that empties a manifest "
                "member, the INSERT that adds an unexplained location) were refused by a "
                "lock wait inside the window"
            )
        if certified_green and (missing_from_estate or unexplained_in_estate):
            violations.append(
                "green attestation without the estate: active_identity_verified=true with "
                "missing_active_ids=[] and extra_active_ids=[] while the ACTIVE estate "
                f"disagreed with the manifest (missing={missing_from_estate}, "
                f"extra={unexplained_in_estate})"
            )
        assert not violations, (
            "; ".join(violations)
            + " -- the guard's end-state comparison is not held under locking or "
            "isolation that prevents concurrent identity substitution, and the "
            "substitution it permits is neither prevented nor recorded as drift"
        )
    finally:
        await async_conn.close()

    # (3) The success path still finalizes: closing the window must not convert a
    # sound batch into a refusal, and the recorded attestation must be the one
    # that describes this estate.
    assert "exc" not in outcome, f"the finalizer refused a sound batch: {outcome.get('exc')!r}"
    assert outcome.get("rc") == 0
    assert row["status"] == "completed"
    assert recorded["active_identity_verified"] is True
    assert recorded["missing_active_ids"] == []
    assert recorded["extra_active_ids"] == []
    assert recorded["expected_active_ids_count"] == len(MANIFEST_IDS)
    assert recorded["active_after_ids_count"] == len(MANIFEST_IDS)
    assert estate == expected_active_ids
    assert SUBSTITUTED_OUT_ID in estate
    assert SUBSTITUTED_IN_ID not in estate
