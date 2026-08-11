"""Integration test: replay init.sql + every migration against a real Postgres.

Closes audit finding F-27. All other tests mock asyncpg; this one proves the
migration chain actually applies in order and that the data-integrity
invariants from migration 032 are enforced by the database.

Skipped unless CAREGIST_TEST_DATABASE_URL (or DATABASE_URL) is set; see the
shared fixtures in tests/integration/conftest.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from api.services.pipeline_health import unique_index_exists
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


async def test_source_snapshot_identity_migration_repairs_a_preexisting_table(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute(
            "ALTER TABLE source_snapshots "
            "DROP CONSTRAINT IF EXISTS source_snapshots_source_type_checksum_sha256_key"
        )
        await conn.execute("DROP INDEX IF EXISTS uniq_source_snapshots_identity")
        assert not await unique_index_exists(
            conn,
            "source_snapshots",
            ("source_type", "checksum_sha256"),
        )

        checksum = "a" * 64
        canonical_id = await conn.fetchval(
            """
            INSERT INTO source_snapshots (
              source_type, source_uri, source_checked_at, checksum_sha256, record_count
            ) VALUES ('cqc_location_index', 'https://example.test/first', NOW(), $1, 10)
            RETURNING id
            """,
            checksum,
        )
        duplicate_id = await conn.fetchval(
            """
            INSERT INTO source_snapshots (
              source_type, source_uri, source_checked_at, checksum_sha256, record_count
            ) VALUES ('cqc_location_index', 'https://example.test/second', NOW(), $1, 10)
            RETURNING id
            """,
            checksum,
        )
        await conn.execute(
            """
            INSERT INTO care_providers (id, name, slug, status)
            VALUES ('1-TEST', 'Migration test provider', 'migration-test-provider', 'ACTIVE')
            """
        )
        await conn.execute(
            """
            INSERT INTO trusted_event_ledger (
              entity_type, entity_id, event_type, effective_date, source,
              dedupe_key, source_snapshot_id
            ) VALUES ('location', '1-TEST', 'new_registration', CURRENT_DATE,
                      'migration-test', 'migration-test-event', $1)
            """,
            duplicate_id,
        )
        await conn.execute(
            """
            INSERT INTO cqc_location_index_entries (
              location_id, first_seen_at, last_seen_at, last_snapshot_id
            ) VALUES ('1-TEST', NOW(), NOW(), $1)
            """,
            duplicate_id,
        )
        await conn.execute(
            """
            INSERT INTO report_documents (
              cqc_location_id, source_snapshot_id, source_url, blob_uri, sha256
            ) VALUES ('1-TEST', $1, 'https://example.test/report',
                      's3://example.test/report', $2)
            """,
            duplicate_id,
            "b" * 64,
        )

        migration = (
            Path(__file__).resolve().parents[2]
            / "db/migrations/050_source_snapshot_identity.sql"
        ).read_text(encoding="utf-8")
        await conn.execute(migration)

        assert await unique_index_exists(
            conn,
            "source_snapshots",
            ("source_type", "checksum_sha256"),
        )
        assert await conn.fetchval(
            "SELECT COUNT(*) FROM source_snapshots "
            "WHERE source_type = 'cqc_location_index' AND checksum_sha256 = $1",
            checksum,
        ) == 1
        assert await conn.fetchval(
            "SELECT source_snapshot_id FROM trusted_event_ledger "
            "WHERE dedupe_key = 'migration-test-event'"
        ) == canonical_id
        assert await conn.fetchval(
            "SELECT last_snapshot_id FROM cqc_location_index_entries "
            "WHERE location_id = '1-TEST'"
        ) == canonical_id
        assert await conn.fetchval(
            "SELECT source_snapshot_id FROM report_documents WHERE cqc_location_id = '1-TEST'"
        ) == canonical_id

        upserted_id = await conn.fetchval(
            """
            INSERT INTO source_snapshots (
              source_type, source_uri, source_checked_at, checksum_sha256, record_count
            ) VALUES ('cqc_location_index', 'https://example.test/upsert', NOW(), $1, 10)
            ON CONFLICT (source_type, checksum_sha256)
            DO UPDATE SET source_checked_at = EXCLUDED.source_checked_at
            RETURNING id
            """,
            checksum,
        )
        assert upserted_id == canonical_id
    finally:
        await conn.close()
