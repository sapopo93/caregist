"""The finalize table lock retries in short bounded waits, on real Postgres.

A single 5s lock_timeout used to abandon a whole reconciliation batch when an
hourly CQC signal poll held care_providers (26 Oct 2026). The helper now retries
inside a savepoint: each wait stays at 5s, the advisory locks taken before it
stay held, and it still gives up after its attempts.
"""

from __future__ import annotations

import os
import threading
import time

import pytest

psycopg2 = pytest.importorskip("psycopg2")

import incremental_update as iu  # noqa: E402

URL = os.getenv("CAREGIST_TEST_ADMIN_DATABASE_URL") or os.getenv("CAREGIST_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not os.getenv("CAREGIST_TEST_DATABASE_URL"), reason="CAREGIST_TEST_DATABASE_URL not set")
SCHEMA = "finalize_lock_test"


@pytest.fixture
def table():
    admin = psycopg2.connect(URL)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE; CREATE SCHEMA {SCHEMA}")
        cur.execute(f"CREATE TABLE {SCHEMA}.care_providers (id text PRIMARY KEY, status text)")
        cur.execute(f"INSERT INTO {SCHEMA}.care_providers VALUES ('1-A', 'ACTIVE')")
    yield
    with admin.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    admin.close()


def _conn():
    return psycopg2.connect(URL, options=f"-csearch_path={SCHEMA}")


def _hold_writer_lock(seconds: float, ready: threading.Event) -> None:
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE care_providers SET status = 'ACTIVE' WHERE id = '1-A'")  # ROW EXCLUSIVE
            ready.set()
            time.sleep(seconds)
        conn.commit()
    finally:
        conn.close()


def test_lock_is_taken_after_a_writer_releases_and_earlier_locks_survive(table):
    ready = threading.Event()
    writer = threading.Thread(target=_hold_writer_lock, args=(7.0, ready))
    writer.start()
    ready.wait(5)
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('finalize-lock-test', 0))")
            started = time.monotonic()
            iu._lock_care_providers_for_finalize(cur, attempts=5, pause_s=1.0)
            assert time.monotonic() - started >= 5  # it really did have to retry
            cur.execute(
                "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
            )
            assert cur.fetchone()[0] == 1  # the savepoint rollback kept the advisory lock
            cur.execute("SELECT count(*) FROM care_providers")  # the transaction is still usable
            assert cur.fetchone()[0] == 1
        conn.rollback()
    finally:
        conn.close()
        writer.join()


def test_gives_up_after_its_attempts_when_the_table_stays_busy(table):
    ready = threading.Event()
    writer = threading.Thread(target=_hold_writer_lock, args=(20.0, ready))
    writer.start()
    ready.wait(5)
    conn = _conn()
    try:
        with conn.cursor() as cur, pytest.raises(psycopg2.errors.LockNotAvailable):
            iu._lock_care_providers_for_finalize(cur, attempts=2, pause_s=0.5)
        conn.rollback()
    finally:
        conn.close()
        writer.join()
