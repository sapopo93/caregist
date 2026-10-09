"""Real-Postgres recovery tests for failed paid Brief generation.

Stripe, Blob storage, generation output and outbound sending are injected. The
transaction rollback, durable failure recorder, refund handler and checkout
replay use the real schema and SQL.
"""

from contextlib import asynccontextmanager

import pytest

from api.routers import billing
from api.services import territory_brief_delivery as delivery
from api.services import territory_brief_fulfilment as fulfil
from tests.integration.conftest import apply_full_schema, asyncpg


TERMS_SHA = "a" * 64
CONSENT_SHA = "b" * 64
PRICE = "price_generation_recovery"


def _cfg() -> fulfil.FulfilmentSettings:
    return fulfil.FulfilmentSettings(
        stripe_price_territory_brief=PRICE,
        terms_version="recovery-test-1",
        terms_sha256=TERMS_SHA,
        consent_sha256=CONSENT_SHA,
        app_url="https://itest.local",
    )


def _authoritative(order_id: str) -> dict:
    cfg = _cfg()
    scope = {
        "kind": "local_authority",
        "name": "Southampton",
        "window_days": 90,
        "shortlist_target": 30,
    }
    return {
        "id": "cs_generation_recovery",
        "metadata": fulfil.build_checkout_metadata(order_id, scope, cfg),
        "payment_status": "paid",
        "consent": {"terms_of_service": "accepted"},
        "line_items": {"data": [{"price": {"id": PRICE}, "quantity": 1}]},
        "payment_intent": "pi_generation_recovery",
        "amount_total": 74500,
        "currency": "gbp",
    }


async def _seed_order(conn) -> str:
    return str(
        await conn.fetchval(
            """
        INSERT INTO territory_brief_orders (
          stripe_checkout_session_id, customer_email, stripe_price_id,
          scope_kind, scope_name, scope_window_days, scope_shortlist_target
        ) VALUES (
          'cs_generation_recovery', 'buyer@example.com', $1,
          'local_authority', 'Southampton', 90, 30
        ) RETURNING id
        """,
            PRICE,
        )
    )


def _deps(authoritative: dict, generated: list[str]) -> fulfil.FulfilmentDeps:
    def fail_generation(_order):
        generated.append("attempted")
        raise RuntimeError("synthetic generator failure")

    def no_upload(*_args):  # pragma: no cover - generation always fails first
        raise AssertionError("storage must not be called")

    async def no_audit(**_kwargs):  # pragma: no cover - fulfil audit is unreachable
        raise AssertionError("fulfil audit must not be called")

    return fulfil.FulfilmentDeps(
        generate=fail_generation,
        upload=no_upload,
        retrieve_session=lambda _session_id: authoritative,
        record_failure=delivery._record_failure,
        write_audit_log=no_audit,
    )


def _successful_deps(
    authoritative: dict,
    generated: list[str],
    uploads: list[str] | None = None,
) -> fulfil.FulfilmentDeps:
    uploads = uploads if uploads is not None else []

    def generate(order):
        generated.append("attempted")
        return fulfil.GeneratedPack(
            pdf_bytes=b"%PDF-1.4 synthetic",
            csv_text="rank,organisation\n1,Synthetic Care\n",
            scope_name=order["scope_name"],
            considered=1,
            shortlisted=1,
        )

    def upload(order_id, kind, _data, _content_type):
        uploads.append(kind)
        return fulfil.BlobRef(pathname=f"territory-briefs/{order_id}/synthetic/brief.{kind}")

    async def audit(**_kwargs):
        return None

    return fulfil.FulfilmentDeps(
        generate=generate,
        upload=upload,
        retrieve_session=lambda _session_id: authoritative,
        record_failure=delivery._record_failure,
        write_audit_log=audit,
    )


class _FailFulfilledWrite:
    """Delegate real SQL except the first write after both uploads."""

    def __init__(self, conn):
        self._conn = conn

    async def execute(self, sql, *args):
        if "SET status = 'fulfilled'" in sql:
            raise RuntimeError("synthetic post-upload database failure")
        return await self._conn.execute(sql, *args)

    async def fetchrow(self, sql, *args):
        return await self._conn.fetchrow(sql, *args)

    async def fetchval(self, sql, *args):
        return await self._conn.fetchval(sql, *args)


@asynccontextmanager
async def _fresh_connection(database_url: str):
    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()


async def _fail_and_roll_back(conn, order_id: str, generated: list[str]):
    authoritative = _authoritative(order_id)
    tx = conn.transaction()
    await tx.start()
    try:
        with pytest.raises(fulfil.TerritoryBriefGenerationError) as caught:
            await fulfil.fulfil_territory_brief_order(
                conn,
                {"id": authoritative["id"]},
                cfg=_cfg(),
                deps=_deps(authoritative, generated),
            )
    finally:
        await tx.rollback()
    return caught.value, authoritative


