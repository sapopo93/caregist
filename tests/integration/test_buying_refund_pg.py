"""Buying audit: real SQL, synthetic refund events, no money movement."""
import pytest

from api.routers import billing
from tests.integration.conftest import apply_full_schema, asyncpg
from tests.integration.test_acceptance_territory_download_pg import _consume, _order, _token


@pytest.mark.parametrize("original_status", ["fulfilled", "failed"])
async def test_repeated_refund_handler_invocation_preserves_revoked_state(fresh_db, monkeypatch, original_status):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order = await _order(conn, status=original_status)
        await conn.execute("UPDATE territory_brief_orders SET stripe_payment_intent_id='pi_audit' WHERE id=$1", order)
        await _token(conn, order, "pdf", "R" * 43)
        event = {"id": "ch_audit", "amount": 74500, "amount_refunded": 20000, "refunded": False, "payment_intent": "pi_audit"}
        await billing._handle_refund(conn, event)
        assert await conn.fetchval("SELECT status FROM territory_brief_orders WHERE id=$1", order) == original_status
        event.update(amount_refunded=74500, refunded=True)
        await billing._handle_refund(conn, event)
        await billing._handle_refund(conn, event)
        assert await conn.fetchval("SELECT status FROM territory_brief_orders WHERE id=$1", order) == "refunded"
        assert await _consume(conn, "R" * 43) is None
        assert await conn.fetchval("SELECT count(*) FROM audit_log WHERE action='billing.charge.refund' AND target_id='ch_audit'") == 3
        assert await conn.fetchval("SELECT count(*) FROM audit_log WHERE target_id='ch_audit' AND metadata->>'amount_refunded_gbp'='745.0'") == 2
    finally:
        await conn.close()


async def test_observed_gap_refund_cannot_match_failed_order_without_payment_intent(fresh_db, monkeypatch):
    """Characterisation of a defect, NOT an acceptance pass for refund recovery.

    This represents a legacy row created before payment-context recovery was
    implemented. The repaired recorder's actual journey is tested separately.
    """
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order = await _order(conn, status="failed")
        await billing._handle_refund(conn, {"id": "ch_unmatched", "amount": 74500, "amount_refunded": 74500, "refunded": True, "payment_intent": "pi_unmatched"})
        assert await conn.fetchval("SELECT status FROM territory_brief_orders WHERE id=$1", order) == "failed"
        assert await conn.fetchval("SELECT count(*) FROM audit_log WHERE target_id='ch_unmatched' AND metadata->>'fully_refunded'='true'") == 1
    finally:
        await conn.close()


async def test_refund_audit_failure_rolls_back_revocation_and_event_marker(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order = await _order(conn)
        await conn.execute("UPDATE territory_brief_orders SET stripe_payment_intent_id='pi_audit_fail' WHERE id=$1", order)
        with pytest.raises(asyncpg.UndefinedTableError):
            async with conn.transaction():
                await conn.execute("INSERT INTO stripe_processed_events (event_id) VALUES ('evt_audit_fail')")
                await conn.execute("DROP TABLE audit_log")
                await billing._handle_refund(conn, {"id": "ch_audit_fail", "amount": 74500, "amount_refunded": 74500, "refunded": True, "payment_intent": "pi_audit_fail"})
        assert await conn.fetchval("SELECT status FROM territory_brief_orders WHERE id=$1", order) == "fulfilled"
        assert await conn.fetchval("SELECT count(*) FROM stripe_processed_events WHERE event_id='evt_audit_fail'") == 0
    finally:
        await conn.close()
