"""Integration test: replay init.sql + every migration against a real Postgres.

Closes audit finding F-27. All other tests mock asyncpg; this one proves the
migration chain actually applies in order and that the data-integrity
invariants from migration 032 are enforced by the database.

Skipped unless CAREGIST_TEST_DATABASE_URL (or DATABASE_URL) is set; see the
shared fixtures in tests/integration/conftest.py.
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio


async def test_full_migration_chain_applies(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        applied = await apply_full_schema(conn)

        assert applied, "no migrations were applied"
        assert "032_data_integrity_constraints.sql" in applied

        assert await conn.fetchval("SELECT COUNT(*) FROM care_providers") == 0
        assert await conn.fetchval("SELECT COUNT(*) FROM subscriptions") == 0

        # F-12 / F-13: integrity foreign keys exist.
        fks = {
            r["conname"]
            for r in await conn.fetch("SELECT conname FROM pg_constraint WHERE contype = 'f'")
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
        await apply_full_schema(conn)

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