async def _assert_no_delivery(conn, order_id: str) -> None:
    row = await conn.fetchrow("SELECT * FROM territory_brief_orders WHERE id = $1", order_id)
    assert row["blob_pdf_pathname"] is None
    assert row["blob_csv_pathname"] is None
    assert row["artifact_sha256"] is None
    assert await conn.fetchval("SELECT count(*) FROM territory_brief_download_tokens WHERE order_id = $1", order_id) == 0
    assert (
        await conn.fetchval(
            "SELECT count(*) FROM pending_emails WHERE idempotency_key = $1",
            f"territory-brief-delivery:{order_id}",
        )
        == 0
    )


async def _durable_state(conn, order_id: str) -> tuple:
    row = await conn.fetchrow(
        """
        SELECT status, stripe_payment_intent_id, amount_total, currency,
               blob_pdf_pathname, blob_csv_pathname, artifact_sha256,
               generation_attempts, last_error
        FROM territory_brief_orders
        WHERE id = $1
        """,
        order_id,
    )
    consent = await conn.fetchrow(
        """
        SELECT stripe_checkout_session_id, terms_version, terms_sha256,
               consent_text_sha256, immediate_supply_consented,
               cancellation_right_acknowledged, accepted_at, evidence_source
        FROM territory_brief_consents
        WHERE order_id = $1
        """,
        order_id,
    )
    return (
        tuple(row.values()),
        tuple(consent.values()) if consent else None,
        await conn.fetchval(
            "SELECT count(*) FROM territory_brief_download_tokens WHERE order_id = $1",
            order_id,
        ),
        await conn.fetchval(
            "SELECT count(*) FROM pending_emails WHERE idempotency_key = $1",
            f"territory-brief-delivery:{order_id}",
        ),
    )


