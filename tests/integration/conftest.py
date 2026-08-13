"""Shared fixtures for integration tests that need a real Postgres.

Skipped unless the explicit CAREGIST_TEST_DATABASE_URL is set. The URL must
target an isolated local host. PostGIS is optional — init.sql is shimmed to
plain TEXT when the extension is unavailable.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

asyncpg = pytest.importorskip("asyncpg")

REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_SQL = REPO_ROOT / "db" / "init.sql"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

DATABASE_URL = os.getenv("CAREGIST_TEST_DATABASE_URL")


def validate_test_database_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("CAREGIST_TEST_DATABASE_URL must target an isolated local host.")
    database = parsed.path.removeprefix("/")
    if database in {"caregist", "caregist_prod", "production"}:
        raise RuntimeError("CAREGIST_TEST_DATABASE_URL must not target a production database.")


def shim_init_without_postgis(sql: str) -> str:
    sql = sql.replace(
        "CREATE EXTENSION IF NOT EXISTS postgis;",
        "-- postgis unavailable: shimmed for integration test",
    )
    sql = sql.replace("GEOMETRY(Point, 4326)", "TEXT")
    sql = re.sub(r".*USING GIST \(geom\).*\n", "", sql)
    return sql


async def postgis_available(conn) -> bool:
    return bool(
        await conn.fetchval("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'")
    )


async def apply_full_schema(conn) -> list[str]:
    """Apply init.sql + every numbered migration in order; return migration names."""
    init_sql = INIT_SQL.read_text(encoding="utf-8")
    if not await postgis_available(conn):
        init_sql = shim_init_without_postgis(init_sql)
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
    """Create and drop an isolated database with the full schema applied."""
    if not DATABASE_URL:
        pytest.skip("Set the explicit isolated CAREGIST_TEST_DATABASE_URL to run integration tests.")
    validate_test_database_url(DATABASE_URL)

    admin = await asyncpg.connect(DATABASE_URL)
    dbname = f"caregist_ittest_{os.getpid()}"
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
