"""Real-Postgres proof for migration 073 (rebuild pre-060 Territory Brief tables).

Production's Brief orders and token tables existed before 060 ran, so 060's
CREATE TABLE IF NOT EXISTS skipped them and 072 then failed on the missing
artifact_kind column (30 Oct 2026). These tests recreate that history: the
chain to 059, an older-design orders and tokens table, then 060 onwards.

Skipped unless CAREGIST_TEST_DATABASE_URL is set; see tests/integration/conftest.py.
"""

from __future__ import annotations

import asyncio

import pytest

from tests.integration.conftest import MIGRATIONS_DIR, apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio

BRIEF_TABLES = (
    "territory_brief_orders",
    "territory_brief_consents",
    "territory_brief_download_tokens",
    "territory_brief_scope_versions",
    "territory_brief_scope_exclusions",
)

# An older design, close to what production holds: no scope_* columns, a single
# blob path, and tokens without artifact_kind.
PRE_060_TABLES = """
CREATE TABLE territory_brief_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stripe_checkout_session_id TEXT UNIQUE,
  customer_email TEXT NOT NULL,
  territory TEXT,
  buyer_type TEXT,
  service_focus TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  blob_pathname TEXT,
  record_count INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE territory_brief_download_tokens (
  token_hash CHAR(64) PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES territory_brief_orders(id),
  expires_at TIMESTAMPTZ NOT NULL,
  download_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def _apply_from(conn, first: str, last: str | None = None) -> list[str]:
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        if path.name < first:
            continue
        if last is not None and path.name > last:
            break
        async with conn.transaction():
            await conn.execute(path.read_text(encoding="utf-8"))
        applied.append(path.name)
    return applied


async def _columns(conn, table: str) -> set[str]:
    rows = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = $1",
        table,
    )
    return {row["column_name"] for row in rows}


async def _schema_signature(conn):
    columns = await conn.fetch(
        "SELECT table_name,column_name,data_type,is_nullable,column_default "
        "FROM information_schema.columns WHERE table_schema=current_schema() "
        "AND table_name=ANY($1::text[]) ORDER BY table_name,column_name", list(BRIEF_TABLES)
    )
    constraints = await conn.fetch(
        "SELECT conrelid::regclass::text AS tbl,pg_get_constraintdef(oid) AS def "
        "FROM pg_constraint WHERE conrelid=ANY(SELECT to_regclass(t) "
        "FROM unnest($1::text[]) t) ORDER BY 1,2", list(BRIEF_TABLES)
    )
    return [dict(r) for r in columns], [dict(r) for r in constraints]


async def _insert_current_order_with_zip_token(conn) -> None:
    order_id = await conn.fetchval(
        "INSERT INTO territory_brief_orders "
        "(customer_email, stripe_price_id, scope_kind, scope_name) "
        "VALUES ('buyer@example.test', 'price_test', 'local_authority', 'Leeds') RETURNING id"
    )
    await conn.execute(
        "INSERT INTO territory_brief_download_tokens (token_hash, order_id, artifact_kind, expires_at) "
        "VALUES ($1, $2, 'zip', NOW() + INTERVAL '1 day')",
        "a" * 64,
        order_id,
    )


async def test_073_rebuilds_empty_pre_060_tables(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn, through="059_widen_provider_phone.sql")
        await conn.execute(PRE_060_TABLES)

        applied = await _apply_from(conn, "060", "073_rebuild_territory_brief_tables.sql")
        assert applied[-1] == "073_rebuild_territory_brief_tables.sql"
        assert "072_shared_customer_package.sql" in applied

        orders = await _columns(conn, "territory_brief_orders")
        assert {"scope_kind", "generation_attempts", "blob_pdf_pathname", "package_sha256"} <= orders
        assert not {"territory", "buyer_type", "blob_pathname", "record_count"} & orders
        assert "artifact_kind" in await _columns(conn, "territory_brief_download_tokens")
        assert "source_edition_id" in orders
        assert await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint "
            "WHERE conrelid = 'territory_brief_orders'::regclass "
            "AND confrelid = 'territory_brief_source_editions'::regclass "
            "AND contype = 'f' AND confdeltype = 'r')"
        )
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await conn.execute(
                "INSERT INTO territory_brief_orders "
                "(customer_email, stripe_price_id, scope_kind, scope_name, source_edition_id) "
                "VALUES ('buyer@example.test', 'price_test', 'region', 'North East', -1)"
            )
        for table in BRIEF_TABLES:
            assert await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table)

        rebuilt_signature = await _schema_signature(conn)
        # Compare all columns/defaults/nullability and constraints with a clean
        # chain, so columns added between 060 and 072 cannot silently disappear.
        comparison = conn.transaction()
        await comparison.start()
        try:
            for table in ("territory_brief_scope_exclusions", "territory_brief_scope_versions",
                          "territory_brief_consents", "territory_brief_download_tokens",
                          "territory_brief_orders"):
                await conn.execute(f"DROP TABLE {table}")
            for prefix in ("060", "066", "071", "072"):
                path = next(MIGRATIONS_DIR.glob(f"{prefix}_*.sql"))
                if prefix == "066":
                    # Its immutable source tables already exist; only restore
                    # the order binding that this migration adds.
                    await conn.execute(
                        "ALTER TABLE territory_brief_orders ADD COLUMN source_edition_id "
                        "BIGINT REFERENCES territory_brief_source_editions(id) ON DELETE RESTRICT"
                    )
                else:
                    # 060/071 functions already exist from the historical run.
                    sql = path.read_text().replace("CREATE FUNCTION ", "CREATE OR REPLACE FUNCTION ")
                    await conn.execute(sql)
            assert await _schema_signature(conn) == rebuilt_signature
        finally:
            # Exercise ZIP/uniqueness/triggers below against the actual 073
            # rebuild, rather than leaving the comparison schema in place.
            await comparison.rollback()

        await _insert_current_order_with_zip_token(conn)
        order_id = await conn.fetchval("SELECT id FROM territory_brief_orders")
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                "INSERT INTO territory_brief_download_tokens (token_hash, order_id, artifact_kind, expires_at) "
                "VALUES ($1, $2, 'zip', NOW() + INTERVAL '1 day')",
                "b" * 64,
                order_id,
            )
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                "INSERT INTO territory_brief_download_tokens (token_hash, order_id, artifact_kind, expires_at) "
                "VALUES ($1, $2, 'xlsx', NOW() + INTERVAL '1 day')",
                "c" * 64,
                order_id,
            )

        # Triggers came back with the tables.
        scope_id = await conn.fetchval(
            "INSERT INTO territory_brief_scope_versions (order_id, scope_sha256) "
            "VALUES ($1, $2) RETURNING id",
            order_id,
            "d" * 64,
        )
        with pytest.raises(asyncpg.RaiseError):
            await conn.execute("DELETE FROM territory_brief_scope_versions WHERE id = $1", scope_id)
    finally:
        await conn.close()


async def test_073_refuses_when_an_old_table_holds_a_row(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn, through="059_widen_provider_phone.sql")
        await conn.execute(PRE_060_TABLES)
        await conn.execute(
            "INSERT INTO territory_brief_orders (customer_email, territory) VALUES ('old@example.test', 'Leeds')"
        )
        await _apply_from(conn, "060", "072_shared_customer_package.sql")

        body = (MIGRATIONS_DIR / "073_rebuild_territory_brief_tables.sql").read_text(encoding="utf-8")
        with pytest.raises(asyncpg.RaiseError, match="Refusing to rebuild territory_brief_orders"):
            async with conn.transaction():
                await conn.execute(body)

        # Rolled back: the old design and its row are untouched.
        assert "territory" in await _columns(conn, "territory_brief_orders")
        assert await conn.fetchval("SELECT COUNT(*) FROM territory_brief_orders") == 1
    finally:
        await conn.close()


async def test_073_leaves_current_tables_and_their_rows_alone(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn, through="072_shared_customer_package.sql")
        await _insert_current_order_with_zip_token(conn)

        body = (MIGRATIONS_DIR / "073_rebuild_territory_brief_tables.sql").read_text(encoding="utf-8")
        async with conn.transaction():
            await conn.execute(body)

        assert await conn.fetchval("SELECT COUNT(*) FROM territory_brief_orders") == 1
        assert await conn.fetchval("SELECT COUNT(*) FROM territory_brief_download_tokens") == 1
    finally:
        await conn.close()


async def test_073_refuses_row_committed_while_waiting_for_table_lock(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    writer = await asyncpg.connect(fresh_db)
    task = None
    try:
        await apply_full_schema(conn, through="059_widen_provider_phone.sql")
        await conn.execute(PRE_060_TABLES)
        await _apply_from(conn, "060", "072_shared_customer_package.sql")
        body = (MIGRATIONS_DIR / "073_rebuild_territory_brief_tables.sql").read_text()

        async def migrate():
            async with conn.transaction():
                await conn.execute("SET LOCAL statement_timeout = '10s'")
                await conn.execute(body)

        async with writer.transaction():
            await writer.execute("LOCK TABLE territory_brief_orders IN ACCESS SHARE MODE")
            pid = await conn.fetchval("SELECT pg_backend_pid()")
            task = asyncio.create_task(migrate())
            for _ in range(100):
                waiting = await writer.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=$1 "
                    "AND relation='territory_brief_orders'::regclass AND NOT granted)", pid
                )
                if waiting:
                    break
                await asyncio.sleep(0.02)
            assert waiting, "migration did not reach the conflicting table lock"
            await writer.execute(
                "INSERT INTO territory_brief_orders(customer_email, territory) "
                "VALUES ('concurrent@example.test', 'Leeds')"
            )

        with pytest.raises(asyncpg.RaiseError, match="Refusing to rebuild territory_brief_orders"):
            await task
        assert await conn.fetchval("SELECT count(*) FROM territory_brief_orders") == 1
        assert "territory" in await _columns(conn, "territory_brief_orders")
        for table in BRIEF_TABLES:
            assert await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table)
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await writer.close()
        await conn.close()


async def test_073_unexpected_dependant_rolls_back_all_drops(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn, through="059_widen_provider_phone.sql")
        await conn.execute(PRE_060_TABLES)
        await _apply_from(conn, "060", "072_shared_customer_package.sql")
        await conn.execute("CREATE VIEW brief_legacy_view AS SELECT id FROM territory_brief_orders")
        body = (MIGRATIONS_DIR / "073_rebuild_territory_brief_tables.sql").read_text()
        with pytest.raises(asyncpg.DependentObjectsStillExistError):
            async with conn.transaction():
                await conn.execute(body)
        assert "territory" in await _columns(conn, "territory_brief_orders")
        assert await conn.fetchval("SELECT to_regclass('brief_legacy_view') IS NOT NULL")
        for table in BRIEF_TABLES:
            assert await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table)
    finally:
        await conn.close()

