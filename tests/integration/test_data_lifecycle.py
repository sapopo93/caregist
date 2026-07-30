"""Integration tests for the data-lifecycle features (F-28, F-44).

Exercises the dead-letter helpers, the pending_emails size CHECK, and the
retention pruning tool against a real Postgres schema.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio


async def test_dead_letter_counts_only_old_failed_emails(fresh_db):
    from api.utils.email_queue import count_dead_letter_emails, get_dead_letter_emails

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute(
            """
            INSERT INTO pending_emails (to_email, subject, html_body, status, created_at)
            VALUES
              ('old@f.com', 's', '<p>x</p>', 'failed', NOW() - INTERVAL '48 hours'),
              ('recent@f.com', 's', '<p>x</p>', 'failed', NOW() - INTERVAL '2 hours'),
              ('done@f.com', 's', '<p>x</p>', 'sent', NOW() - INTERVAL '48 hours')
            """
        )
        assert await count_dead_letter_emails(conn, older_than_hours=24) == 1
        rows = await get_dead_letter_emails(conn, older_than_hours=24)
        assert [r["to_email"] for r in rows] == ["old@f.com"]
    finally:
        await conn.close()


async def test_pending_emails_size_check_enforced(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                "INSERT INTO pending_emails (to_email, subject, html_body, status) "
                "VALUES ('big@f.com', 's', $1, 'pending')",
                "a" * 1_000_001,
            )
    finally:
        await conn.close()


async def test_retention_prune_deletes_only_old_rows(fresh_db):
    from tools.prune_retention import prune

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute(
            "INSERT INTO analytics_events (event_type, created_at) "
            "VALUES ('old', NOW() - INTERVAL '120 days'), ('fresh', NOW())"
        )
        await conn.execute(
            """
            INSERT INTO pending_emails (to_email, subject, html_body, status, created_at)
            VALUES ('old@f.com', 's', '<p>x</p>', 'sent', NOW() - INTERVAL '40 days'),
                   ('keep@f.com', 's', '<p>x</p>', 'failed', NOW() - INTERVAL '40 days')
            """
        )

        results = await prune(conn, audit_days=730, dry_run=False)
        assert results["analytics_events"] == 1
        assert results["pending_emails"] == 1  # only the old *sent* row

        assert await conn.fetchval("SELECT COUNT(*) FROM analytics_events") == 1
        # The old failed email is retained for the dead-letter workflow.
        assert await conn.fetchval(
            "SELECT COUNT(*) FROM pending_emails WHERE status = 'failed'"
        ) == 1
    finally:
        await conn.close()


async def test_legacy_claim_proof_is_removed_and_unverified_activation_suspended(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute(
            """
            INSERT INTO care_providers (id, name, slug, status, is_claimed, claimed_at)
            VALUES ('LEGACY1', 'Legacy Provider', 'legacy-provider', 'ACTIVE', TRUE, NOW());

            INSERT INTO provider_claims (
              provider_id, status, claimant_name, claimant_email, proof_of_association
            ) VALUES (
              'LEGACY1', 'approved', 'Legacy Claimant', 'legacy@example.com',
              'raw document and authority details'
            );
            """
        )

        migration = (
            Path(__file__).resolve().parents[2] / "db/migrations/042_claim_evidence_minimisation.sql"
        ).read_text(encoding="utf-8")
        await conn.execute(migration)

        claim = await conn.fetchrow(
            "SELECT status, proof_of_association, decision_reason_code FROM provider_claims WHERE provider_id = 'LEGACY1'"
        )
        assert claim["status"] == "suspended"
        assert claim["proof_of_association"] == "[legacy evidence removed; reverification required]"
        assert claim["decision_reason_code"] == "reverification_required"
        assert await conn.fetchval("SELECT is_claimed FROM care_providers WHERE id = 'LEGACY1'") is False
    finally:
        await conn.close()
