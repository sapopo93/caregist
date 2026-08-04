from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

asyncpg = pytest.importorskip("asyncpg")

REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_SQL = REPO_ROOT / "db" / "init.sql"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
DATABASE_URL = os.getenv("CAREGIST_TEST_DATABASE_URL")


def _shim_without_postgis(sql: str) -> str:
    sql = sql.replace("CREATE EXTENSION IF NOT EXISTS postgis;", "-- PostGIS shim")
    sql = sql.replace("GEOMETRY(Point, 4326)", "TEXT")
    return re.sub(r".*USING GIST \(geom\).*\n", "", sql)


async def _postgis_available(conn) -> bool:
    return bool(await conn.fetchval("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'"))


async def apply_schema_through(conn, final_migration: int = 999) -> list[str]:
    init_sql = INIT_SQL.read_text(encoding="utf-8")
    if not await _postgis_available(conn):
        init_sql = _shim_without_postgis(init_sql)
    await conn.execute(init_sql)
    applied: list[str] = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        if int(path.name.split("_", 1)[0]) > final_migration:
            continue
        body = path.read_text(encoding="utf-8").strip()
        if not body:
            continue
        async with conn.transaction():
            await conn.execute(body)
        applied.append(path.name)
    return applied


async def apply_full_schema(conn) -> list[str]:
    return await apply_schema_through(conn)


@pytest.fixture
async def fresh_db():
    if not DATABASE_URL:
        pytest.skip("CAREGIST_TEST_DATABASE_URL is required")
    admin = await asyncpg.connect(DATABASE_URL)
    database_name = f"caregist_cqc_test_{os.getpid()}"
    await admin.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    await admin.execute(f'CREATE DATABASE "{database_name}"')
    await admin.close()
    test_url = f"{DATABASE_URL.rsplit('/', 1)[0]}/{database_name}"
    try:
        yield test_url
    finally:
        admin = await asyncpg.connect(DATABASE_URL)
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()",
            database_name,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        await admin.close()
