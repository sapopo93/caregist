"""Shared fixtures for integration tests that need a real Postgres.

Skipped unless the explicit CAREGIST_TEST_DATABASE_URL is set. The URL must
target an isolated local host. PostGIS is optional — init.sql is shimmed to
plain TEXT when the extension is unavailable.

Row-level security is only testable by a role that RLS actually applies to, so
the fixture guarantees the test connection is a NOSUPERUSER, NOBYPASSRLS role
that owns the throwaway database and everything the schema creates in it. When
CAREGIST_TEST_DATABASE_URL already names such a role it is used as-is; when it
names a superuser or a BYPASSRLS role (a stand-in for the local throwaway
cluster, where initdb's bootstrap role is the only login role that exists) a
dedicated role is provisioned instead of letting the assertions run against a
role that would ignore every policy and pass or fail for the wrong reason.
"""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from urllib.parse import quote, urlparse

import pytest

asyncpg = pytest.importorskip("asyncpg")

REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_SQL = REPO_ROOT / "db" / "init.sql"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

DATABASE_URL = os.getenv("CAREGIST_TEST_DATABASE_URL")
ADMIN_DATABASE_URL = os.getenv("CAREGIST_TEST_ADMIN_DATABASE_URL") or DATABASE_URL
_ROLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# The role the RLS assertions run as when the configured role cannot see RLS at
# all. Named so a reader of a failing run can tell which role was under test.
RLS_ROLE = os.getenv("CAREGIST_TEST_RLS_ROLE", "caregist_rls_test")


def validate_test_database_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("CAREGIST_TEST_DATABASE_URL must target an isolated local host.")
    database = parsed.path.removeprefix("/")
    if database in {"caregist", "caregist_prod", "production"}:
        raise RuntimeError("CAREGIST_TEST_DATABASE_URL must not target a production database.")


async def role_can_see_rls(conn, role: str) -> bool:
    """Whether ``role`` is subject to row-level security.

    A superuser or a BYPASSRLS role bypasses every policy, so any assertion
    made through it is about the bypass, not about the invariant.
    """
    row = await conn.fetchrow(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = $1", role
    )
    if row is None:
        return False
    return not row["rolsuper"] and not row["rolbypassrls"]


async def provision_rls_role(admin, role: str) -> str:
    """Create (or refresh) a dedicated non-superuser login role; return its password.

    The role is deliberately the weakest thing that can still own a schema —
    LOGIN, NOSUPERUSER, NOBYPASSRLS, NOCREATEDB, NOCREATEROLE — because that is
    the only kind of role for which the RLS assertions measure anything.
    """
    if not _ROLE_NAME_RE.fullmatch(role):
        raise RuntimeError(f"CAREGIST_TEST_RLS_ROLE is not a valid role name: {role!r}")
    password = secrets.token_urlsafe(32)
    literal = "'" + password + "'"
    exists = await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", role)
    attributes = "LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
    if exists:
        await admin.execute(f'ALTER ROLE "{role}" WITH {attributes} PASSWORD {literal}')
    else:
        await admin.execute(f'CREATE ROLE "{role}" WITH {attributes} PASSWORD {literal}')
    if not await role_can_see_rls(admin, role):
        raise RuntimeError(
            f"the RLS test role {role!r} is still a superuser or BYPASSRLS role, so the "
            "row-level-security assertions would be measuring the bypass"
        )
    return password


async def test_connection_url(admin, *, dbname: str, configured_role: str) -> str:
    """The URL the tests connect with: RLS-visible role, password already in place."""
    if not DATABASE_URL:  # the fixture skips before this point; belt and braces
        raise RuntimeError("CAREGIST_TEST_DATABASE_URL is not set")
    if await role_can_see_rls(admin, configured_role):
        base = DATABASE_URL.rsplit("/", 1)[0]
        return f"{base}/{dbname}"
    password = await provision_rls_role(admin, RLS_ROLE)
    parsed = urlparse(DATABASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    return f"postgresql://{quote(RLS_ROLE, safe='')}:{quote(password, safe='')}@{host}:{port}/{dbname}"


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


async def apply_full_schema(conn, *, through: str | None = None) -> list[str]:
    """Apply init.sql and numbered migrations, optionally stopping at one filename."""
    init_sql = INIT_SQL.read_text(encoding="utf-8")
    if not await postgis_available(conn):
        init_sql = shim_init_without_postgis(init_sql)
    await conn.execute(init_sql)

    applied: list[str] = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        if through is not None and path.name > through:
            break
        body = path.read_text(encoding="utf-8").strip()
        if not body:
            continue
        async with conn.transaction():
            await conn.execute(body)
        applied.append(path.name)
        if path.name == through:
            break
    return applied


@pytest.fixture
async def fresh_db():
    """Create and drop an isolated database with the full schema applied."""
    if not DATABASE_URL:
        pytest.skip("Set the explicit isolated CAREGIST_TEST_DATABASE_URL to run integration tests.")
    validate_test_database_url(DATABASE_URL)

    if not ADMIN_DATABASE_URL:
        pytest.skip("Set the explicit isolated CAREGIST_TEST_DATABASE_URL to run integration tests.")
    validate_test_database_url(ADMIN_DATABASE_URL)

    parsed_test_url = urlparse(DATABASE_URL)
    configured = parsed_test_url.username
    if not isinstance(configured, str) or not _ROLE_NAME_RE.fullmatch(configured):
        raise RuntimeError("CAREGIST_TEST_DATABASE_URL must contain a valid test role name.")
    owner = configured

    dbname = f"caregist_ittest_{os.getpid()}"
    admin = await asyncpg.connect(ADMIN_DATABASE_URL)
    try:
        # The database is owned by the role the tests connect with. That role has
        # to be one RLS applies to, otherwise FORCE ROW LEVEL SECURITY is tested
        # against a connection that bypasses it: see test_connection_url.
        test_url = await test_connection_url(admin, dbname=dbname, configured_role=owner)
        connect_role = urlparse(test_url).username
        if connect_role is None or not _ROLE_NAME_RE.fullmatch(connect_role):
            raise RuntimeError("the RLS test role name must be a valid role name.")
        await admin.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        await admin.execute(f'CREATE DATABASE "{dbname}" OWNER "{connect_role}"')
        # Owner privileges are implied, but the grant is explicit so a reader can
        # see the test role was given the database rather than inheriting it by
        # accident of who ran initdb.
        await admin.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{dbname}" TO "{connect_role}"')
        validate_test_database_url(test_url)
    finally:
        await admin.close()

    try:
        if os.getenv("CAREGIST_TEST_ADMIN_DATABASE_URL"):
            admin_base = ADMIN_DATABASE_URL.rsplit("/", 1)[0]
            test_admin_url = f"{admin_base}/{dbname}"
            admin = await asyncpg.connect(test_admin_url)
            try:
                if await postgis_available(admin):
                    await admin.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            finally:
                await admin.close()
        yield test_url
    finally:
        admin = await asyncpg.connect(ADMIN_DATABASE_URL)
        try:
            try:
                await admin.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = $1 AND pid <> pg_backend_pid()",
                    dbname,
                )
            finally:
                await admin.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        finally:
            await admin.close()
