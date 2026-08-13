"""Real-Postgres verification of the CRM security and retention boundaries."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tests.integration.conftest import apply_full_schema, validate_test_database_url

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_054 = ROOT / "db/migrations/054_crm_completion_controls.sql"
DOWN_054 = ROOT / "db/migrations/down/054_crm_completion_controls.down.sql"


async def _seed_two_tenants(conn):
    user_one = await conn.fetchval(
        "INSERT INTO users (email, password_hash, name, is_verified) "
        "VALUES ('crm-one@example.test', 'x', 'CRM One', true) RETURNING id"
    )
    user_two = await conn.fetchval(
        "INSERT INTO users (email, password_hash, name, is_verified) "
        "VALUES ('crm-two@example.test', 'x', 'CRM Two', true) RETURNING id"
    )
    organization_one = await conn.fetchval(
        "INSERT INTO organizations (name, slug, created_by_user_id) "
        "VALUES ('CRM One', 'crm-one', $1) RETURNING id",
        user_one,
    )
    organization_two = await conn.fetchval(
        "INSERT INTO organizations (name, slug, created_by_user_id) "
        "VALUES ('CRM Two', 'crm-two', $1) RETURNING id",
        user_two,
    )
    await conn.executemany(
        "INSERT INTO organization_members (organization_id, user_id, role) "
        "VALUES ($1, $2, 'owner')",
        [(organization_one, user_one), (organization_two, user_two)],
    )

    contacts = []
    for organization_id, user_id, email in (
        (organization_one, user_one, "contact-one@example.test"),
        (organization_two, user_two, "contact-two@example.test"),
    ):
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(user_id))
            contacts.append(
                await conn.fetchval(
                    "INSERT INTO crm_contacts "
                    "(organization_id, created_by_user_id, email) VALUES ($1, $2, $3) RETURNING id",
                    organization_id,
                    user_id,
                    email,
                )
            )
    return user_one, user_two, organization_one, organization_two, contacts[0], contacts[1]


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "postgresql://user:password@db.example.test/postgres",
        "postgresql://user:password@127.0.0.1/caregist",
        "postgresql://user:password@localhost/production",
    ],
)
async def test_integration_database_url_rejects_nonisolated_targets(unsafe_url):
    with pytest.raises(RuntimeError):
        validate_test_database_url(unsafe_url)


async def test_migration_054_rolls_back_and_reapplies_cleanly(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        assert await conn.fetchval(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'crm_contacts'"
        )

        async with conn.transaction():
            await conn.execute(DOWN_054.read_text(encoding="utf-8"))
        assert not await conn.fetchval(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'crm_contacts'"
        )
        assert not await conn.fetchval("SELECT to_regclass('public.crm_companies') IS NOT NULL")
        assert not await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_deals_contact_tenant')"
        )

        async with conn.transaction():
            await conn.execute(MIGRATION_054.read_text(encoding="utf-8"))
        assert await conn.fetchval(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'crm_contacts'"
        )
        assert await conn.fetchval("SELECT to_regclass('public.crm_companies') IS NOT NULL")
        assert await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_crm_deals_contact_tenant')"
        )
    finally:
        await conn.close()


async def test_crm_health_worker_sees_forced_rls_operational_rows(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_one, _, organization_one, _, contact_one, _ = await _seed_two_tenants(conn)
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(user_one))
            call_id = await conn.fetchval(
                "INSERT INTO crm_call_sessions (organization_id, contact_id, agent_user_id, "
                "authorization_token_hash, authorization_expires_at, status) "
                "VALUES ($1, $2, $3, $4, NOW(), 'completed') RETURNING id",
                organization_one, contact_one, user_one, "c" * 64,
            )
            await conn.execute(
                "INSERT INTO crm_recordings (organization_id, call_session_id, twilio_recording_sid, "
                "object_key, status, expires_at) "
                "VALUES ($1, $2, $3, 'expired-health.mp3', 'error', NOW() - INTERVAL '1 minute')",
                organization_one, call_id, "RE" + "c" * 32,
            )
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_health', true)")
            assert await conn.fetchval(
                "SELECT COUNT(*) FROM crm_recordings "
                "WHERE expires_at <= NOW() AND status <> 'deleted'"
            ) == 1
    finally:
        await conn.close()


async def test_forced_rls_worker_visibility_tenant_fk_and_agent_lock(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    contender = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_one, _, organization_one, organization_two, _, contact_two = await _seed_two_tenants(conn)

        owner = await conn.fetchrow(
            """
            SELECT current_user = role.rolname AS connection_owns_table,
                   role.rolsuper, role.rolbypassrls, table_class.relforcerowsecurity
            FROM pg_class table_class
            JOIN pg_roles role ON role.oid = table_class.relowner
            WHERE table_class.relname = 'crm_contacts'
            """
        )
        assert dict(owner) == {
            "connection_owns_table": True,
            "rolsuper": False,
            "rolbypassrls": False,
            "relforcerowsecurity": True,
        }

        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(user_one))
            visible = await conn.fetch("SELECT organization_id FROM crm_contacts ORDER BY organization_id")
            assert [row["organization_id"] for row in visible] == [organization_one]

        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'twilio', true)")
            assert await conn.fetchval("SELECT COUNT(*) FROM crm_contacts") == 2

        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_retention', true)")
            assert await conn.fetchval("SELECT COUNT(*) FROM crm_contacts") == 0

        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(user_one))
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                await conn.execute(
                    "INSERT INTO crm_deals (organization_id, contact_id, title) VALUES ($1, $2, 'Cross tenant')",
                    organization_one,
                    contact_two,
                )

        first_tx = conn.transaction()
        second_tx = contender.transaction()
        await first_tx.start()
        await second_tx.start()
        try:
            await conn.execute("SELECT pg_advisory_xact_lock($1, $2)", user_one, 0x43524D)
            assert not await contender.fetchval(
                "SELECT pg_try_advisory_xact_lock($1, $2)", user_one, 0x43524D
            )
        finally:
            await second_tx.rollback()
            await first_tx.rollback()
    finally:
        await contender.close()
        await conn.close()


async def test_retention_purges_only_expired_data_and_writes_audit(fresh_db, monkeypatch):
    from api import database
    from api.services import crm_retention

    conn = await asyncpg.connect(fresh_db)
    pool = None
    previous_pool = database._pool
    try:
        await apply_full_schema(conn)
        user_one, _, organization_one, _, contact_one, _ = await _seed_two_tenants(conn)
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(user_one))
            expired_call = await conn.fetchval(
                "INSERT INTO crm_call_sessions "
                "(organization_id, contact_id, agent_user_id, authorization_token_hash, "
                " authorization_expires_at, status) "
                "VALUES ($1, $2, $3, $4, NOW() - INTERVAL '31 days', 'completed') RETURNING id",
                organization_one,
                contact_one,
                user_one,
                "a" * 64,
            )
            future_call = await conn.fetchval(
                "INSERT INTO crm_call_sessions "
                "(organization_id, contact_id, agent_user_id, authorization_token_hash, "
                " authorization_expires_at, status) "
                "VALUES ($1, $2, $3, $4, NOW() + INTERVAL '1 day', 'completed') RETURNING id",
                organization_one,
                contact_one,
                user_one,
                "b" * 64,
            )
            expired_recording = await conn.fetchval(
                "INSERT INTO crm_recordings "
                "(organization_id, call_session_id, twilio_recording_sid, object_key, status, expires_at) "
                "VALUES ($1, $2, $3, 'expired.mp3', 'ready', NOW() - INTERVAL '1 second') RETURNING id",
                organization_one,
                expired_call,
                "RE" + "a" * 32,
            )
            future_recording = await conn.fetchval(
                "INSERT INTO crm_recordings "
                "(organization_id, call_session_id, twilio_recording_sid, object_key, status, expires_at) "
                "VALUES ($1, $2, $3, 'future.mp3', 'ready', NOW() + INTERVAL '1 day') RETURNING id",
                organization_one,
                future_call,
                "RE" + "b" * 32,
            )
            await conn.execute(
                "INSERT INTO crm_call_intelligence "
                "(organization_id, call_session_id, recording_id, status, transcript, summary, "
                " evaluation, reserved_cost_usd) "
                "VALUES ($1, $2, $3, 'failed', 'private transcript', 'summary', '{}'::jsonb, 0.25)",
                organization_one,
                expired_call,
                expired_recording,
            )

        deleted_objects = []

        async def delete_object(key):
            deleted_objects.append(key)

        async def delete_source(_sid):
            return True

        monkeypatch.setattr(crm_retention, "delete_recording_object", delete_object)
        monkeypatch.setattr(crm_retention, "delete_twilio_source", delete_source)
        pool = await asyncpg.create_pool(fresh_db, min_size=1, max_size=2)
        database._pool = pool

        result = await crm_retention.purge_expired_recordings(limit=50)
        assert result == {"deleted": 1, "failed": 0, "sources_deleted": 1}
        assert deleted_objects == ["expired.mp3"]

        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(user_one))
            expired = await conn.fetchrow(
                "SELECT status, deleted_at FROM crm_recordings WHERE id = $1", expired_recording
            )
            future = await conn.fetchrow(
                "SELECT status, deleted_at FROM crm_recordings WHERE id = $1", future_recording
            )
            intelligence = await conn.fetchrow(
                "SELECT status, transcript, summary, evaluation, reserved_cost_usd, processed_at "
                "FROM crm_call_intelligence "
                "WHERE recording_id = $1",
                expired_recording,
            )
        assert expired["status"] == "deleted" and expired["deleted_at"] is not None
        assert future["status"] == "ready" and future["deleted_at"] is None
        assert dict(intelligence) == {
            "status": "purged",
            "transcript": None,
            "summary": None,
            "evaluation": None,
            "reserved_cost_usd": Decimal("0.25000000"),
            "processed_at": intelligence["processed_at"],
        }
        assert intelligence["processed_at"] is not None
        assert await conn.fetchval(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE action = 'crm.recording.retention_delete' AND target_id = $1::uuid::text",
            expired_recording,
        ) == 1
    finally:
        database._pool = previous_pool
        if pool is not None:
            await pool.close()
        await conn.close()