async def test_conflicting_durable_payment_identity_rejects_replay_without_changes(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order_id = await _seed_order(conn)
        await conn.execute(
            """
            UPDATE territory_brief_orders
            SET status = 'failed', stripe_payment_intent_id = 'pi_original',
                amount_total = 74500, currency = 'gbp', generation_attempts = 1,
                last_error = 'original failure'
            WHERE id = $1
            """,
            order_id,
        )
        before = await _durable_state(conn, order_id)
        authoritative = _authoritative(order_id)
        authoritative["payment_intent"] = "pi_replacement"
        generated: list[str] = []

        with pytest.raises(fulfil.TerritoryBriefFulfilmentError, match="durable payment evidence"):
            async with conn.transaction():
                await fulfil.fulfil_territory_brief_order(
                    conn,
                    {"id": authoritative["id"]},
                    cfg=_cfg(),
                    deps=_successful_deps(authoritative, generated),
                )

        assert generated == []
        assert await _durable_state(conn, order_id) == before
        await _assert_no_delivery(conn, order_id)
    finally:
        await conn.close()


async def test_conflicting_durable_consent_rejects_before_generation_without_changes(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order_id = await _seed_order(conn)
        await conn.execute(
            """
            UPDATE territory_brief_orders
            SET status = 'failed', stripe_payment_intent_id = 'pi_generation_recovery',
                amount_total = 74500, currency = 'gbp', generation_attempts = 1,
                last_error = 'original failure'
            WHERE id = $1
            """,
            order_id,
        )
        await conn.execute(
            """
            INSERT INTO territory_brief_consents (
              order_id, stripe_checkout_session_id, terms_version, terms_sha256,
              consent_text_sha256, immediate_supply_consented,
              cancellation_right_acknowledged, accepted_at, evidence_source
            ) VALUES ($1, 'cs_generation_recovery', 'conflicting-terms', $2, $3,
                      TRUE, TRUE, NOW(), 'stripe_checkout_terms_checkbox')
            """,
            order_id,
            TERMS_SHA,
            CONSENT_SHA,
        )
        before = await _durable_state(conn, order_id)
        authoritative = _authoritative(order_id)
        generated: list[str] = []

        with pytest.raises(fulfil.TerritoryBriefFulfilmentError, match="durable consent evidence"):
            async with conn.transaction():
                await fulfil.fulfil_territory_brief_order(
                    conn,
                    {"id": authoritative["id"]},
                    cfg=_cfg(),
                    deps=_successful_deps(authoritative, generated),
                )

        assert generated == []
        assert await _durable_state(conn, order_id) == before
        await _assert_no_delivery(conn, order_id)
    finally:
        await conn.close()


async def test_generation_rollback_recorder_refund_and_checkout_replay_fail_closed(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order_id = await _seed_order(conn)
        generated: list[str] = []
        failure, authoritative = await _fail_and_roll_back(conn, order_id, generated)
        monkeypatch.setattr(
            "api.database.get_connection",
            lambda: _fresh_connection(fresh_db),
        )

        await failure.record_failure()
        recovered = await conn.fetchrow("SELECT * FROM territory_brief_orders WHERE id = $1", order_id)
        assert recovered["status"] == "failed"
        assert recovered["stripe_payment_intent_id"] == "pi_generation_recovery"
        assert recovered["amount_total"] == 74500
        assert recovered["currency"] == "gbp"
        assert recovered["paid_at"] is not None
        assert recovered["generation_attempts"] == 1
        assert await conn.fetchval("SELECT count(*) FROM territory_brief_consents WHERE order_id = $1", order_id) == 1

        # A retried failure write remains idempotent for evidence and cannot
        # drive the durable attempt counter beyond the generation cap.
        for _ in range(6):
            await failure.record_failure()
        assert await conn.fetchval("SELECT generation_attempts FROM territory_brief_orders WHERE id = $1", order_id) == 5
        assert await conn.fetchval("SELECT count(*) FROM territory_brief_consents WHERE order_id = $1", order_id) == 1

        async with conn.transaction():
            await billing._handle_refund(
                conn,
                {
                    "id": "ch_generation_recovery",
                    "amount": 74500,
                    "amount_refunded": 74500,
                    "refunded": True,
                    "payment_intent": "pi_generation_recovery",
                },
            )
        assert await conn.fetchval("SELECT status FROM territory_brief_orders WHERE id = $1", order_id) == "refunded"

        with pytest.raises(fulfil.TerritoryBriefFulfilmentError, match="refunded"):
            async with conn.transaction():
                await fulfil.fulfil_territory_brief_order(
                    conn,
                    {"id": authoritative["id"]},
                    cfg=_cfg(),
                    deps=_deps(authoritative, generated),
                )
        assert generated == ["attempted"]
        await _assert_no_delivery(conn, order_id)
    finally:
        await conn.close()


async def test_refund_audit_before_failure_recorder_sets_refunded_atomically(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order_id = await _seed_order(conn)
        generated: list[str] = []
        failure, authoritative = await _fail_and_roll_back(conn, order_id, generated)
        monkeypatch.setattr(
            "api.database.get_connection",
            lambda: _fresh_connection(fresh_db),
        )

        async with conn.transaction():
            await billing._handle_refund(
                conn,
                {
                    "id": "ch_refund_before_recorder",
                    "amount": 74500,
                    "amount_refunded": 74500,
                    "refunded": True,
                    "payment_intent": "pi_generation_recovery",
                },
            )
        assert await conn.fetchval("SELECT status FROM territory_brief_orders WHERE id = $1", order_id) == "pending"

        await failure.record_failure()
        row = await conn.fetchrow("SELECT * FROM territory_brief_orders WHERE id = $1", order_id)
        assert row["status"] == "refunded"
        assert row["stripe_payment_intent_id"] == "pi_generation_recovery"
        assert row["generation_attempts"] == 1
        assert await conn.fetchval("SELECT count(*) FROM territory_brief_consents WHERE order_id = $1", order_id) == 1

        with pytest.raises(fulfil.TerritoryBriefFulfilmentError, match="refunded"):
            async with conn.transaction():
                await fulfil.fulfil_territory_brief_order(
                    conn,
                    {"id": authoritative["id"]},
                    cfg=_cfg(),
                    deps=_deps(authoritative, generated),
                )
        assert generated == ["attempted"]
        await _assert_no_delivery(conn, order_id)
    finally:
        await conn.close()


async def test_post_upload_database_failure_recovers_evidence_then_refund_blocks_replay(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        order_id = await _seed_order(conn)
        authoritative = _authoritative(order_id)
        generated: list[str] = []
        uploads: list[str] = []
        tx = conn.transaction()
        await tx.start()
        try:
            with pytest.raises(fulfil.TerritoryBriefGenerationError) as caught:
                await fulfil.fulfil_territory_brief_order(
                    _FailFulfilledWrite(conn),
                    {"id": authoritative["id"]},
                    cfg=_cfg(),
                    deps=_successful_deps(authoritative, generated, uploads),
                )
        finally:
            await tx.rollback()

        assert generated == ["attempted"]
        assert uploads == ["pdf", "csv"]
        await _assert_no_delivery(conn, order_id)
        monkeypatch.setattr(
            "api.database.get_connection",
            lambda: _fresh_connection(fresh_db),
        )
        await caught.value.record_failure()

        recovered = await conn.fetchrow("SELECT * FROM territory_brief_orders WHERE id = $1", order_id)
        assert recovered["status"] == "failed"
        assert recovered["stripe_payment_intent_id"] == "pi_generation_recovery"
        assert recovered["amount_total"] == 74500
        assert recovered["currency"] == "gbp"
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM territory_brief_consents WHERE order_id = $1",
                order_id,
            )
            == 1
        )

        async with conn.transaction():
            await billing._handle_refund(
                conn,
                {
                    "id": "ch_post_upload_failure",
                    "amount": 74500,
                    "amount_refunded": 74500,
                    "refunded": True,
                    "payment_intent": "pi_generation_recovery",
                },
            )
        assert await conn.fetchval("SELECT status FROM territory_brief_orders WHERE id = $1", order_id) == "refunded"

        with pytest.raises(fulfil.TerritoryBriefFulfilmentError, match="refunded"):
            async with conn.transaction():
                await fulfil.fulfil_territory_brief_order(
                    conn,
                    {"id": authoritative["id"]},
                    cfg=_cfg(),
                    deps=_successful_deps(authoritative, generated, uploads),
                )
        assert generated == ["attempted"]
        assert uploads == ["pdf", "csv"]
        await _assert_no_delivery(conn, order_id)
    finally:
        await conn.close()
