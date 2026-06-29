"""Integration test: replay init.sql + every migration against a real Postgres.

Closes audit finding F-27. All other tests mock asyncpg; this one proves the
migration chain actually applies in order and that the data-integrity
invariants from migration 032 are enforced by the database.

The test is skipped unless a Postgres connection is provided via
``CAREGIST_TEST_DATABASE_URL`` (or ``DATABASE_URL``). In CI this is supplied by
a ``postgres`` service container. Locally you can point it at a throwaway DB.

PostGIS is optional: if the server lacks the extension, ``init.sql`` is applied
with the geometry column/index shimmed to plain ``TEXT`` so the rest of the
schema and every migration still get exercised. Migration SQL itself never
depends on PostGIS.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

asyncpg = pytest.importorskip("asyncpg")

REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_SQL = REPO_ROOT / "db" / "init.sql"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

DATABASE_URL = os.getenv("CAREGIST_TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not DATABASE_URL,
        reason="Set CAREGIST_TEST_DATABASE_URL to run the migration replay test.",
    ),
    pytest.mark.asyncio,
]


async def _postgis_available(conn) -> bool:
    row = await conn.fetchval(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'"
    )
    return bool(row)


def _shim_init_without_postgis(sql: str) -> str:
    sql = sql.replace(
        "CREATE EXTENSION IF NOT EXISTS postgis;",
        "-- postgis unavailable: shimmed for migration replay test",
    )
    sql = sql.replace("GEOMETRY(Point, 4326)", "TEXT")
    sql = re.sub(r".*USING GIST \(geom\).*\n", "", sql)
    return sql


async def _apply_sql_files(conn, init_sql: str) -> list[str]:
    await conn.execute(init_sql)
    applied: list[str] = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        body = path.read_text(encoding="utf-8").strip()
        if not body:
            continue
        async with conn.transaction():
            await conn.execute(body)
        applied.append(path.name)
    return applied


@pytest.fixture
async def fresh_db():
    """Create and drop an isolated database for a clean replay."""
    admin = await asyncpg.connect(DATABASE_URL)
    dbname = f"caregist_migtest_{os.getpid()}"
    await admin.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
    await admin.execute(f'CREATE DATABASE "{dbname}"')
    await admin.close()

    base = DATABASE_URL.rsplit("/", 1)[0]
    test_url = f"{base}/{dbname}"
    try:
        yield test_url
    finally:
        admin = await asyncpg.connect(DATABASE_URL)
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            dbname,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        await admin.close()


async def test_full_migration_chain_applies(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        init_sql = INIT_SQL.read_text(encoding="utf-8")
        if not await _postgis_available(conn):
            init_sql = _shim_init_without_postgis(init_sql)

        applied = await _apply_sql_files(conn, init_sql)

        # Every numbered migration ran.
        assert applied, "no migrations were applied"
        assert "032_data_integrity_constraints.sql" in applied

        # Smoke queries against the resulting schema.
        assert await conn.fetchval("SELECT COUNT(*) FROM care_providers") == 0
        assert await conn.fetchval("SELECT COUNT(*) FROM subscriptions") == 0

        # F-12 / F-13: integrity foreign keys exist.
        fks = {
            r["conname"]
            for r in await conn.fetch(
                "SELECT conname FROM pg_constraint WHERE contype = 'f'"
            )
        }
        assert "fk_rating_changes_provider" in fks
        assert "fk_trusted_event_ledger_location" in fks

        # F-14: partial unique index enforces one active subscription per user.
        idx = {
            r["indexname"]
            for r in await conn.fetch(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'subscriptions'"
            )
        }
        assert "uniq_active_sub_per_user" in idx
    finally:
        await conn.close()


async def test_active_subscription_uniqueness_is_enforced(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        init_sql = INIT_SQL.read_text(encoding="utf-8")
        if not await _postgis_available(conn):
            init_sql = _shim_init_without_postgis(init_sql)
        await _apply_sql_files(conn, init_sql)

        user_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash, name) "
            "VALUES ('mig@test.com', 'x', 'Mig') RETURNING id"
        )
        await conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status) VALUES ($1, 'pro', 'active')",
            user_id,
        )
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                "INSERT INTO subscriptions (user_id, tier, status) "
                "VALUES ($1, 'business', 'active')",
                user_id,
            )
        # A non-active duplicate is allowed.
        await conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status) "
            "VALUES ($1, 'business', 'canceled')",
            user_id,
        )
    finally:
        await conn.close()
