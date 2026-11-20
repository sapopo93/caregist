"""Operator History paid path against a real Postgres, with Stripe stubbed.

Checkout, the signed payment event, delivery, the account-scoped download, refunds and
recovery. The Stripe calls are replaced by ``StripeStub`` (no network); webhook
signatures are real HMAC signatures checked by the real ``stripe.Webhook``.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

import api.database as api_database
from api.main import app
from api.middleware import ip_rate_limit
from api.middleware.auth import validate_billing_identity
from api.routers import operator_history_orders as router_module
from api.services import operator_history as oh
from api.services import operator_history_orders as service
from api.services import operator_history_render as render
from tests.integration.conftest import MIGRATIONS_DIR, apply_full_schema
from tests.integration.test_operator_history_pg import (
    DISPUTED_LEDGER, DISPUTED_LOCATION, DISPUTED_NAMES, DISPUTED_RECORDED, MULTI, NO_EDITION,
    NO_LOCATIONS, RENAMED, UNKNOWN, add_edition, seed_world, utc,
)
from tests.operator_history_orders_support import (
    PRICE_ID, WEBHOOK_SECRET, StripeStub, completed_event, refund_event, signed_event, valid_price,
)

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio

TERMS_VERSION = "b2b-2026-11-20"
TERMS_SHA = "a" * 64
CHECKOUT = "/api/v1/billing/operator-history-checkout"
WEBHOOK = "/api/v1/billing/webhook"


def _ready_health(_conn):
    async def health(_conn):
        return {"readiness_ok": True, "source_fresh": True, "units": {"countsReconciled": True}}
    return health


class Shop:
    """One isolated database, a Stripe stub, a client and two signed-in accounts."""

    def __init__(self, conn, pool, stub, client, users):
        self.conn, self.pool, self.stub, self.client, self.users = conn, pool, stub, client, users
        self.current = users["a"]

    def as_user(self, key: str) -> None:
        self.current = self.users[key]

    def body(self, provider_id: str = MULTI, **overrides):
        body = {
            "provider_id": provider_id, "email": self.current["email"], "terms_version": TERMS_VERSION,
            "business_use_confirmed": True,
        }
        body.update(overrides)
        return body

    async def checkout(self, provider_id: str = MULTI, **overrides):
        return await self.client.post(CHECKOUT, json=self.body(provider_id, **overrides))

    async def webhook(self, event, *, secret: str = WEBHOOK_SECRET, signature: str | None = None):
        payload, header = signed_event(event, secret=secret)
        headers = {"content-type": "application/json"}
        if signature != "":
            headers["stripe-signature"] = signature or header
        return await self.client.post(WEBHOOK, content=payload, headers=headers)

    async def pay(self, session_id: str, *, event_id: str, **kwargs):
        return await self.webhook(completed_event(self.stub, session_id, event_id=event_id), **kwargs)

    async def buy(self, provider_id: str = MULTI, *, event_id: str = "evt_oh_1"):
        """Checkout and pay. Returns (order_id, session_id)."""
        created = await self.checkout(provider_id)
        assert created.status_code == 200, created.text
        data = created.json()
        paid = await self.pay(data["session_id"], event_id=event_id)
        assert paid.status_code == 200, paid.text
        return data["order_id"], data["session_id"]

    async def order(self, order_id: str):
        return await self.conn.fetchrow("SELECT * FROM operator_history_orders WHERE id = $1::uuid", order_id)

    async def download(self, order_id: str, fmt: str):
        return await self.client.get(f"/api/v1/operator-history/orders/{order_id}/download", params={"format": fmt})


@pytest.fixture
async def shop(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    await apply_full_schema(conn)
    await seed_world(conn)
    # A fresh stored edition, so the source-freshness gate's own edition check passes.
    await add_edition(conn, datetime.now(timezone.utc) - timedelta(hours=1), [("9-L-Z", "1-9000009", "Fresh Care Ltd")], "fresh")
    users = {}
    for key, email in (("a", "buyer.a@example.com"), ("b", "buyer.b@example.com")):
        user_id = await conn.fetchval(
            "INSERT INTO users (email, name, password_hash, is_verified) VALUES ($1, $2, 'x', true) RETURNING id",
            email, key,
        )
        users[key] = {"user_id": user_id, "email": email, "auth_method": "session", "is_verified": True}
    pool = await asyncpg.create_pool(fresh_db, min_size=1, max_size=8)
    monkeypatch.setattr(api_database, "_pool", pool)
    stub = StripeStub().install(monkeypatch)
    settings = router_module.settings
    for name, value in {
        "operator_history_enabled": True, "operator_history_checkout_enabled": True,
        "billing_checkout_enabled": True, "stripe_secret_key": "sk_test_operator_history",
        "stripe_webhook_secret": WEBHOOK_SECRET, "stripe_price_operator_history": PRICE_ID,
        "b2b_terms_version": TERMS_VERSION, "b2b_terms_sha256": TERMS_SHA, "app_url": "https://caregist.test",
    }.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(router_module, "get_pipeline_health", _ready_health(None))
    ip_rate_limit._ip_requests.clear()

    client_holder = {}

    async def identity():
        return dict(client_holder["shop"].current)

    app.dependency_overrides[validate_billing_identity] = identity
    app.dependency_overrides[ip_rate_limit.check_ip_rate_limit] = lambda: None
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        shop = Shop(conn, pool, stub, client, users)
        client_holder["shop"] = shop
        yield shop
    app.dependency_overrides.pop(validate_billing_identity, None)
    app.dependency_overrides.pop(ip_rate_limit.check_ip_rate_limit, None)
    await pool.close()
    await conn.close()


def pdf_text(data: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def csv_rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


# --- the happy path ---------------------------------------------------------


async def test_checkout_pay_deliver_download_end_to_end(shop):
    created = await shop.checkout()
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["price_pence"] == 9500 and data["currency"] == "gbp" and data["reused"] is False
    assert data["checkout_url"] == f"https://checkout.stripe.test/c/pay/{data['session_id']}"
    assert shop.stub.gateway_calls == ["price.retrieve", "session.create"]

    call = shop.stub.calls[1][1]
    assert call["mode"] == "payment"
    assert call["line_items"] == [{"price": PRICE_ID, "quantity": 1}]
    assert call["idempotency_key"] == f"caregist-operator-history-{data['order_id']}"
    assert call["customer_email"] == "buyer.a@example.com"
    meta = call["metadata"]
    assert meta["type"] == "operator_history" and meta["provider_id"] == MULTI
    assert meta["price_pence"] == "9500" and meta["terms_version"] == TERMS_VERSION

    # The order pins the build, the edition and the price, and the acceptance is recorded.
    order = await shop.order(data["order_id"])
    async with shop.pool.acquire() as c, c.transaction(isolation="repeatable_read", readonly=True):
        record = await oh.build_operator_history(c, await oh.resolve_operator(c, provider_id=MULTI))
    assert order["state"] == "pending_payment"
    assert order["content_sha256"] == record["content_sha256"] == data["content_sha256"]
    assert json.loads(order["record"]) == record
    assert order["price_pence"] == 9500 and order["currency"] == "gbp"
    assert order["edition_providers_sha256"] == record["provider"]["edition"]["providers_sha256"]
    assert order["edition_locations_sha256"] == record["provider"]["edition"]["locations_sha256"]
    edition_id = await shop.conn.fetchval(
        "SELECT id FROM territory_brief_source_editions WHERE providers_sha256 = $1", order["edition_providers_sha256"]
    )
    assert order["edition_id"] == edition_id and list(order["edition_ids"]) == [edition_id]
    acceptance = await shop.conn.fetchrow(
        "SELECT * FROM b2b_contract_acceptances WHERE stripe_checkout_session_id = $1", data["session_id"]
    )
    assert acceptance["terms_version"] == TERMS_VERSION and acceptance["user_id"] == shop.users["a"]["user_id"]
    assert order["contract_acceptance_id"] == acceptance["id"]
    assert order["stripe_checkout_session_id"] == data["session_id"]

    # Nothing can be downloaded before payment.
    assert (await shop.download(data["order_id"], "csv")).status_code == 402

    paid = await shop.pay(data["session_id"], event_id="evt_pay")
    assert paid.status_code == 200
    order = await shop.order(data["order_id"])
    assert order["state"] == "delivered"
    assert order["stripe_payment_intent_id"] == shop.stub.payment_intent_for(data["session_id"])
    assert order["amount_total"] == 9500 and order["paid_at"] and order["delivered_at"]

    for fmt in ("csv", "pdf"):
        response = await shop.download(data["order_id"], fmt)
        assert response.status_code == 200
        assert hashlib.sha256(response.content).hexdigest() == order[f"{fmt}_sha256"]
        assert response.headers["x-content-sha256"] == order[f"{fmt}_sha256"]
        assert f"caregist-operator-history-{MULTI}-" in response.headers["content-disposition"]
        assert response.headers["content-disposition"].endswith(f'.{fmt}"')
        assert response.headers["cache-control"] == "private, no-store"
    csv_bytes = (await shop.download(data["order_id"], "csv")).content
    pdf_bytes = (await shop.download(data["order_id"], "pdf")).content

    rows = csv_rows(csv_bytes)
    assert {row["report"] for row in rows} == {"Operator History"}
    assert {row["cqc_provider_id"] for row in rows} == {MULTI}
    assert {row["legal_name_as_held"] for row in rows} == {"Alpha Care Ltd"}
    assert {row["content_sha256"] for row in rows} == {record["content_sha256"]}
    assert {row["edition_retrieved_on"] for row in rows} == {"2026-09-01"}
    assert {row["edition_providers_sha256"] for row in rows} == {record["provider"]["edition"]["providers_sha256"]}
    texts = [row["text"] for row in rows if row["row_type"] == "limit"]
    assert all(limit in texts for limit in record["limits"])
    locations = [row for row in rows if row["row_type"] == "location"]
    assert [row["location_id"] for row in locations] == [loc["location_id"] for loc in record["locations"]]
    events = [row for row in rows if row["row_type"] == "event"]
    assert len(events) == len(record["events"]) > 0
    assert all(row["source_label"] and row["source_url"].startswith("https://") for row in locations + events)

    text = pdf_text(pdf_bytes)
    assert "Operator History" in text and MULTI in text and "Alpha Care Ltd" in text
    assert record["content_sha256"] in text.replace("\n", "")
    assert all(limit.split(".")[0][:40] in text.replace("\n", " ") for limit in record["limits"])
    assert "fixed at that point" in text.replace("\n", " ")

    status = await shop.client.get(f"/api/v1/operator-history/orders/{data['order_id']}")
    assert status.status_code == 200 and status.json()["state"] == "delivered"
    assert status.json()["downloads"]["csv"]["sha256"] == order["csv_sha256"]
    assert "record" not in status.json()


# --- price, refusals and gates ----------------------------------------------


async def test_client_cannot_change_the_price(shop):
    for extra in ({"price_pence": 1}, {"amount": 100}, {"unit_amount": 1}, {"price_id": "price_cheap"}, {"name": "Alpha"}):
        response = await shop.checkout(**extra)
        assert response.status_code == 422, extra
    assert shop.stub.calls == []
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_orders") == 0

    ok = await shop.checkout()
    assert ok.status_code == 200
    create = [kw for name, kw in shop.stub.calls if name == "session.create"][0]
    assert create["line_items"] == [{"price": PRICE_ID, "quantity": 1}]
    assert (await shop.order(ok.json()["order_id"]))["price_pence"] == 9500


async def test_a_stripe_price_that_is_not_95_pounds_closes_checkout_before_a_session_exists(shop):
    for override in ({"unit_amount": 9000}, {"currency": "usd"}, {"type": "recurring"}, {"active": False},
                     {"lookup_key": "other"}, {"product": {"active": False}}):
        shop.stub.price = valid_price(**override)
        response = await shop.checkout()
        assert response.status_code == 503, override
    assert shop.stub.creates == 0


@pytest.mark.parametrize(
    "provider_id, code, status",
    [
        (UNKNOWN, "not_found", 404),
        (DISPUTED_LOCATION, "identity_disputed", 409),
        (DISPUTED_RECORDED, "identity_disputed", 409),
        (DISPUTED_NAMES, "identity_disputed", 409),
        (DISPUTED_LEDGER, "identity_disputed", 409),
        (NO_EDITION, "no_legal_name_held", 409),
        (NO_LOCATIONS, "not_enough_history", 409),
        ("1-12", "invalid_input", 422),
        ("not-an-id", "invalid_input", 422),
    ],
)
async def test_every_stage_one_refusal_blocks_before_any_stripe_call(shop, provider_id, code, status):
    response = await shop.checkout(provider_id)
    assert response.status_code == status, response.text
    assert response.json()["detail"]["code"] == code
    assert response.json()["detail"]["message"] == oh.REFUSAL_MESSAGES[code]
    assert shop.stub.calls == []
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_orders") == 0
    assert await shop.conn.fetchval("SELECT count(*) FROM b2b_contract_acceptances") == 0


async def test_a_name_is_never_accepted_at_checkout_so_an_ambiguous_name_cannot_be_bought(shop):
    # Two operators share the name "Gamma Care Ltd". Checkout takes a Provider ID only.
    response = await shop.client.post(CHECKOUT, json={
        "name": "Gamma Care Ltd", "email": shop.current["email"], "terms_version": TERMS_VERSION,
        "business_use_confirmed": True,
    })
    assert response.status_code == 422
    assert shop.stub.calls == []
    async with shop.pool.acquire() as c:
        with pytest.raises(oh.OperatorRefusal) as excinfo:
            await oh.resolve_operator(c, name="Gamma Care Ltd")
    assert excinfo.value.code == oh.AMBIGUOUS


@pytest.mark.parametrize(
    "health",
    [
        {"readiness_ok": False, "source_fresh": True, "units": {"countsReconciled": True}},
        {"readiness_ok": True, "source_fresh": False, "units": {"countsReconciled": True}},
        {"readiness_ok": True, "source_fresh": True, "units": {"countsReconciled": False}},
        {},
    ],
)
async def test_readiness_gate_closed_is_a_plain_503_with_no_gateway_call_and_no_order(shop, monkeypatch, health):
    async def closed(_conn):
        return health

    monkeypatch.setattr(router_module, "get_pipeline_health", closed)
    response = await shop.checkout()
    assert response.status_code == 503
    assert "source-freshness" in response.json()["detail"]
    assert shop.stub.calls == []
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_orders") == 0


async def test_readiness_needs_a_complete_fresh_stored_edition(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)

        async def health(_conn):
            return {"readiness_ok": True, "source_fresh": True, "units": {"countsReconciled": True}}

        assert await service.readiness_gap(conn, health) == "no CQC evidence edition is stored"
        await add_edition(conn, utc(2026, 9, 1), [("1-L-A", MULTI, "Alpha Care Ltd")], "old")
        assert "stale" in await service.readiness_gap(conn, health)
        await add_edition(conn, datetime.now(timezone.utc) - timedelta(hours=1), [("1-L-B", MULTI, "Alpha Care Ltd")], "new")
        assert await service.readiness_gap(conn, health) is None
    finally:
        await conn.close()


# --- double submit and recovery ---------------------------------------------


async def test_double_submit_yields_one_payable_session(shop):
    first = await shop.checkout()
    second = await shop.checkout()
    assert first.status_code == second.status_code == 200
    assert second.json()["order_id"] == first.json()["order_id"]
    assert second.json()["checkout_url"] == first.json()["checkout_url"]
    assert second.json()["reused"] is True
    assert shop.stub.creates == 1 and shop.stub.live_sessions == [first.json()["session_id"]]
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_orders") == 1
    assert await shop.conn.fetchval("SELECT count(*) FROM b2b_contract_acceptances") == 1


async def test_concurrent_double_submit_yields_one_payable_session(shop):
    results = await asyncio.gather(*(shop.checkout() for _ in range(4)))
    assert {r.status_code for r in results} == {200}
    assert len({r.json()["session_id"] for r in results}) == 1
    assert len({r.json()["order_id"] for r in results}) == 1
    assert shop.stub.creates == 1
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_orders") == 1


async def test_lost_response_is_recovered_without_a_second_session(shop):
    first = await shop.checkout()
    # The buyer never saw that response. Asking again returns the stored session, with no Stripe call.
    calls_before = list(shop.stub.calls)
    again = await shop.checkout()
    assert again.json()["checkout_url"] == first.json()["checkout_url"]
    assert shop.stub.calls == calls_before


async def test_a_session_that_cannot_be_recorded_is_expired_and_the_next_submit_starts_clean(shop, monkeypatch):
    real = service.attach_session
    state = {"failed": False}

    async def flaky(*args, **kwargs):
        if not state["failed"]:
            state["failed"] = True
            raise RuntimeError("database lost the connection")
        return await real(*args, **kwargs)

    monkeypatch.setattr(service, "attach_session", flaky)
    broken = await shop.checkout()
    assert broken.status_code == 500
    assert shop.stub.expired == ["cs_test_oh_1"] and shop.stub.live_sessions == []
    assert await shop.conn.fetchval("SELECT state FROM operator_history_orders") == "expired"
    assert await shop.conn.fetchval("SELECT count(*) FROM b2b_contract_acceptances") == 0

    retry = await shop.checkout()
    assert retry.status_code == 200
    assert shop.stub.live_sessions == [retry.json()["session_id"]]
    assert retry.json()["session_id"] != "cs_test_oh_1"


async def test_a_pending_order_taken_under_older_terms_is_expired_and_not_reused(shop, monkeypatch):
    first = (await shop.checkout()).json()
    monkeypatch.setattr(router_module.settings, "b2b_terms_version", "b2b-2026-12-01")
    monkeypatch.setattr(router_module.settings, "b2b_terms_sha256", "b" * 64)
    second = await shop.checkout(terms_version="b2b-2026-12-01")
    assert second.status_code == 200
    assert second.json()["order_id"] != first["order_id"] and second.json()["reused"] is False
    assert (await shop.order(first["order_id"]))["state"] == "expired"
    assert (await shop.order(second.json()["order_id"]))["terms_version"] == "b2b-2026-12-01"


async def test_a_pending_order_past_its_checkout_lifetime_is_expired_and_replaced(shop):
    first = (await shop.checkout()).json()
    await shop.conn.execute("ALTER TABLE operator_history_orders DISABLE TRIGGER operator_history_orders_guard_trg")
    await shop.conn.execute("UPDATE operator_history_orders SET checkout_expires_at = NOW() - INTERVAL '1 minute'")
    await shop.conn.execute("ALTER TABLE operator_history_orders ENABLE TRIGGER operator_history_orders_guard_trg")
    second = (await shop.checkout()).json()
    assert second["order_id"] != first["order_id"] and second["session_id"] != first["session_id"]
    assert (await shop.order(first["order_id"]))["state"] == "expired"


async def test_two_purchases_of_the_same_operator_are_two_orders(shop):
    first_order, first_session = await shop.buy(event_id="evt_first")
    second = await shop.checkout()
    assert second.status_code == 200
    assert second.json()["order_id"] != first_order and second.json()["session_id"] != first_session
    assert second.json()["reused"] is False
    keys = [kw["idempotency_key"] for name, kw in shop.stub.calls if name == "session.create"]
    assert len(set(keys)) == 2
    paid = await shop.pay(second.json()["session_id"], event_id="evt_second")
    assert paid.status_code == 200
    rows = await shop.conn.fetch("SELECT id, state FROM operator_history_orders WHERE provider_id = $1", MULTI)
    assert sorted(r["state"] for r in rows) == ["delivered", "delivered"]
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 4


# --- the signed payment event -------------------------------------------------


async def test_a_bad_or_missing_signature_is_rejected_and_changes_nothing(shop):
    created = (await shop.checkout()).json()
    event = completed_event(shop.stub, created["session_id"], event_id="evt_bad")
    wrong = await shop.webhook(event, secret="whsec_not_ours")
    missing = await shop.webhook(event, signature="")
    stale_payload, stale_header = signed_event(event, timestamp=1_000_000)
    stale = await shop.client.post(WEBHOOK, content=stale_payload, headers={"stripe-signature": stale_header})
    assert wrong.status_code == missing.status_code == stale.status_code == 400
    assert (await shop.order(created["order_id"]))["state"] == "pending_payment"
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 0
    assert "session.retrieve" not in shop.stub.gateway_calls


async def test_replayed_event_creates_no_second_delivery(shop):
    order_id, session_id = await shop.buy(event_id="evt_replay")
    before = await shop.conn.fetch("SELECT id, artefact_sha256 FROM operator_history_artefacts ORDER BY id")
    again = await shop.pay(session_id, event_id="evt_replay")
    assert again.status_code == 200
    after = await shop.conn.fetch("SELECT id, artefact_sha256 FROM operator_history_artefacts ORDER BY id")
    assert [tuple(r) for r in before] == [tuple(r) for r in after] and len(after) == 2
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'operator_history.order.deliver' AND target_id = $1", order_id
    ) == 1
    assert await shop.conn.fetchval("SELECT count(*) FROM stripe_processed_events WHERE event_id = 'evt_replay'") == 1


async def test_a_different_event_for_an_already_delivered_session_delivers_nothing_more(shop):
    order_id, session_id = await shop.buy(event_id="evt_one")
    again = await shop.webhook(
        completed_event(shop.stub, session_id, event_id="evt_two", event_type="checkout.session.async_payment_succeeded")
    )
    assert again.status_code == 200
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 2
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'operator_history.order.deliver' AND target_id = $1", order_id
    ) == 1


@pytest.mark.parametrize(
    "tamper",
    ["amount", "currency", "unpaid_status_other", "line_item", "metadata_hash", "metadata_user", "no_acceptance",
     "other_terms"],
)
async def test_a_payment_that_does_not_match_the_pinned_order_is_refused_and_delivers_nothing(shop, tamper):
    created = (await shop.checkout()).json()
    session_id = created["session_id"]
    if tamper == "amount":
        shop.stub.amount_total = 100
    elif tamper == "currency":
        shop.stub.currency = "usd"
    elif tamper == "unpaid_status_other":
        shop.stub.payment_status = "no_payment_required"
    elif tamper == "line_item":
        shop.stub.sessions[session_id]["line_items"] = [{"price": "price_other", "quantity": 1}]
    elif tamper == "metadata_hash":
        shop.stub.sessions[session_id]["metadata"]["content_sha256"] = "0" * 64
    elif tamper == "metadata_user":
        shop.stub.sessions[session_id]["metadata"]["user_id"] = "999999"
    elif tamper == "no_acceptance":
        await shop.conn.execute("ALTER TABLE b2b_contract_acceptances DISABLE TRIGGER trg_b2b_contract_acceptances_immutable")
        await shop.conn.execute("ALTER TABLE operator_history_orders DISABLE TRIGGER operator_history_orders_guard_trg")
        await shop.conn.execute("UPDATE operator_history_orders SET contract_acceptance_id = NULL")
        await shop.conn.execute("DELETE FROM b2b_contract_acceptances")
    elif tamper == "other_terms":
        await shop.conn.execute("ALTER TABLE b2b_contract_acceptances DISABLE TRIGGER trg_b2b_contract_acceptances_immutable")
        await shop.conn.execute("UPDATE b2b_contract_acceptances SET terms_version = 'b2b-other'")
    response = await shop.pay(session_id, event_id="evt_tamper")
    assert response.status_code == 500
    order = await shop.order(created["order_id"])
    assert order["state"] == "pending_payment" and order["stripe_payment_intent_id"] is None
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 0
    assert await shop.conn.fetchval("SELECT count(*) FROM stripe_processed_events") == 0


async def test_a_delayed_payment_method_is_paid_by_the_later_event(shop):
    created = (await shop.checkout()).json()
    shop.stub.payment_status = "unpaid"
    pending = await shop.pay(created["session_id"], event_id="evt_unpaid")
    assert pending.status_code == 200
    assert (await shop.order(created["order_id"]))["state"] == "pending_payment"
    shop.stub.payment_status = "paid"
    done = await shop.webhook(completed_event(
        shop.stub, created["session_id"], event_id="evt_later", event_type="checkout.session.async_payment_succeeded"))
    assert done.status_code == 200
    assert (await shop.order(created["order_id"]))["state"] == "delivered"


# --- interruption between paid and delivered -------------------------------------


async def test_a_failure_after_payment_leaves_it_paid_and_visible_and_redelivery_finishes_it_once(shop, monkeypatch):
    created = (await shop.checkout()).json()
    real_pdf = render.render_pdf
    monkeypatch.setattr(render, "render_pdf", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("pdf writer fell over")))
    failed = await shop.pay(created["session_id"], event_id="evt_flaky")
    assert failed.status_code == 500  # Stripe will redeliver

    order = await shop.order(created["order_id"])
    assert order["state"] == "paid" and order["delivery_attempts"] == 1
    assert "pdf writer fell over" in order["last_error"]
    assert order["stripe_payment_intent_id"] == shop.stub.payment_intent_for(created["session_id"])
    assert order["paid_at"] is not None and order["delivered_at"] is None
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 0
    assert await shop.conn.fetchval("SELECT count(*) FROM stripe_processed_events") == 0
    blocked = await shop.download(created["order_id"], "csv")
    assert blocked.status_code == 409 and "prepared" in blocked.json()["detail"]
    status = await shop.client.get(f"/api/v1/operator-history/orders/{created['order_id']}")
    assert status.json()["state"] == "paid" and status.json()["downloads"] is None

    monkeypatch.setattr(render, "render_pdf", real_pdf)
    redelivered = await shop.pay(created["session_id"], event_id="evt_flaky")
    assert redelivered.status_code == 200
    order = await shop.order(created["order_id"])
    assert order["state"] == "delivered" and order["last_error"] is None
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 2
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'operator_history.order.deliver'") == 1
    once_more = await shop.pay(created["session_id"], event_id="evt_flaky")
    assert once_more.status_code == 200
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 2
    assert (await shop.download(created["order_id"], "pdf")).status_code == 200


async def test_the_retry_command_finishes_a_paid_order_exactly_once(shop, monkeypatch, fresh_db):
    from tools.retry_operator_history_delivery import _run

    created = (await shop.checkout()).json()
    real_csv = render.render_csv
    monkeypatch.setattr(render, "render_csv", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    assert (await shop.pay(created["session_id"], event_id="evt_retry")).status_code == 500
    monkeypatch.setattr(render, "render_csv", real_csv)

    dry = await _run(fresh_db, apply=False, include_failed=False, limit=10)
    assert [(item["order_id"], item["result"]) for item in dry] == [(created["order_id"], "would_deliver")]
    assert (await shop.order(created["order_id"]))["state"] == "paid"

    done = await _run(fresh_db, apply=True, include_failed=False, limit=10)
    assert [(item["order_id"], item["result"]) for item in done] == [(created["order_id"], "delivered")]
    assert await _run(fresh_db, apply=True, include_failed=False, limit=10) == []
    assert (await shop.order(created["order_id"]))["state"] == "delivered"
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 2
    # Stripe's later redelivery of the original event finds it delivered and does nothing more.
    assert (await shop.pay(created["session_id"], event_id="evt_retry")).status_code == 200
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 2
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'operator_history.order.deliver'") == 1


async def test_repeated_failures_mark_it_failed_and_the_retry_command_can_still_finish_it(shop, monkeypatch, fresh_db):
    from tools.retry_operator_history_delivery import _run

    created = (await shop.checkout()).json()
    real_pdf = render.render_pdf
    monkeypatch.setattr(render, "render_pdf", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("still broken")))
    for _attempt in range(service.MAX_DELIVERY_ATTEMPTS):
        assert (await shop.pay(created["session_id"], event_id="evt_cap")).status_code == 500
    order = await shop.order(created["order_id"])
    assert order["state"] == "failed" and order["delivery_attempts"] == service.MAX_DELIVERY_ATTEMPTS
    assert (await shop.download(created["order_id"], "csv")).status_code == 409

    monkeypatch.setattr(render, "render_pdf", real_pdf)
    assert await _run(fresh_db, apply=True, include_failed=False, limit=10) == []
    done = await _run(fresh_db, apply=True, include_failed=True, limit=10)
    assert [item["result"] for item in done] == ["delivered"]
    assert (await shop.order(created["order_id"]))["state"] == "delivered"


# --- the download ----------------------------------------------------------------


async def test_another_account_gets_the_same_404_as_an_unknown_order(shop):
    order_id, _ = await shop.buy()
    shop.as_user("b")
    other = await shop.download(order_id, "csv")
    unknown = await shop.download("00000000-0000-4000-8000-000000000000", "csv")
    malformed = await shop.download("not-a-uuid", "csv")
    assert other.status_code == unknown.status_code == malformed.status_code == 404
    assert other.json() == unknown.json() == malformed.json()
    other_status = await shop.client.get(f"/api/v1/operator-history/orders/{order_id}")
    assert other_status.status_code == 404 and other_status.json() == unknown.json()
    shop.as_user("a")
    assert (await shop.download(order_id, "csv")).status_code == 200


async def test_unpaid_and_expired_orders_are_refused_and_an_unknown_format_is_a_422(shop):
    created = (await shop.checkout()).json()
    assert (await shop.download(created["order_id"], "pdf")).status_code == 402
    await shop.conn.execute("UPDATE operator_history_orders SET state = 'expired'")
    assert (await shop.download(created["order_id"], "pdf")).status_code == 402
    assert (await shop.download(created["order_id"], "xml")).status_code == 422


# --- refunds ---------------------------------------------------------------------


async def test_a_full_refund_revokes_access_and_changes_state_only(shop):
    order_id, session_id = await shop.buy()
    before = await shop.order(order_id)
    before_files = await shop.conn.fetch("SELECT id, artefact_sha256, content FROM operator_history_artefacts ORDER BY id")
    assert (await shop.download(order_id, "csv")).status_code == 200

    event = refund_event(shop.stub.payment_intent_for(session_id), event_id="evt_refund")
    assert (await shop.webhook(event)).status_code == 200
    after = await shop.order(order_id)
    assert after["state"] == "refunded" and after["refunded_at"] is not None
    changed = {key for key in before.keys() if before[key] != after[key]}
    assert changed == {"state", "refunded_at", "updated_at"}
    after_files = await shop.conn.fetch("SELECT id, artefact_sha256, content FROM operator_history_artefacts ORDER BY id")
    assert [tuple(r) for r in before_files] == [tuple(r) for r in after_files]
    for fmt in ("csv", "pdf"):
        refused = await shop.download(order_id, fmt)
        assert refused.status_code == 410 and "refunded" in refused.json()["detail"]
    assert (await shop.webhook(event)).status_code == 200  # replay: nothing more happens
    # A replayed payment event cannot bring a refunded order back.
    assert (await shop.pay(session_id, event_id="evt_late_pay")).status_code == 200
    assert (await shop.order(order_id))["state"] == "refunded"


async def test_a_partial_refund_changes_nothing_here(shop):
    order_id, session_id = await shop.buy()
    event = refund_event(shop.stub.payment_intent_for(session_id), event_id="evt_partial", full=False)
    assert (await shop.webhook(event)).status_code == 200
    assert (await shop.order(order_id))["state"] == "delivered"
    assert (await shop.download(order_id, "csv")).status_code == 200
    assert await shop.conn.fetchval(
        "SELECT metadata->>'fully_refunded' FROM audit_log WHERE action = 'billing.charge.refund' "
        "AND metadata->>'payment_intent' = $1", shop.stub.payment_intent_for(session_id)) == "false"


async def test_a_refund_that_arrives_before_the_payment_event_means_nothing_is_delivered(shop):
    created = (await shop.checkout()).json()
    intent = shop.stub.payment_intent_for(created["session_id"])
    assert (await shop.webhook(refund_event(intent, event_id="evt_refund_first"))).status_code == 200
    assert (await shop.order(created["order_id"]))["state"] == "pending_payment"  # no order is bound to it yet
    assert (await shop.pay(created["session_id"], event_id="evt_pay_after")).status_code == 200
    order = await shop.order(created["order_id"])
    assert order["state"] == "refunded" and order["stripe_payment_intent_id"] == intent
    assert await shop.conn.fetchval("SELECT count(*) FROM operator_history_artefacts") == 0


# --- the pinned edition -----------------------------------------------------------


async def test_an_edition_replaced_after_payment_does_not_change_the_delivered_record(shop):
    created = (await shop.checkout(RENAMED)).json()
    pinned = await shop.order(created["order_id"])
    assert pinned["legal_name"] == "Beta Homes Group Ltd"  # the newest edition at checkout (retrieved 15 Oct 2026)

    # CQC's next edition renames the operator again, after the buyer paid nothing yet.
    await add_edition(shop.conn, datetime.now(timezone.utc), [("2-L-A", RENAMED, "Beta Homes Holdings Ltd")], "replacement")
    paid = await shop.pay(created["session_id"], event_id="evt_edition")
    assert paid.status_code == 200
    csv_bytes = (await shop.download(created["order_id"], "csv")).content
    rows = csv_rows(csv_bytes)
    assert {row["legal_name_as_held"] for row in rows} == {"Beta Homes Group Ltd"}
    assert {row["edition_retrieved_on"] for row in rows} == {"2026-10-15"}
    assert {row["edition_providers_sha256"] for row in rows} == {pinned["edition_providers_sha256"]}
    notice = [row["text"] for row in rows if "fixed at that point" in row["text"]][0]
    assert "retrieved on 15 October 2026" in notice
    pdf = pdf_text((await shop.download(created["order_id"], "pdf")).content).replace("\n", " ")
    assert "Beta Homes Group Ltd" in pdf and "Beta Homes Holdings" not in pdf and "15 October 2026" in pdf

    # A purchase made now would be built on the replacement, so the two differ.
    async with shop.pool.acquire() as c:
        fresh = await oh.build_operator_history(c, await oh.resolve_operator(c, provider_id=RENAMED))
    assert fresh["provider"]["legal_name"] == "Beta Homes Holdings Ltd"
    assert fresh["content_sha256"] != pinned["content_sha256"]


# --- the database keeps the delivered record immutable -----------------------------------


async def test_the_database_refuses_to_rewrite_a_delivered_order_or_its_files(shop):
    order_id, session_id = await shop.buy()
    c = shop.conn
    for statement in (
        "UPDATE operator_history_orders SET record = '{}'::jsonb",
        "UPDATE operator_history_orders SET content_sha256 = repeat('0', 64)",
        "UPDATE operator_history_orders SET price_pence = 1",
        "UPDATE operator_history_orders SET edition_id = edition_id + 1",
        "UPDATE operator_history_orders SET csv_sha256 = repeat('0', 64)",
        "UPDATE operator_history_orders SET stripe_payment_intent_id = 'pi_other'",
        "UPDATE operator_history_orders SET state = 'paid'",
        "UPDATE operator_history_orders SET state = 'pending_payment'",
        "DELETE FROM operator_history_orders",
        "UPDATE operator_history_artefacts SET content = '\\x00'::bytea",
        "UPDATE operator_history_artefacts SET artefact_sha256 = repeat('0', 64)",
        "DELETE FROM operator_history_artefacts",
    ):
        with pytest.raises(asyncpg.PostgresError):
            await c.execute(statement)
    assert (await shop.order(order_id))["state"] == "delivered"
    await c.execute("UPDATE operator_history_orders SET state = 'refunded', refunded_at = NOW()")
    for statement in ("UPDATE operator_history_orders SET state = 'delivered'",
                      "UPDATE operator_history_orders SET state = 'paid'"):
        with pytest.raises(asyncpg.PostgresError):
            await c.execute(statement)


async def test_the_database_checks_a_file_against_its_own_hash(shop):
    order_id, _ = await shop.buy()
    with pytest.raises(asyncpg.CheckViolationError):
        await shop.conn.execute(
            "INSERT INTO operator_history_artefacts (order_id, format, filename, content_type, content, byte_size, artefact_sha256) "
            "VALUES ($1::uuid, 'csv', 'x.csv', 'text/csv', '\\x41'::bytea, 1, repeat('0', 64))", order_id,
        )


# --- the migration ---------------------------------------------------------------------


async def test_migration_075_applies_cleanly_and_its_down_script_reverses_it(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        applied = await apply_full_schema(conn)
        assert applied[-1] == "075_operator_history_orders.sql"
        assert applied[-2] == "074_operator_history.sql"
        tables = {"operator_history_orders", "operator_history_artefacts"}
        present = {r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
        assert tables <= present
        down = (Path(MIGRATIONS_DIR) / "down" / "075_operator_history_orders.down.sql").read_text(encoding="utf-8")
        await conn.execute(down)
        present = {r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
        assert not tables & present
        functions = {r["proname"] for r in await conn.fetch("SELECT proname FROM pg_proc WHERE proname LIKE 'operator_history_%'")}
        assert functions == set()
        up = (Path(MIGRATIONS_DIR) / "075_operator_history_orders.sql").read_text(encoding="utf-8")
        await conn.execute(up)
        await conn.execute(up)  # idempotent
        assert tables <= {r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    finally:
        await conn.close()
