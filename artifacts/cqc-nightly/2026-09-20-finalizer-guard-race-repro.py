"""Chief of Staff independent verification: is the identity guard sound under concurrency?

Scratch module, NOT part of the reviewed commit. It lives in a throwaway worktree
at c192eb6 and modifies no product file. It drives the real `_finalize_batch` and
commits a count-neutral identity substitution from a second connection inside the
one window the guard cannot see: after its end-state read of the ACTIVE id set
(incremental_update.py:2154-2157) but before its commit (incremental_update.py:2284).

The interleaving is pinned deterministically by wrapping the single `json.dumps`
call the success path makes at incremental_update.py:2265 (inside the
`UPDATE pipeline_runs` arguments, i.e. strictly after both end-state reads and
strictly before the commit). Nothing about the product code is changed: the hook
releases the finalizer once the substitution has been committed.

If the guard were sound under concurrency the finalize would refuse. If it is not,
the batch is marked completed with `active_identity_verified: true` while the
ACTIVE estate no longer matches the authoritative manifest -- a silent false
assurance in the ingestion path, the same class of defect as a green verdict
without evidence.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import psycopg2
import pytest

asyncpg = pytest.importorskip("asyncpg")

from tests.integration import test_finalize_guard_pg as _guard

pytestmark = pytest.mark.asyncio

MANIFEST_IDS = _guard.MANIFEST_IDS
ROGUE_IDS = _guard.ROGUE_IDS
EXTRA_ID = "1-97001"


async def test_guard_is_defeated_by_a_substitution_committed_after_its_read(
    tmp_path, fresh_db, monkeypatch
):
    missing_id = MANIFEST_IDS[7]
    payloads = {rogue: {"registrationStatus": "Deregistered"} for rogue in ROGUE_IDS}
    batch_id = await _guard._seed_rogue_candidates(tmp_path, fresh_db, payloads)
    monkeypatch.setattr(
        "incremental_update.fetch_location_detail", _guard._detail_fetcher(payloads)
    )
    print("batch_id under test:", batch_id)
    print("missing (leaves ACTIVE):", missing_id, "| extra (joins ACTIVE):", EXTRA_ID)

    # Control: prove the batch row really is lockable from a second connection, so
    # a non-blocking result cannot be explained away as a connection to elsewhere.
    probe = psycopg2.connect(fresh_db)
    probe.autocommit = False
    try:
        with probe.cursor() as probe_cur:
            probe_cur.execute("SET statement_timeout = 2000")
            probe_cur.execute(
                "SELECT status FROM reconciliation_batches WHERE id = %s FOR UPDATE",
                (str(batch_id),),
            )
            print("control: batch row lock acquired, status =", probe_cur.fetchone()[0])
    finally:
        probe.rollback()
        probe.close()

    import incremental_update as iu

    real_dumps = iu.json.dumps
    armed = threading.Event()
    reached = threading.Event()
    release = threading.Event()

    def _hooked_dumps(obj, *args, **kwargs):
        if (
            armed.is_set()
            and not reached.is_set()
            and isinstance(obj, dict)
            and obj.get("fullCoverage") is True
        ):
            reached.set()
            release.wait(60)
        return real_dumps(obj, *args, **kwargs)

    monkeypatch.setattr(iu.json, "dumps", _hooked_dumps)

    outcome: dict[str, Any] = {}

    def _run() -> None:
        try:
            outcome["rc"] = _guard._run_finalize(
                fresh_db, batch_id, tmp_path, dry_run=False, api_key="integration-test-key"
            )
        except BaseException as exc:  # noqa: BLE001 - a refusal is the sound outcome
            outcome["exc"] = exc

    armed.set()
    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    try:
        pinned = reached.wait(120)
        print("pinned after the guard's read, before its commit:", pinned)
        assert pinned, (
            "the finalizer never reached the post-read / pre-commit point, so no "
            "interleaving was established and this run proves nothing"
        )

        # Inside the window. Both statements are count-neutral: one manifest
        # location leaves the ACTIVE set, one unexplained location joins it.
        drift = psycopg2.connect(fresh_db)
        drift.autocommit = True
        try:
            with drift.cursor() as drift_cur:
                drift_cur.execute(
                    "UPDATE care_providers SET status = 'INACTIVE' WHERE id = %s",
                    (missing_id,),
                )
                drift_cur.execute(
                    """
                    INSERT INTO care_providers (id, name, slug, status)
                    VALUES (%s, %s, %s, 'ACTIVE')
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (EXTRA_ID, "Unexplained Provider", "provider-unexplained"),
                )
            print("substitution committed inside the window:",
                  missing_id, "-> INACTIVE,", EXTRA_ID, "-> ACTIVE")
        finally:
            drift.close()
    finally:
        release.set()
        worker.join(timeout=180)

    print("finalizer still alive after join:", worker.is_alive())
    print("outcome:", {key: repr(value)[:400] for key, value in outcome.items()})

    async_conn = await asyncpg.connect(fresh_db)
    try:
        row = await _guard._batch_row(async_conn, batch_id)
        actual = {
            str(record["id"])
            for record in await async_conn.fetch(
                "SELECT id FROM care_providers WHERE UPPER(status) = 'ACTIVE'"
            )
        }
        recorded = json.loads(
            await async_conn.fetchval(
                "SELECT deactivation_confirmation FROM reconciliation_batches WHERE id = $1",
                batch_id,
            )
        )
        print("batch status:", row["status"], "| run_status:", row["run_status"],
              "| counts_reconciled:", row["counts_reconciled"])
        print("guard recorded: verified =", recorded.get("active_identity_verified"),
              "| missing =", recorded.get("missing_active_ids"),
              "| extra =", recorded.get("extra_active_ids"),
              "| expected_count =", recorded.get("expected_active_ids_count"),
              "| after_count =", recorded.get("active_after_ids_count"))
        print("true estate: ACTIVE total =", len(actual),
              "| manifest member still ACTIVE?", missing_id in actual,
              "| unexplained location ACTIVE?", EXTRA_ID in actual)

        # The demonstration, asserted on rows the guard itself wrote.
        assert "exc" not in outcome, f"finalizer refused (the sound outcome): {outcome.get('exc')!r}"
        assert outcome.get("rc") == 0
        assert row["status"] == "completed"
        assert recorded["active_identity_verified"] is True
        assert recorded["missing_active_ids"] == []
        assert recorded["extra_active_ids"] == []
        assert missing_id not in actual
        assert EXTRA_ID in actual
        assert len(actual) == recorded["expected_active_ids_count"]
    finally:
        await async_conn.close()
