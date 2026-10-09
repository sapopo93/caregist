"""Real-Postgres ordering tests for historical full-dataset webhook replay."""

from __future__ import annotations

import asyncio

import pytest

from api.routers import billing
from api.utils import email_queue
from tests.integration.conftest import apply_full_schema, asyncpg


PRICE = "price_dataset_refund_test"
SESSION_ID = "cs_dataset_refund_test"
PAYMENT_INTENT = "pi_dataset_refund_test"
TERMS_VERSION = "dataset-refund-test-1"
TERMS_SHA = "a" * 64


def _configure(monkeypatch) -> None:
    monkeypatch.setattr(billing.settings, "stripe_price_full_dataset", PRICE)
    monkeypatch.setattr(billing.settings, "digital_content_terms_version", TERMS_VERSION)
    monkeypatch.setattr(billing.settings, "digital_content_terms_sha256", TERMS_SHA)
    monkeypatch.setattr(billing.settings, "app_url", "https://itest.local")
    monkeypatch.setattr(
        billing,
        "_new_dataset_download_token",
        lambda: ("synthetic-dataset-token", "d" * 64),
    )


async def _seed_order(conn) -> tuple[str, str]:
    artifact_id = str(
        await conn.fetchval(
            """
            INSERT INTO full_dataset_artifacts (
              blob_pathname, record_count, sha256, source_watermark,
              ogl_attribution, is_active
            ) VALUES (
              'datasets/refund-test.csv', 1, $1, NOW(),
              'Open Government Licence v3.0', TRUE
            ) RETURNING id
            """,
            "b" * 64,
        )
    )
    order_id = str(
        await conn.fetchval(
            """
            INSERT INTO full_dataset_orders (
              artifact_id, stripe_checkout_session_id, customer_email, stripe_price_id
            ) VALUES ($1, $2, 'buyer@example.com', $3)
            RETURNING id
            """,
            artifact_id,
            SESSION_ID,
            PRICE,
        )
    )
    return order_id, artifact_id


def _authoritative(order_id: str, artifact_id: str, *, payment_intent=PAYMENT_INTENT):
    terms_version, terms_sha, consent_sha = billing._dataset_terms()
    return {
        "id": SESSION_ID,
        "metadata": {
            "type": "full_dataset",
            "order_id": order_id,
            "artifact_id": artifact_id,
            "price_id": PRICE,
            "terms_version": terms_version,
            "terms_sha256": terms_sha,
            "consent_text_sha256": consent_sha,
        },
        "payment_status": "paid",
        "consent": {"terms_of_service": "accepted"},
        "line_items": {"data": [{"price": {"id": PRICE}, "quantity": 1}]},
        "payment_intent": payment_intent,
        "amount_total": 19900,
        "currency": "gbp",
    }


def _mock_authoritative(monkeypatch, authoritative: dict) -> None:
    monkeypatch.setattr(
        billing.stripe.checkout.Session,
        "retrieve",
        lambda session_id, **_kwargs: authoritative
        if session_id == SESSION_ID
        else pytest.fail("unexpected Stripe session retrieval"),
    )


async def _refund(conn) -> None:
    await billing._handle_refund(
        conn,
        {
            "object": "charge",
            "id": "ch_dataset_refund_test",
            "amount": 19900,
            "amount_refunded": 19900,
            "refunded": True,
            "payment_intent": PAYMENT_INTENT,
        },
    )


async def _assert_no_grant(conn, order_id: str) -> None:
    row = await conn.fetchrow(
        """SELECT status, stripe_payment_intent_id, amount_total, currency
           FROM full_dataset_orders WHERE id = $1""",
        order_id,
    )
    assert tuple(row.values()) == ("pending", None, None, None)
    assert await conn.fetchval(
        "SELECT count(*) FROM digital_content_consents WHERE order_id = $1", order_id
    ) == 0
    assert await conn.fetchval(
        "SELECT count(*) FROM dataset_download_tokens WHERE order_id = $1", order_id
    ) == 0
    assert await conn.fetchval(
        "SELECT count(*) FROM pending_emails WHERE idempotency_key = $1",
        f"full-dataset-delivery:{order_id}",
    ) == 0


async def _consume_dataset_token(conn):
    return await conn.fetchrow(
        """
        WITH consumed AS (
          UPDATE dataset_download_tokens AS token
          SET download_count = token.download_count + 1,
              last_downloaded_at = NOW()
          FROM full_dataset_orders AS purchase
          WHERE token.token_hash = $1
            AND token.order_id = purchase.id
            AND token.expires_at > NOW()
            AND token.download_count < token.max_downloads
            AND purchase.status = 'paid'
          RETURNING purchase.artifact_id
        )
        SELECT artifact.blob_pathname
        FROM consumed
        JOIN full_dataset_artifacts AS artifact ON artifact.id = consumed.artifact_id
        LIMIT 1
        """,
        "d" * 64,
    )


async def test_refund_before_checkout_rejects_grant_without_tokens_or_email(
    fresh_db, monkeypatch
):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        _configure(monkeypatch)
        order_id, artifact_id = await _seed_order(conn)
        authoritative = _authoritative(order_id, artifact_id)
        _mock_authoritative(monkeypatch, authoritative)

        async with conn.transaction():
            await _refund(conn)

        with pytest.raises(RuntimeError, match="refunded full-dataset payment"):
            async with conn.transaction():
                await billing._handle_dataset_checkout_completed(
                    conn, {"id": SESSION_ID}
                )

        await _assert_no_grant(conn, order_id)
        assert await conn.fetchval(
            """SELECT count(*) FROM audit_log
               WHERE action = 'billing.charge.refund'
                 AND metadata->>'payment_intent' = $1
                 AND metadata->>'fully_refunded' = 'true'""",
            PAYMENT_INTENT,
        ) == 1
        assert await conn.fetchval(
            """SELECT count(*) FROM audit_log
               WHERE action = 'billing.full_dataset.fulfil'"""
        ) == 0
    finally:
        await conn.close()


