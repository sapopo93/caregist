"""Real-Postgres check of migration 071 and the scope store.

Skipped unless SCOPE_PG_URL points at a disposable database. It works in its own
schema (``scope_pg_test``), applies 060 and 071 there and drops it afterwards, so it
touches nothing else. Never point it at production.

    SCOPE_PG_URL=postgresql://user@localhost/scratch python -m pytest tests/test_territory_brief_scope_pg.py -q
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.services import territory_brief_scope_store as store
from api.services.territory_brief import TerritoryScope

URL = os.environ.get("SCOPE_PG_URL")
MIGRATIONS = Path(__file__).resolve().parents[1] / "db" / "migrations"
pytestmark = pytest.mark.skipif(not URL, reason="set SCOPE_PG_URL to a scratch Postgres")

RULES = TerritoryScope(
    kind="local_authority",
    name="Southampton",
    buyer_objective="Governance support for West Midlands domiciliary care providers",
    excluded_provider_ids=("1-100000001", "1-100000002"),
    excluded_location_ids=("1-200000001",),
)


async def _fresh():
    import asyncpg

    conn = await asyncpg.connect(URL)
    await conn.execute("DROP SCHEMA IF EXISTS scope_pg_test CASCADE; CREATE SCHEMA scope_pg_test")
    await conn.execute("SET search_path TO scope_pg_test")
    await conn.execute((MIGRATIONS / "060_territory_brief_fulfilment.sql").read_text())
    await conn.execute((MIGRATIONS / "071_territory_brief_buyer_scope.sql").read_text())
    return conn


async def _order(conn, n=1):
    row = await conn.fetchrow(
        "INSERT INTO territory_brief_orders (customer_email, stripe_price_id, scope_kind, scope_name) "
        "VALUES ($1, 'price_x', 'region', 'South East') RETURNING id",
        f"b{n}@example.com",
    )
    return str(row["id"])


@pytest.mark.asyncio
async def test_round_trip_isolation_freeze_and_retention():
    conn = await _fresh()
    try:
        a, b = await _order(conn, 1), await _order(conn, 2)
        ref = await store.insert_scope_version(conn, a, RULES)
        loaded = await store.load_scope_rules(conn, ref, a)
        assert loaded["excluded_provider_ids"] == ["1-100000001", "1-100000002"]

        # Another order cannot read this order's scope.
        with pytest.raises(LookupError):
            await store.load_scope_rules(conn, ref, b)

        # The frozen scope cannot be edited or deleted; retention columns can move.
        with pytest.raises(Exception, match="frozen"):
            await conn.execute("UPDATE territory_brief_scope_versions SET buyer_objective = 'changed text here' WHERE id = $1", ref)
        with pytest.raises(Exception, match="retained as evidence"):
            await conn.execute("DELETE FROM territory_brief_scope_versions WHERE id = $1", ref)

        # An identifier that is not a CQC id is refused by the schema, not just the API.
        with pytest.raises(Exception, match="check constraint"):
            await conn.execute(
                "INSERT INTO territory_brief_scope_exclusions VALUES ($1, 'provider', 'Acme Care Ltd')", ref
            )

        # Amendments are new versions linked to the original.
        ref2 = await store.insert_scope_version(conn, a, RULES, version=2)
        sup = await conn.fetchval("SELECT supersedes_version FROM territory_brief_scope_versions WHERE id = $1", ref2)
        assert sup == 1

        # Retention: nothing is due until the window passes; then purge keeps the row and hash.
        await store.schedule_exclusion_purge(conn, ref)
        assert (await store.purge_expired_exclusions(conn, apply=True))["scope_versions_due"] == 0
        await conn.execute(
            "UPDATE territory_brief_scope_versions SET exclusions_purge_after = NOW() - INTERVAL '1 day' WHERE id = $1", ref
        )
        dry = await store.purge_expired_exclusions(conn)
        assert dry["scope_versions_due"] == 1 and dry["exclusion_rows_deleted"] == 0
        done = await store.purge_expired_exclusions(conn, apply=True)
        assert done == {"scope_versions_due": 1, "exclusion_rows_deleted": 3}
        row = await conn.fetchrow("SELECT scope_sha256, exclusions_purged_at, provider_exclusion_count FROM territory_brief_scope_versions WHERE id = $1", ref)
        assert row["scope_sha256"] == store.scope_rules_sha256(RULES) and row["exclusions_purged_at"] is not None
        assert row["provider_exclusion_count"] == 2
        with pytest.raises(LookupError):
            await store.load_scope_rules(conn, ref, a)  # cannot regenerate without the list

        # Legacy order (no scope version) is untouched.
        assert await conn.fetchval("SELECT COUNT(*) FROM territory_brief_scope_versions WHERE order_id = $1", b) == 0

        # Down migration is clean.
        await conn.execute((MIGRATIONS / "down" / "071_territory_brief_buyer_scope.down.sql").read_text())
        assert await conn.fetchval("SELECT to_regclass('territory_brief_scope_exclusions')") is None
        assert await conn.fetchval("SELECT COUNT(*) FROM territory_brief_orders") == 2
    finally:
        await conn.execute("DROP SCHEMA IF EXISTS scope_pg_test CASCADE")
        await conn.close()
