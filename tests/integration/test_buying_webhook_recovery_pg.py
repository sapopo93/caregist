"""Real-Postgres refund webhook recovery tests; all Stripe data is synthetic."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from starlette.requests import Request

from api.routers import billing
from tests.integration.conftest import apply_full_schema, asyncpg
from tests.integration.test_acceptance_territory_download_pg import _consume, _order, _token


def _request(body: bytes = b'{"synthetic":true}') -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/billing/webhook",
            "headers": [(b"stripe-signature", b"test-signature")],
            "query_string": b"",
        },
        receive,
    )


def _patch_webhook(monkeypatch, conn, event):
    constructed = []

    @asynccontextmanager
    async def connection():
        yield conn

    def construct_event(payload, signature, secret):
        constructed.append((payload, signature, secret))
        return event

    monkeypatch.setattr(billing.settings, "stripe_secret_key", "sk_test_refund")
    monkeypatch.setattr(billing.settings, "stripe_webhook_secret", "whsec_test_refund")
    monkeypatch.setattr(billing, "get_connection", connection)
    monkeypatch.setattr(billing.stripe.Webhook, "construct_event", construct_event)
    return constructed


async def _brief_with_token(conn, *, payment_intent: str, token: str):
    order_id = await _order(conn, status="fulfilled")
    await conn.execute(
        "UPDATE territory_brief_orders SET stripe_payment_intent_id = $1 WHERE id = $2",
        payment_intent,
        order_id,
    )
    await _token(conn, order_id, "pdf", token)
    return order_id


async def test_full_refund_webhook_replay_is_deduplicated_and_revokes_token(
    fresh_db, monkeypatch
):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        token = "W" * 43
        order_id = await _brief_with_token(
            conn, payment_intent="pi_webhook_replay", token=token
        )
        assert await _consume(conn, token) is not None
        event = {
            "id": "evt_refund_replay",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "object": "charge",
                    "id": "ch_refund_replay",
                    "amount": 74500,
                    "amount_refunded": 74500,
                    "refunded": True,
                    "payment_intent": "pi_webhook_replay",
                }
            },
        }
        constructed = _patch_webhook(monkeypatch, conn, event)

        assert await billing.stripe_webhook(_request()) == {"status": "ok"}
        assert await billing.stripe_webhook(_request()) == {"status": "ok"}

        assert len(constructed) == 2
        assert all(
            call == (b'{"synthetic":true}', "test-signature", "whsec_test_refund")
            for call in constructed
        )
        assert await conn.fetchval(
            "SELECT status FROM territory_brief_orders WHERE id = $1", order_id
        ) == "refunded"
        assert await _consume(conn, token) is None
        assert await conn.fetchval(
            "SELECT count(*) FROM stripe_processed_events WHERE event_id = $1",
            event["id"],
        ) == 1
        assert await conn.fetchval(
            """SELECT count(*) FROM audit_log
               WHERE action = 'billing.charge.refund' AND target_id = $1""",
            "ch_refund_replay",
        ) == 1
    finally:
        await conn.close()


async def test_refund_object_webhook_retrieves_authoritative_charge(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        token = "A" * 43
        order_id = await _brief_with_token(
            conn, payment_intent="pi_authoritative", token=token
        )
        event = {
            "id": "evt_refund_object",
            "type": "charge.refund.updated",
            "data": {
                "object": {
                    "object": "refund",
                    "id": "re_refund_object",
                    "charge": "ch_authoritative",
                    "amount": 1,
                }
            },
        }
        _patch_webhook(monkeypatch, conn, event)
        retrieved = []

        def retrieve(charge_id):
            retrieved.append(charge_id)
            return {
                "object": "charge",
                "id": charge_id,
                "amount": 74500,
                "amount_refunded": 74500,
                "refunded": True,
                "payment_intent": "pi_authoritative",
            }

        monkeypatch.setattr(billing.stripe.Charge, "retrieve", retrieve)

        assert await billing.stripe_webhook(_request()) == {"status": "ok"}

        assert retrieved == ["ch_authoritative"]
        assert await conn.fetchval(
            "SELECT status FROM territory_brief_orders WHERE id = $1", order_id
        ) == "refunded"
        assert await _consume(conn, token) is None
        audit = await conn.fetchrow(
            """SELECT target_id,
                      metadata->>'payment_intent' AS payment_intent,
                      (metadata->>'fully_refunded')::boolean AS fully_refunded
               FROM audit_log
               WHERE action = 'billing.charge.refund'"""
        )
        assert audit["target_id"] == "ch_authoritative"
        assert audit["payment_intent"] == "pi_authoritative"
        assert audit["fully_refunded"] is True
    finally:
        await conn.close()


async def test_strict_refund_audit_failure_rolls_back_then_retry_succeeds(
    fresh_db, monkeypatch
):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        token = "F" * 43
        order_id = await _brief_with_token(
            conn, payment_intent="pi_audit_retry", token=token
        )
        event = {
            "id": "evt_audit_retry",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "object": "charge",
                    "id": "ch_audit_retry",
                    "amount": 74500,
                    "amount_refunded": 74500,
                    "refunded": True,
                    "payment_intent": "pi_audit_retry",
                }
            },
        }
        _patch_webhook(monkeypatch, conn, event)
        real_write_audit_log = billing.write_audit_log
        attempts = 0

        async def fail_once(**kwargs):
            nonlocal attempts
            attempts += 1
            assert kwargs["strict"] is True
            assert kwargs["conn"] is conn
            if attempts == 1:
                raise RuntimeError("synthetic strict audit failure")
            await real_write_audit_log(**kwargs)

        monkeypatch.setattr(billing, "write_audit_log", fail_once)

        with pytest.raises(RuntimeError, match="synthetic strict audit failure"):
            await billing.stripe_webhook(_request())

        assert await conn.fetchval(
            "SELECT count(*) FROM stripe_processed_events WHERE event_id = $1",
            event["id"],
        ) == 0
        assert await conn.fetchval(
            "SELECT status FROM territory_brief_orders WHERE id = $1", order_id
        ) == "fulfilled"
        assert await conn.fetchval(
            """SELECT expires_at > NOW() FROM territory_brief_download_tokens
               WHERE order_id = $1""",
            order_id,
        ) is True
        assert await conn.fetchval(
            "SELECT count(*) FROM audit_log WHERE target_id = $1", "ch_audit_retry"
        ) == 0

        assert await billing.stripe_webhook(_request()) == {"status": "ok"}

        assert attempts == 2
        assert await conn.fetchval(
            "SELECT count(*) FROM stripe_processed_events WHERE event_id = $1",
            event["id"],
        ) == 1
        assert await conn.fetchval(
            "SELECT status FROM territory_brief_orders WHERE id = $1", order_id
        ) == "refunded"
        assert await _consume(conn, token) is None
        assert await conn.fetchval(
            """SELECT count(*) FROM audit_log
               WHERE action = 'billing.charge.refund' AND target_id = $1""",
            "ch_audit_retry",
        ) == 1
    finally:
        await conn.close()