async def test_invalid_authoritative_payment_intent_rejects_before_lock_or_grant(
    fresh_db, monkeypatch
):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        _configure(monkeypatch)
        order_id, artifact_id = await _seed_order(conn)
        _mock_authoritative(
            monkeypatch,
            _authoritative(order_id, artifact_id, payment_intent="ch_not_a_payment_intent"),
        )

        with pytest.raises(RuntimeError, match="valid authoritative payment intent"):
            async with conn.transaction():
                await billing._handle_dataset_checkout_completed(
                    conn, {"id": SESSION_ID}
                )

        await _assert_no_grant(conn, order_id)
    finally:
        await conn.close()


async def test_refund_lock_blocks_checkout_until_commit_then_checkout_rejects(
    fresh_db, monkeypatch
):
    setup = await asyncpg.connect(fresh_db)
    refund_conn = await asyncpg.connect(fresh_db)
    checkout_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(setup)
        _configure(monkeypatch)
        order_id, artifact_id = await _seed_order(setup)
        _mock_authoritative(monkeypatch, _authoritative(order_id, artifact_id))

        refund_tx = refund_conn.transaction()
        await refund_tx.start()
        await _refund(refund_conn)

        async def checkout_attempt():
            async with checkout_conn.transaction():
                await billing._handle_dataset_checkout_completed(
                    checkout_conn, {"id": SESSION_ID}
                )

        checkout_task = asyncio.create_task(checkout_attempt())
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(checkout_task), timeout=0.2)

        await refund_tx.commit()
        with pytest.raises(RuntimeError, match="refunded full-dataset payment"):
            await asyncio.wait_for(checkout_task, timeout=2)

        await _assert_no_grant(setup, order_id)
    finally:
        await setup.close()
        await refund_conn.close()
        await checkout_conn.close()


async def test_checkout_lock_wins_then_refund_revokes_and_delivery_stays_gated(
    fresh_db, monkeypatch
):
    setup = await asyncpg.connect(fresh_db)
    checkout_conn = await asyncpg.connect(fresh_db)
    refund_conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(setup)
        _configure(monkeypatch)
        monkeypatch.setattr(email_queue.settings, "outbound_communications_enabled", False)
        order_id, artifact_id = await _seed_order(setup)
        _mock_authoritative(monkeypatch, _authoritative(order_id, artifact_id))

        checkout_tx = checkout_conn.transaction()
        await checkout_tx.start()
        await billing._handle_dataset_checkout_completed(
            checkout_conn, {"id": SESSION_ID}
        )

        async def refund_attempt():
            async with refund_conn.transaction():
                await _refund(refund_conn)

        refund_task = asyncio.create_task(refund_attempt())
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(refund_task), timeout=0.2)

        await checkout_tx.commit()
        await asyncio.wait_for(refund_task, timeout=2)

        assert await setup.fetchval(
            "SELECT status FROM full_dataset_orders WHERE id = $1", order_id
        ) == "refunded"
        assert await setup.fetchval(
            """SELECT count(*) FROM dataset_download_tokens
               WHERE order_id = $1 AND expires_at > NOW()""",
            order_id,
        ) == 0
        assert await _consume_dataset_token(setup) is None
        assert await setup.fetchval(
            "SELECT count(*) FROM pending_emails WHERE idempotency_key = $1",
            f"full-dataset-delivery:{order_id}",
        ) == 1
        assert await email_queue._claim_pending_emails(setup, 10) == []
    finally:
        await setup.close()
        await checkout_conn.close()
        await refund_conn.close()


@pytest.mark.parametrize("conflict", ["payment", "consent"])
async def test_conflicting_durable_evidence_rejects_before_dataset_grant(
    fresh_db, monkeypatch, conflict
):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        _configure(monkeypatch)
        order_id, artifact_id = await _seed_order(conn)
        authoritative = _authoritative(order_id, artifact_id)
        _mock_authoritative(monkeypatch, authoritative)
        if conflict == "payment":
            await conn.execute(
                """UPDATE full_dataset_orders
                   SET stripe_payment_intent_id = 'pi_conflicting',
                       amount_total = 19900, currency = 'gbp'
                   WHERE id = $1""",
                order_id,
            )
            message = "durable payment evidence"
        else:
            await conn.execute(
                """
                INSERT INTO digital_content_consents (
                  order_id, stripe_checkout_session_id, terms_version, terms_sha256,
                  consent_text_sha256, immediate_supply_consented,
                  cancellation_right_acknowledged, accepted_at, evidence_source
                ) VALUES ($1, $2, 'conflicting-terms', $3, $4, TRUE, TRUE, NOW(),
                          'stripe_checkout_terms_checkbox')
                """,
                order_id,
                SESSION_ID,
                TERMS_SHA,
                billing._dataset_terms()[2],
            )
            message = "durable consent evidence"

        with pytest.raises(RuntimeError, match=message):
            async with conn.transaction():
                await billing._handle_dataset_checkout_completed(
                    conn, {"id": SESSION_ID}
                )

        assert await conn.fetchval(
            "SELECT status FROM full_dataset_orders WHERE id = $1", order_id
        ) == "pending"
        assert await conn.fetchval(
            "SELECT count(*) FROM dataset_download_tokens WHERE order_id = $1", order_id
        ) == 0
        assert await conn.fetchval(
            "SELECT count(*) FROM pending_emails WHERE idempotency_key = $1",
            f"full-dataset-delivery:{order_id}",
        ) == 0
    finally:
        await conn.close()
