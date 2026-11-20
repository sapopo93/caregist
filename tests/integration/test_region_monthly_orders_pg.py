"""Region Monthly paid path against a real Postgres, with Stripe stubbed.

Checkout, the signed payment event, per-month entitlements, the account-scoped
download, refunds and recovery. The Stripe calls are replaced by
``RegionMonthlyStripeStub`` (no network); webhook signatures are real HMAC signatures
checked by the real ``stripe.Webhook``.

Seeded builds (version 1 unless stated), built through the real ``store_build``:

  London, all services       April to October 2026
  London, home-care          April to October 2026
  South East, all services   April to October 2026
  South West, all services   April, May and July to October 2026 (June is missing)
  East                       none

"Now" is 20 November 2026 unless a test moves it, so October 2026 is the latest month
that can be built and November 2026 is a future month (built from 7 December).
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

import api.database as api_database
from api.main import app
from api.middleware import ip_rate_limit
from api.middleware.auth import validate_billing_identity
from api.routers import region_monthly_orders as router_module
from api.services import region_monthly as rm
from api.services import region_monthly_orders as service
from api.services import region_monthly_render as render
from tests.integration.conftest import MIGRATIONS_DIR, apply_full_schema
from tests.region_monthly_orders_support import (
    AS_OF, PRICE_IDS, WEBHOOK_SECRET, RegionMonthlyStripeStub, completed_event, refund_event, signed_event,
)

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio

UTC = timezone.utc
TERMS_VERSION = "b2b-2026-11-20"
TERMS_SHA = "a" * 64
CHECKOUT = "/api/v1/billing/region-monthly-checkout"
WEBHOOK = "/api/v1/billing/webhook"
PRICES = {kind: spec.price_pence for kind, spec in rm.PURCHASE_KINDS.items()}


def d(y: int, m: int, day: int = 1) -> date:
    return date(y, m, day)


def months(first: date, count: int) -> list[date]:
    return rm.month_range(first, count)


SEEDS = [
    ("London", None, months(d(2026, 4), 7)),
    ("London", "home-care", months(d(2026, 4), 7)),
    ("South East", None, months(d(2026, 4), 7)),
    ("South West", None, [d(2026, 4), d(2026, 5)] + months(d(2026, 7), 4)),
]


def build_row(month: date, bump: int = 0) -> dict[str, int]:
    base = month.month * 3 + bump
    return {
        "new_registrations": base, "outstanding": 1, "good": 2 + bump, "requires_improvement": 1, "inadequate": 0,
        "no_published_rating_value": 1, "ratings_total": 5 + bump, "closures_observed": 2, "reinstatements_observed": 1,
    }


async def add_build(conn, month: date, region: str = "London", service_slug: str | None = None, *, bump: int = 0,
                    correction: str | None = None):
    built = rm._assemble(month, region, service_slug, build_row(month, bump), AS_OF)
    return await rm.store_build(conn, built, correction_reason=correction)


def _ready_health():
    async def health(_conn):
        return {"readiness_ok": True, "source_fresh": True, "units": {"countsReconciled": True}}
    return health


class Shop:
    """One isolated database, a Stripe stub, a client and two signed-in accounts."""

    def __init__(self, conn, pool, stub, client, users, clock):
        self.conn, self.pool, self.stub, self.client, self.users, self.clock = conn, pool, stub, client, users, clock
        self.current = users["a"]

    def as_user(self, key: str) -> None:
        self.current = self.users[key]

    def set_now(self, moment: datetime) -> None:
        self.clock["now"] = moment

    def body(self, **overrides):
        body = {
            "region": "London", "kind": "six", "first_month": "2026-05", "email": self.current["email"],
            "terms_version": TERMS_VERSION, "business_use_confirmed": True,
        }
        body.update(overrides)
        return {key: value for key, value in body.items() if value is not None}

    async def checkout(self, **overrides):
        return await self.client.post(CHECKOUT, json=self.body(**overrides))

    async def webhook(self, event, *, secret: str = WEBHOOK_SECRET, signature: str | None = None):
        payload, header = signed_event(event, secret=secret)
        headers = {"content-type": "application/json"}
        if signature != "":
            headers["stripe-signature"] = signature or header
        return await self.client.post(WEBHOOK, content=payload, headers=headers)

    async def pay(self, session_id: str, *, event_id: str, **kwargs):
        return await self.webhook(completed_event(self.stub, session_id, event_id=event_id), **kwargs)

    async def buy(self, *, event_id: str = "evt_rm_1", **overrides):
        """Checkout and pay. Returns (order_id, session_id)."""
        created = await self.checkout(**overrides)
        assert created.status_code == 200, created.text
        data = created.json()
        paid = await self.pay(data["session_id"], event_id=event_id)
        assert paid.status_code == 200, paid.text
        return data["order_id"], data["session_id"]

    async def order(self, order_id: str):
        return await self.conn.fetchrow("SELECT * FROM region_monthly_orders WHERE id = $1::uuid", order_id)

    async def entitlements(self, order_id: str | None = None):
        if order_id:
            return await self.conn.fetch(
                "SELECT order_id, period_month, created_at FROM region_monthly_entitlements "
                "WHERE order_id = $1::uuid ORDER BY period_month", order_id)
        return await self.conn.fetch("SELECT order_id, period_month, created_at FROM region_monthly_entitlements "
                                     "ORDER BY order_id, period_month")

    async def count(self, table: str) -> int:
        return await self.conn.fetchval(f"SELECT count(*) FROM {table}")

    async def download(self, order_id: str, month: str, fmt: str):
        return await self.client.get(f"/api/v1/region-monthly/orders/{order_id}/months/{month}/download",
                                     params={"format": fmt})

    async def status(self, order_id: str):
        return await self.client.get(f"/api/v1/region-monthly/orders/{order_id}")

    def refund(self, session_id: str, *, event_id: str, kind: str = "six", full: bool = True):
        return self.webhook(refund_event(
            self.stub.payment_intent_for(session_id), event_id=event_id, amount=PRICES[kind], full=full))


@pytest.fixture
async def shop(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    await apply_full_schema(conn)
    for region, slug, built_months in SEEDS:
        for month in built_months:
            await add_build(conn, month, region, slug)
    users = {}
    for key, email in (("a", "buyer.a@example.com"), ("b", "buyer.b@example.com")):
        user_id = await conn.fetchval(
            "INSERT INTO users (email, name, password_hash, is_verified) VALUES ($1, $2, 'x', true) RETURNING id",
            email, key,
        )
        users[key] = {"user_id": user_id, "email": email, "auth_method": "session", "is_verified": True}
    pool = await asyncpg.create_pool(fresh_db, min_size=1, max_size=8)
    monkeypatch.setattr(api_database, "_pool", pool)
    stub = RegionMonthlyStripeStub().install(monkeypatch)
    settings = router_module.settings
    for name, value in {
        "region_monthly_enabled": True, "region_monthly_checkout_enabled": True,
        "billing_checkout_enabled": True, "stripe_secret_key": "sk_test_region_monthly",
        "stripe_webhook_secret": WEBHOOK_SECRET,
        "stripe_price_region_monthly_single": PRICE_IDS["single"],
        "stripe_price_region_monthly_six": PRICE_IDS["six"],
        "stripe_price_region_monthly_twelve": PRICE_IDS["twelve"],
        "b2b_terms_version": TERMS_VERSION, "b2b_terms_sha256": TERMS_SHA, "app_url": "https://caregist.test",
    }.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(router_module, "get_pipeline_health", _ready_health())
    clock = {"now": AS_OF}
    monkeypatch.setattr(router_module, "_now", lambda: clock["now"])
    ip_rate_limit._ip_requests.clear()

    holder = {}

    async def identity():
        return dict(holder["shop"].current)

    app.dependency_overrides[validate_billing_identity] = identity
    app.dependency_overrides[ip_rate_limit.check_ip_rate_limit] = lambda: None
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        shop = Shop(conn, pool, stub, client, users, clock)
        holder["shop"] = shop
        yield shop
    app.dependency_overrides.pop(validate_billing_identity, None)
    app.dependency_overrides.pop(ip_rate_limit.check_ip_rate_limit, None)
    await pool.close()
    await conn.close()


def pdf_text(data: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def csv_rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


MAY_TO_OCT = [rm.month_key(m) for m in months(d(2026, 5), 6)]


# --- the happy path ---------------------------------------------------------


async def test_checkout_pay_entitle_download_end_to_end(shop):
    created = await shop.checkout()
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["price_pence"] == 24500 and data["currency"] == "gbp" and data["reused"] is False
    assert data["checkout_url"] == f"https://checkout.stripe.test/c/pay/{data['session_id']}"
    assert [m["month"] for m in data["months"]] == MAY_TO_OCT and {m["status"] for m in data["months"]} == {"built"}
    assert data["future_months"] == [] and data["future_month_notice"] is None
    assert shop.stub.gateway_calls == ["price.retrieve", "session.create"]

    call = shop.stub.calls[1][1]
    assert call["mode"] == "payment" and call["line_items"] == [{"price": PRICE_IDS["six"], "quantity": 1}]
    assert call["idempotency_key"] == f"caregist-region-monthly-{data['order_id']}"
    assert call["customer_email"] == "buyer.a@example.com"
    meta = call["metadata"]
    assert meta["type"] == "region_monthly" and meta["region"] == "London" and meta["service"] == "all-services"
    assert meta["kind"] == "six" and meta["months"] == ",".join(MAY_TO_OCT) and meta["price_pence"] == "24500"
    assert meta["terms_version"] == TERMS_VERSION

    # The order pins the months, the price and the terms, and the acceptance is recorded.
    order = await shop.order(data["order_id"])
    assert order["state"] == "pending_payment" and order["kind"] == "six" and order["month_count"] == 6
    assert order["months"] == months(d(2026, 5), 6) and order["future_months"] == [] and order["service_slug"] is None
    assert order["price_pence"] == 24500 and order["currency"] == "gbp" and order["stripe_price_id"] == PRICE_IDS["six"]
    acceptance = await shop.conn.fetchrow(
        "SELECT * FROM b2b_contract_acceptances WHERE stripe_checkout_session_id = $1", data["session_id"])
    assert acceptance["terms_version"] == TERMS_VERSION and acceptance["user_id"] == shop.users["a"]["user_id"]
    assert order["contract_acceptance_id"] == acceptance["id"]
    assert await shop.count("region_monthly_entitlements") == 0

    # Nothing can be downloaded before payment.
    refused = await shop.download(data["order_id"], "2026-05", "csv")
    assert refused.status_code == 402 and refused.json()["detail"]["code"] == "order_not_paid"
    pending_view = (await shop.status(data["order_id"])).json()
    assert pending_view["state"] == "pending_payment" and {m["availability"] for m in pending_view["months"]} == {"not_paid"}

    paid = await shop.pay(data["session_id"], event_id="evt_pay")
    assert paid.status_code == 200
    order = await shop.order(data["order_id"])
    assert order["state"] == "paid" and order["stripe_payment_intent_id"] == shop.stub.payment_intent_for(data["session_id"])
    assert order["amount_total"] == 24500 and order["paid_at"] is not None
    entitlements = await shop.entitlements(data["order_id"])
    assert [row["period_month"] for row in entitlements] == months(d(2026, 5), 6)

    for month in MAY_TO_OCT:
        for fmt in ("csv", "pdf"):
            response = await shop.download(data["order_id"], month, fmt)
            assert response.status_code == 200, (month, fmt, response.text)
            assert response.headers["x-content-sha256"] == hashlib.sha256(response.content).hexdigest()
            assert response.headers["content-disposition"] == (
                f'attachment; filename="caregist-region-monthly-london-all-services-{month}-v1.{fmt}"')
            assert response.headers["x-build-version"] == "1" and response.headers["cache-control"] == "private, no-store"

    view = (await shop.status(data["order_id"])).json()
    assert view["state"] == "paid" and [m["month"] for m in view["months"]] == MAY_TO_OCT
    assert {m["availability"] for m in view["months"]} == {"available"}
    assert all(m["build_version"] == 1 and len(m["content_sha256"]) == 64 for m in view["months"])
    assert "stripe" not in json.dumps(view).lower()


async def test_each_purchase_kind_is_priced_from_the_central_table_in_the_pence_the_stripe_price_holds(shop):
    single = (await shop.checkout(kind="single", first_month="2026-10")).json()
    six = (await shop.checkout(kind="six", service="home-care")).json()
    twelve = (await shop.checkout(kind="twelve", first_month="2026-04", region="South East",
                                  accept_future_months=True)).json()
    assert (single["price_pence"], six["price_pence"], twelve["price_pence"]) == (4900, 24500, 44500)
    for body, kind in ((single, "single"), (six, "six"), (twelve, "twelve")):
        order = await shop.order(body["order_id"])
        assert (order["kind"], order["price_pence"], order["stripe_price_id"]) == (kind, PRICES[kind], PRICE_IDS[kind])
    sessions = [kw for name, kw in shop.stub.calls if name == "session.create"]
    assert [s["line_items"][0]["price"] for s in sessions] == [PRICE_IDS["single"], PRICE_IDS["six"], PRICE_IDS["twelve"]]
    assert [await shop.conn.fetchval("SELECT month_count FROM region_monthly_orders WHERE id = $1::uuid", b["order_id"])
            for b in (single, six, twelve)] == [1, 6, 12]
    assert twelve["months"][0]["month"] == "2026-04" and twelve["months"][-1]["month"] == "2027-03"
    assert twelve["future_months"] == ["2026-11", "2026-12", "2027-01", "2027-02", "2027-03"]


# --- price, refusals and gates ----------------------------------------------


async def test_client_cannot_change_the_price(shop):
    for extra in ({"price_pence": 1}, {"amount": 100}, {"unit_amount": 1}, {"price_id": "price_cheap"},
                  {"months": ["2026-05"]}, {"name": "London"}):
        response = await shop.checkout(**extra)
        assert response.status_code == 422, extra
    assert shop.stub.calls == []
    assert await shop.count("region_monthly_orders") == 0

    ok = await shop.checkout()
    assert ok.status_code == 200
    create = [kw for name, kw in shop.stub.calls if name == "session.create"][0]
    assert create["line_items"] == [{"price": PRICE_IDS["six"], "quantity": 1}]
    assert (await shop.order(ok.json()["order_id"]))["price_pence"] == 24500


@pytest.mark.parametrize("kind", ["single", "six", "twelve"])
async def test_a_stripe_price_that_does_not_match_closes_checkout_before_a_session_exists(shop, kind):
    first = {"single": "2026-10", "six": "2026-05", "twelve": "2026-04"}[kind]
    for override in ({"unit_amount": PRICES[kind] - 100}, {"currency": "usd"}, {"type": "recurring"}, {"active": False},
                     {"lookup_key": "other"}, {"product": {"active": False}}):
        shop.stub.set_price(kind, **override)
        response = await shop.checkout(kind=kind, first_month=first, accept_future_months=True)
        assert response.status_code == 503, override
    assert shop.stub.creates == 0


REFUSALS = [
    # (overrides, code, status)
    ({"region": "Wales"}, "region_unsupported", 422),
    ({"region": ""}, "region_unsupported", 422),
    ({"region": "Scotland"}, "region_unsupported", 422),
    ({"service": "not-a-service"}, "service_unsupported", 422),
    ({"kind": "weekly"}, "kind_unsupported", 422),
    ({"kind": ""}, "kind_unsupported", 422),
    ({"first_month": "2026-13"}, "months_malformed", 422),
    ({"first_month": "October 2026"}, "months_malformed", 422),
    ({"first_month": ""}, "months_malformed", 422),
    ({"kind": "single", "first_month": "2026-03"}, "month_before_earliest", 422),
    ({"kind": "twelve", "first_month": "2025-12"}, "month_before_earliest", 422),
    ({"region": "East", "kind": "single", "first_month": "2026-10"}, "month_not_built", 409),
    ({"region": "South West", "first_month": "2026-05"}, "month_not_built", 409),
    ({"kind": "single", "first_month": "2026-11"}, "future_months_not_accepted", 409),
    ({"kind": "six", "first_month": "2026-09"}, "future_months_not_accepted", 409),
    ({"kind": "single", "first_month": "2028-01", "accept_future_months": True}, "future_months_too_far", 422),
    ({"kind": "twelve", "first_month": "2027-06", "accept_future_months": True}, "future_months_too_far", 422),
]


@pytest.mark.parametrize(("overrides", "code", "status"), REFUSALS)
async def test_every_purchase_refusal_blocks_before_any_stripe_call(shop, overrides, code, status):
    response = await shop.checkout(**overrides)
    assert response.status_code == status, response.text
    detail = response.json()["detail"]
    assert detail["code"] == code and detail["message"]
    assert rm.REFUSAL_MESSAGES[code].split("{")[0].strip() in detail["message"]
    assert shop.stub.calls == []  # zero gateway calls
    assert await shop.count("region_monthly_orders") == 0
    assert await shop.count("b2b_contract_acceptances") == 0


async def test_an_unbuilt_past_month_names_the_month_and_is_never_sold(shop):
    response = await shop.checkout(region="South West", first_month="2026-05")
    assert response.status_code == 409
    assert "June 2026 has not been built yet" in response.json()["detail"]["message"]
    assert shop.stub.calls == []


async def test_a_purchase_of_unbuilt_future_months_needs_the_explicit_acceptance_and_records_it(shop):
    refused = await shop.checkout(first_month="2026-09")
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "future_months_not_accepted"
    assert "November 2026" in refused.json()["detail"]["message"] and shop.stub.calls == []
    accepted = await shop.checkout(first_month="2026-09", accept_future_months=True)
    assert accepted.status_code == 200
    body = accepted.json()
    assert [(m["month"], m["status"], m["available_from"]) for m in body["months"]] == [
        ("2026-09", "built", None), ("2026-10", "built", None), ("2026-11", "future", "2026-12-07"),
        ("2026-12", "future", "2027-01-07"), ("2027-01", "future", "2027-02-07"), ("2027-02", "future", "2027-03-07")]
    assert body["future_month_notice"] == rm.FUTURE_MONTH_NOTICE
    order = await shop.order(body["order_id"])
    assert order["future_months"] == [d(2026, 11), d(2026, 12), d(2027, 1), d(2027, 2)]
    assert order["future_available_from"] == [d(2026, 12, 7), d(2027, 1, 7), d(2027, 2, 7), d(2027, 3, 7)]
    assert order["future_months_accepted"] is True


async def test_the_clock_change_decides_which_month_is_a_future_month_at_checkout(shop):
    # 00:00 BST on 7 October is 23:00Z on 6 October: September is still a future month one second before.
    shop.set_now(datetime(2026, 10, 6, 22, 59, 59, tzinfo=UTC))
    refused = await shop.checkout(region="East", kind="single", first_month="2026-09")
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "future_months_not_accepted"
    sold = await shop.checkout(region="East", kind="single", first_month="2026-09", accept_future_months=True)
    assert sold.status_code == 200 and sold.json()["months"][0]["available_from"] == "2026-10-07"
    assert shop.stub.creates == 1

    shop.set_now(datetime(2026, 10, 6, 23, 0, 0, tzinfo=UTC))
    not_built = await shop.checkout(region="East", kind="single", first_month="2026-09", accept_future_months=True)
    assert not_built.status_code == 409 and not_built.json()["detail"]["code"] == "month_not_built"
    assert shop.stub.creates == 1


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
    assert await shop.count("region_monthly_orders") == 0


async def test_the_readiness_gate_needs_the_builds_table(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn, through="075_operator_history_orders.sql")  # stage 1's table (076) is absent
        assert "builds" in await service.readiness_gap(conn, _ready_health())
    finally:
        await conn.close()


async def test_the_email_must_belong_to_the_signed_in_account(shop):
    response = await shop.checkout(email="someone.else@example.com")
    assert response.status_code == 403 and shop.stub.calls == []


# --- double submit and recovery ---------------------------------------------


async def test_double_submit_yields_one_payable_session(shop):
    first = await shop.checkout()
    second = await shop.checkout()
    assert first.status_code == second.status_code == 200
    assert second.json()["order_id"] == first.json()["order_id"]
    assert second.json()["checkout_url"] == first.json()["checkout_url"] and second.json()["reused"] is True
    assert shop.stub.creates == 1 and shop.stub.live_sessions == [first.json()["session_id"]]
    assert await shop.count("region_monthly_orders") == 1 and await shop.count("b2b_contract_acceptances") == 1


async def test_concurrent_double_submit_yields_one_payable_session(shop):
    results = await asyncio.gather(*(shop.checkout() for _ in range(4)))
    assert {r.status_code for r in results} == {200}
    assert len({r.json()["session_id"] for r in results}) == 1 and len({r.json()["order_id"] for r in results}) == 1
    assert shop.stub.creates == 1 and await shop.count("region_monthly_orders") == 1


async def test_lost_response_is_recovered_without_a_second_session(shop):
    first = await shop.checkout()
    calls_before = list(shop.stub.calls)
    again = await shop.checkout()
    assert again.json()["checkout_url"] == first.json()["checkout_url"]
    assert [name for name, _ in shop.stub.calls[len(calls_before):]] == []  # not even a Price read


async def test_a_session_created_at_stripe_but_never_recorded_is_found_again_by_its_idempotency_key(shop, monkeypatch):
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
    # The unrecorded session was expired and the order closed, so nothing payable is left behind.
    assert shop.stub.expired == ["cs_test_rm_1"] and shop.stub.live_sessions == []
    assert await shop.conn.fetchval("SELECT state FROM region_monthly_orders") == "expired"
    assert await shop.count("b2b_contract_acceptances") == 0

    retry = await shop.checkout()
    assert retry.status_code == 200
    assert shop.stub.live_sessions == [retry.json()["session_id"]] and retry.json()["session_id"] != "cs_test_rm_1"


async def test_a_lost_response_from_stripe_is_recovered_with_the_same_idempotency_key(shop):
    first = (await shop.checkout()).json()
    # Simulate "Stripe created the session but the reply never reached us": the order has no session recorded.
    await shop.conn.execute("ALTER TABLE region_monthly_orders DISABLE TRIGGER region_monthly_orders_guard_trg")
    await shop.conn.execute("UPDATE region_monthly_orders SET stripe_checkout_session_id = NULL, stripe_checkout_url = NULL")
    await shop.conn.execute("ALTER TABLE region_monthly_orders ENABLE TRIGGER region_monthly_orders_guard_trg")
    # The next submit finds the pending order and asks Stripe again with the same key and parameters.
    again = await shop.checkout()
    assert again.status_code == 200 and again.json()["session_id"] == first["session_id"]
    assert shop.stub.creates == 2 and len(shop.stub.by_key) == 1 and shop.stub.live_sessions == [first["session_id"]]


async def test_a_different_purchase_in_the_same_scope_replaces_the_pending_one_and_closes_its_session(shop):
    first = (await shop.checkout()).json()
    second = await shop.checkout(kind="single", first_month="2026-10")
    assert second.status_code == 200 and second.json()["order_id"] != first["order_id"]
    assert second.json()["reused"] is False and second.json()["price_pence"] == 4900
    assert shop.stub.expired == [first["session_id"]] and shop.stub.live_sessions == [second.json()["session_id"]]
    assert (await shop.order(first["order_id"]))["state"] == "expired"
    assert (await shop.order(second.json()["order_id"]))["state"] == "pending_payment"


async def test_if_stripe_cannot_close_the_earlier_session_nothing_changes_and_the_buyer_is_told(shop):
    first = (await shop.checkout()).json()
    shop.stub.fail_expire = True
    second = await shop.checkout(kind="single", first_month="2026-10")
    assert second.status_code == 409 and second.json()["detail"]["code"] == "checkout_still_open"
    assert shop.stub.creates == 1 and (await shop.order(first["order_id"]))["state"] == "pending_payment"
    assert await shop.count("region_monthly_orders") == 1
    # The earlier checkout is still the buyer's: the same request returns it.
    assert (await shop.checkout()).json()["session_id"] == first["session_id"]


async def test_a_pending_order_taken_under_older_terms_is_replaced(shop, monkeypatch):
    first = (await shop.checkout()).json()
    monkeypatch.setattr(router_module.settings, "b2b_terms_version", "b2b-2026-12-01")
    monkeypatch.setattr(router_module.settings, "b2b_terms_sha256", "b" * 64)
    second = await shop.checkout(terms_version="b2b-2026-12-01")
    assert second.status_code == 200 and second.json()["order_id"] != first["order_id"]
    assert (await shop.order(first["order_id"]))["state"] == "expired"
    assert (await shop.order(second.json()["order_id"]))["terms_version"] == "b2b-2026-12-01"
    assert shop.stub.expired == [first["session_id"]]


async def test_a_pending_order_past_its_checkout_lifetime_is_expired_without_a_stripe_call(shop):
    first = (await shop.checkout()).json()
    await shop.conn.execute("ALTER TABLE region_monthly_orders DISABLE TRIGGER region_monthly_orders_guard_trg")
    await shop.conn.execute("UPDATE region_monthly_orders SET checkout_expires_at = NOW() - INTERVAL '1 minute'")
    await shop.conn.execute("ALTER TABLE region_monthly_orders ENABLE TRIGGER region_monthly_orders_guard_trg")
    second = (await shop.checkout()).json()
    assert second["order_id"] != first["order_id"] and second["session_id"] != first["session_id"]
    assert (await shop.order(first["order_id"]))["state"] == "expired" and shop.stub.expired == []


# --- two purchases of the same scope --------------------------------------------


async def test_deliberate_later_purchases_of_the_same_scope_are_new_orders(shop):
    first_order, first_session = await shop.buy(kind="single", first_month="2026-09", event_id="evt_first")
    second = await shop.checkout(kind="single", first_month="2026-10")
    assert second.status_code == 200
    assert second.json()["order_id"] != first_order and second.json()["session_id"] != first_session
    assert second.json()["reused"] is False
    keys = [kw["idempotency_key"] for name, kw in shop.stub.calls if name == "session.create"]
    assert len(set(keys)) == 2
    assert (await shop.pay(second.json()["session_id"], event_id="evt_second")).status_code == 200
    rows = await shop.conn.fetch("SELECT state FROM region_monthly_orders")
    assert [r["state"] for r in rows] == ["paid", "paid"] and await shop.count("region_monthly_entitlements") == 2


async def test_months_the_account_already_holds_are_refused_before_payment(shop):
    await shop.buy()  # May to October
    creates = shop.stub.creates
    for overrides in ({"kind": "single", "first_month": "2026-10"}, {"kind": "single", "first_month": "2026-05"},
                      {"kind": "six", "first_month": "2026-04"}, {"kind": "twelve", "first_month": "2026-04",
                                                                   "accept_future_months": True}):
        response = await shop.checkout(**overrides)
        assert response.status_code == 409, overrides
        assert response.json()["detail"]["code"] == "months_already_held"
        assert "already holds" in response.json()["detail"]["message"] and response.json()["detail"]["months"]
    assert shop.stub.creates == creates
    assert await shop.count("region_monthly_orders") == 1

    # Months next to it, another service, another region and another account are all fine.
    assert (await shop.checkout(kind="single", first_month="2026-04")).status_code == 200
    assert (await shop.checkout(kind="single", first_month="2026-10", service="home-care")).status_code == 200
    assert (await shop.checkout(kind="single", first_month="2026-10", region="South East")).status_code == 200
    shop.as_user("b")
    assert (await shop.checkout(kind="single", first_month="2026-10")).status_code == 200


async def test_the_months_of_a_refunded_order_can_be_bought_again(shop):
    _order, session = await shop.buy()
    assert (await shop.checkout(kind="single", first_month="2026-10")).status_code == 409
    assert (await shop.refund(session, event_id="evt_refund_again")).status_code == 200
    again = await shop.checkout(kind="single", first_month="2026-10")
    assert again.status_code == 200 and again.json()["price_pence"] == 4900


async def test_two_accounts_can_buy_the_same_scope_and_each_sees_only_their_own(shop):
    order_a, _ = await shop.buy(event_id="evt_a")
    shop.as_user("b")
    order_b, _ = await shop.buy(event_id="evt_b")
    assert order_a != order_b
    assert await shop.conn.fetchval("SELECT count(*) FROM region_monthly_orders WHERE state = 'paid'") == 2
    assert await shop.count("region_monthly_entitlements") == 12
    assert (await shop.download(order_b, "2026-10", "csv")).status_code == 200
    assert (await shop.download(order_a, "2026-10", "csv")).status_code == 404
    shop.as_user("a")
    assert (await shop.download(order_a, "2026-10", "csv")).status_code == 200
    assert (await shop.download(order_b, "2026-10", "csv")).status_code == 404
    first = (await shop.download(order_a, "2026-10", "csv")).content
    shop.as_user("b")
    assert (await shop.download(order_b, "2026-10", "csv")).content == first  # the same build gives the same bytes


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
    assert await shop.count("region_monthly_entitlements") == 0 and "session.retrieve" not in shop.stub.gateway_calls


async def test_replayed_event_creates_no_second_entitlement(shop):
    order_id, session_id = await shop.buy(event_id="evt_replay")
    before = await shop.entitlements()
    again = await shop.pay(session_id, event_id="evt_replay")
    assert again.status_code == 200
    after = await shop.entitlements()
    assert [tuple(r) for r in before] == [tuple(r) for r in after] and len(after) == 6
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'region_monthly.order.paid' AND target_id = $1", order_id) == 1
    assert await shop.conn.fetchval("SELECT count(*) FROM stripe_processed_events WHERE event_id = 'evt_replay'") == 1


async def test_a_different_event_for_an_already_paid_session_creates_nothing_more(shop):
    order_id, session_id = await shop.buy(event_id="evt_one")
    again = await shop.webhook(completed_event(
        shop.stub, session_id, event_id="evt_two", event_type="checkout.session.async_payment_succeeded"))
    assert again.status_code == 200
    assert await shop.count("region_monthly_entitlements") == 6
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'region_monthly.order.paid' AND target_id = $1", order_id) == 1


@pytest.mark.parametrize(
    "tamper",
    ["amount", "currency", "status_other", "line_item", "metadata_months", "metadata_region", "metadata_kind",
     "metadata_user", "no_acceptance", "other_terms", "paid_a_cheaper_kind"],
)
async def test_a_payment_that_does_not_match_the_pinned_order_is_refused_and_grants_nothing(shop, tamper):
    created = (await shop.checkout()).json()
    session_id = created["session_id"]
    meta = shop.stub.sessions[session_id]["metadata"]
    if tamper == "amount":
        shop.stub.amount_total = 4900
    elif tamper == "paid_a_cheaper_kind":
        shop.stub.amount_total = 24500 - 1
    elif tamper == "currency":
        shop.stub.currency = "usd"
    elif tamper == "status_other":
        shop.stub.payment_status = "no_payment_required"
    elif tamper == "line_item":
        shop.stub.sessions[session_id]["line_items"] = [{"price": PRICE_IDS["single"], "quantity": 1}]
    elif tamper == "metadata_months":
        meta["months"] = "2026-04,2026-05,2026-06,2026-07,2026-08,2026-09"
    elif tamper == "metadata_region":
        meta["region"] = "East"
    elif tamper == "metadata_kind":
        meta["kind"] = "single"
    elif tamper == "metadata_user":
        meta["user_id"] = "999999"
    elif tamper == "no_acceptance":
        await shop.conn.execute("ALTER TABLE b2b_contract_acceptances DISABLE TRIGGER trg_b2b_contract_acceptances_immutable")
        await shop.conn.execute("ALTER TABLE region_monthly_orders DISABLE TRIGGER region_monthly_orders_guard_trg")
        await shop.conn.execute("UPDATE region_monthly_orders SET contract_acceptance_id = NULL")
        await shop.conn.execute("DELETE FROM b2b_contract_acceptances")
    elif tamper == "other_terms":
        await shop.conn.execute("ALTER TABLE b2b_contract_acceptances DISABLE TRIGGER trg_b2b_contract_acceptances_immutable")
        await shop.conn.execute("UPDATE b2b_contract_acceptances SET terms_version = 'b2b-other'")
    response = await shop.pay(session_id, event_id="evt_tamper")
    assert response.status_code == 500
    order = await shop.order(created["order_id"])
    assert order["state"] == "pending_payment" and order["stripe_payment_intent_id"] is None
    assert await shop.count("region_monthly_entitlements") == 0 and await shop.count("stripe_processed_events") == 0


async def test_a_delayed_payment_method_is_paid_by_the_later_event(shop):
    created = (await shop.checkout()).json()
    shop.stub.payment_status = "unpaid"
    pending = await shop.pay(created["session_id"], event_id="evt_unpaid")
    assert pending.status_code == 200
    assert (await shop.order(created["order_id"]))["state"] == "pending_payment"
    assert await shop.count("region_monthly_entitlements") == 0
    shop.stub.payment_status = "paid"
    done = await shop.webhook(completed_event(
        shop.stub, created["session_id"], event_id="evt_later", event_type="checkout.session.async_payment_succeeded"))
    assert done.status_code == 200
    assert (await shop.order(created["order_id"]))["state"] == "paid" and await shop.count("region_monthly_entitlements") == 6


async def test_an_order_paid_after_its_session_expired_locally_is_still_granted_once(shop):
    created = (await shop.checkout()).json()
    await shop.conn.execute("UPDATE region_monthly_orders SET state = 'expired'")
    assert (await shop.pay(created["session_id"], event_id="evt_late")).status_code == 200
    assert (await shop.order(created["order_id"]))["state"] == "paid" and await shop.count("region_monthly_entitlements") == 6


async def test_a_second_payment_for_months_the_account_already_holds_is_granted_and_flagged_for_the_owner(shop):
    first = (await shop.checkout(kind="single", first_month="2026-10")).json()
    # A second checkout for the same month cannot be started once the first is paid; this simulates both
    # sessions being payable at once by taking the first order out of the way before the second is made.
    await shop.conn.execute("UPDATE region_monthly_orders SET state = 'expired'")
    second = (await shop.checkout(kind="single", first_month="2026-10")).json()
    assert (await shop.pay(second["session_id"], event_id="evt_second")).status_code == 200
    assert (await shop.pay(first["session_id"], event_id="evt_first")).status_code == 200
    assert await shop.count("region_monthly_entitlements") == 2  # both payments are honoured
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'region_monthly.order.overlap_paid'") == 1


# --- interruption between payment and entitlement ------------------------------------


async def test_a_failure_after_payment_leaves_it_paid_and_visible_and_redelivery_finishes_it_once(shop, monkeypatch):
    created = (await shop.checkout()).json()
    real = service._insert_entitlements

    async def broken(*_args, **_kwargs):
        raise RuntimeError("the database fell over")

    monkeypatch.setattr(service, "_insert_entitlements", broken)
    failed = await shop.pay(created["session_id"], event_id="evt_flaky")
    assert failed.status_code == 500  # Stripe will redeliver

    order = await shop.order(created["order_id"])
    assert order["state"] == "paid" and order["entitlement_attempts"] == 1
    assert "the database fell over" in order["last_error"]
    assert order["stripe_payment_intent_id"] == shop.stub.payment_intent_for(created["session_id"])
    assert order["paid_at"] is not None and await shop.count("region_monthly_entitlements") == 0
    assert await shop.count("stripe_processed_events") == 0
    blocked = await shop.download(created["order_id"], "2026-05", "csv")
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "access_being_set_up"
    view = (await shop.status(created["order_id"])).json()
    assert view["state"] == "paid" and {m["availability"] for m in view["months"]} == {"being_set_up"}

    monkeypatch.setattr(service, "_insert_entitlements", real)
    redelivered = await shop.pay(created["session_id"], event_id="evt_flaky")
    assert redelivered.status_code == 200
    order = await shop.order(created["order_id"])
    assert order["state"] == "paid" and order["last_error"] is None
    assert await shop.count("region_monthly_entitlements") == 6
    assert await shop.conn.fetchval("SELECT count(*) FROM audit_log WHERE action = 'region_monthly.order.paid'") == 1
    assert (await shop.pay(created["session_id"], event_id="evt_flaky")).status_code == 200
    assert await shop.count("region_monthly_entitlements") == 6
    assert (await shop.download(created["order_id"], "2026-05", "pdf")).status_code == 200


async def test_the_retry_command_finishes_a_paid_order_exactly_once(shop, monkeypatch, fresh_db):
    from tools.retry_region_monthly_entitlements import _run

    created = (await shop.checkout()).json()
    real = service._insert_entitlements

    async def broken(*_args, **_kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(service, "_insert_entitlements", broken)
    assert (await shop.pay(created["session_id"], event_id="evt_retry")).status_code == 500
    monkeypatch.setattr(service, "_insert_entitlements", real)

    dry = await _run(fresh_db, apply=False, limit=10)
    assert [(item["order_id"], item["result"]) for item in dry] == [(created["order_id"], "would_grant")]
    assert await shop.count("region_monthly_entitlements") == 0

    done = await _run(fresh_db, apply=True, limit=10)
    assert [(item["order_id"], item["result"]) for item in done] == [(created["order_id"], "granted")]
    assert await _run(fresh_db, apply=True, limit=10) == []
    assert await shop.count("region_monthly_entitlements") == 6
    # Stripe's later redelivery of the original event finds the order done and creates nothing more.
    assert (await shop.pay(created["session_id"], event_id="evt_retry")).status_code == 200
    assert await shop.count("region_monthly_entitlements") == 6
    assert await shop.conn.fetchval("SELECT count(*) FROM audit_log WHERE action = 'region_monthly.order.paid'") == 1


async def test_the_retry_command_records_a_failing_attempt_and_leaves_the_order_paid(shop, monkeypatch, fresh_db):
    from tools.retry_region_monthly_entitlements import _run

    created = (await shop.checkout()).json()

    async def broken(*_args, **_kwargs):
        raise RuntimeError("still broken")

    monkeypatch.setattr(service, "_insert_entitlements", broken)
    for _attempt in range(2):
        assert (await shop.pay(created["session_id"], event_id="evt_cap")).status_code == 500
    assert (await shop.order(created["order_id"]))["entitlement_attempts"] == 2
    failing = await _run(fresh_db, apply=True, limit=10)
    assert [item["result"] for item in failing] == ["failed"]
    order = await shop.order(created["order_id"])
    assert order["state"] == "paid" and order["entitlement_attempts"] == 3 and "still broken" in order["last_error"]
    assert await shop.count("region_monthly_entitlements") == 0


# --- entitlement per month, including a future month -----------------------------------


async def test_a_future_month_is_downloadable_only_after_its_build_exists(shop):
    order_id, _ = await shop.buy(first_month="2026-09", accept_future_months=True)
    assert [row["period_month"] for row in await shop.entitlements(order_id)] == months(d(2026, 9), 6)  # all six from payment

    view = (await shop.status(order_id)).json()
    assert [(m["month"], m["availability"]) for m in view["months"]] == [
        ("2026-09", "available"), ("2026-10", "available"), ("2026-11", "will_be_available"),
        ("2026-12", "will_be_available"), ("2027-01", "will_be_available"), ("2027-02", "will_be_available")]
    november = view["months"][2]
    assert november["was_future_at_purchase"] and november["available_from"] == "2026-12-07"
    assert november["text"] == "Will be available on 7 December 2026." and november["build_version"] is None
    assert (await shop.download(order_id, "2026-10", "csv")).status_code == 200

    early = await shop.download(order_id, "2026-11", "csv")
    assert early.status_code == 409
    assert early.json()["detail"] == {
        "code": "month_not_available_yet", "message": "November 2026 will be available on 7 December 2026.",
        "available_from": "2026-12-07"}

    # The build appears: the month is downloadable from that moment, and the next one still is not.
    await add_build(shop.conn, d(2026, 11))
    november_csv = await shop.download(order_id, "2026-11", "csv")
    assert november_csv.status_code == 200 and november_csv.headers["x-build-version"] == "1"
    assert {row["period_month"] for row in csv_rows(november_csv.content)} == {"2026-11"}
    assert (await shop.download(order_id, "2026-12", "csv")).status_code == 409
    view = (await shop.status(order_id)).json()
    assert [m["availability"] for m in view["months"][:4]] == ["available", "available", "available", "will_be_available"]

    # Its day passes with no build: the month is reported as not built, with the date it was due.
    shop.set_now(datetime(2027, 1, 8, 9, 0, tzinfo=UTC))
    late = await shop.download(order_id, "2026-12", "pdf")
    assert late.status_code == 409 and late.json()["detail"]["code"] == "month_not_built"
    assert late.json()["detail"]["available_from"] == "2027-01-07"
    assert (await shop.status(order_id)).json()["months"][3]["availability"] == "not_built"

    # A correction is a new version; the latest is served and says which version it is.
    v1 = november_csv.content
    await add_build(shop.conn, d(2026, 11), bump=5, correction="test correction")
    v2 = await shop.download(order_id, "2026-11", "csv")
    assert v2.status_code == 200 and v2.headers["x-build-version"] == "2" and v2.content != v1
    assert {row["build_version"] for row in csv_rows(v2.content)} == {"2"}


async def test_access_is_per_purchased_month_and_a_month_outside_the_order_is_a_404(shop):
    order_id, _ = await shop.buy(kind="single", first_month="2026-10")
    assert [row["period_month"] for row in await shop.entitlements(order_id)] == [d(2026, 10)]
    assert (await shop.download(order_id, "2026-10", "csv")).status_code == 200
    unknown = await shop.download("00000000-0000-4000-8000-000000000000", "2026-10", "csv")
    for month in ("2026-09", "2026-11", "2025-10", "2026-13", "not-a-month", "2026-1", "2026-10-01"):
        response = await shop.download(order_id, month, "csv")
        assert response.status_code == 404 and response.json() == unknown.json(), month


# --- the download ----------------------------------------------------------------

async def test_download_bytes_are_stable_and_carry_the_whole_build(shop):
    order_id, _ = await shop.buy()
    build = await shop.conn.fetchrow(
        "SELECT * FROM region_monthly_builds WHERE region = 'London' AND service_slug IS NULL AND period_month = '2026-07-01'")
    first = await shop.download(order_id, "2026-07", "csv")
    second = await shop.download(order_id, "2026-07", "csv")
    assert first.status_code == 200 and first.content == second.content
    assert first.headers["x-content-sha256"] == hashlib.sha256(first.content).hexdigest()
    assert first.headers["x-build-content-sha256"] == build["content_sha256"]
    pdf_one, pdf_two = (await shop.download(order_id, "2026-07", "pdf")).content, (await shop.download(order_id, "2026-07", "pdf")).content
    assert pdf_one == pdf_two

    rows = csv_rows(first.content)
    for column, expected in {
        "report": "Region Monthly", "region": "London", "service": "All services", "period_month": "2026-07",
        "build_version": "1", "built_at": render.iso_utc(build["built_at"]),
        "data_cutoff": render.iso_utc(build["built_from_data_cutoff"]), "content_sha256": build["content_sha256"],
    }.items():
        assert {row[column] for row in rows} == {expected}, column
    assert [row["text"] for row in rows if row["row_type"] == "limit"][:8] == list(rm.LIMITS)
    figures = {(row["metric"], row["breakdown"]): row for row in rows if row["row_type"] == "figure"}
    assert figures[("new_registrations", "")]["value"] == str(build_row(d(2026, 7))["new_registrations"])
    assert figures[("ratings_published", "Total")]["value"] == "5"
    assert figures[("closures_observed", "")]["value"] == "" and figures[("closures_observed", "")]["coverage_status"] == "not_captured_before"
    text = pdf_text(pdf_one).replace("\n", " ")
    assert "July 2026" in text and build["content_sha256"] in text.replace(" ", "") and "Build version: 1" in text
    for limit in rm.LIMITS:
        assert limit[:50] in text

    # A different month's bytes differ; the same month for the service build differs from the regional one.
    other = (await shop.download(order_id, "2026-08", "csv")).content
    assert other != first.content


async def test_a_service_purchase_serves_the_service_build_not_the_regional_one(shop):
    regional, _ = await shop.buy(event_id="evt_region", kind="single", first_month="2026-10")
    shop.as_user("b")
    service_order, _ = await shop.buy(event_id="evt_service", kind="single", first_month="2026-10", service="home-care")
    shop.as_user("a")
    rows = csv_rows((await shop.download(regional, "2026-10", "csv")).content)
    shop.as_user("b")
    service_rows = csv_rows((await shop.download(service_order, "2026-10", "csv")).content)
    assert {r["service"] for r in rows} == {"All services"} and {r["service"] for r in service_rows} == {"Home Care"}
    assert {r["service_slug"] for r in service_rows} == {"home-care"}
    assert {r["content_sha256"] for r in rows} != {r["content_sha256"] for r in service_rows}


async def test_a_build_that_no_longer_matches_its_hash_is_never_served(shop):
    order_id, _ = await shop.buy()
    await shop.conn.execute("ALTER TABLE region_monthly_builds DISABLE TRIGGER region_monthly_builds_immutable_row")
    await shop.conn.execute(
        "UPDATE region_monthly_builds SET metrics = jsonb_set(metrics, '{new_registrations}', '999') "
        "WHERE region = 'London' AND service_slug IS NULL AND period_month = '2026-06-01'")
    await shop.conn.execute("ALTER TABLE region_monthly_builds ENABLE TRIGGER region_monthly_builds_immutable_row")
    bad = await shop.download(order_id, "2026-06", "csv")
    assert bad.status_code == 500 and "could not be served" in bad.json()["detail"]
    assert (await shop.download(order_id, "2026-07", "csv")).status_code == 200


async def test_another_account_gets_the_same_404_as_an_unknown_order(shop):
    order_id, _ = await shop.buy()
    shop.as_user("b")
    other = await shop.download(order_id, "2026-10", "csv")
    unknown = await shop.download("00000000-0000-4000-8000-000000000000", "2026-10", "csv")
    malformed = await shop.download("not-a-uuid", "2026-10", "csv")
    assert other.status_code == unknown.status_code == malformed.status_code == 404
    assert other.json() == unknown.json() == malformed.json()
    other_status = await shop.status(order_id)
    assert other_status.status_code == 404 and other_status.json() == unknown.json()
    shop.as_user("a")
    assert (await shop.download(order_id, "2026-10", "csv")).status_code == 200


async def test_unpaid_and_expired_orders_are_refused_and_an_unknown_format_is_a_422(shop):
    created = (await shop.checkout()).json()
    assert (await shop.download(created["order_id"], "2026-10", "pdf")).status_code == 402
    await shop.conn.execute("UPDATE region_monthly_orders SET state = 'expired'")
    expired = await shop.download(created["order_id"], "2026-10", "pdf")
    assert expired.status_code == 402 and expired.json()["detail"]["code"] == "order_not_paid"
    assert (await shop.download(created["order_id"], "2026-10", "xml")).status_code == 422
    assert (await shop.status(created["order_id"])).json()["state"] == "expired"


# --- refunds ---------------------------------------------------------------------


async def test_a_full_refund_revokes_access_and_changes_state_only(shop):
    order_id, session_id = await shop.buy()
    before = await shop.order(order_id)
    before_rows = [tuple(r) for r in await shop.entitlements(order_id)]
    assert (await shop.download(order_id, "2026-10", "csv")).status_code == 200

    event = refund_event(shop.stub.payment_intent_for(session_id), event_id="evt_refund", amount=24500)
    assert (await shop.webhook(event)).status_code == 200
    after = await shop.order(order_id)
    assert after["state"] == "refunded" and after["refunded_at"] is not None
    assert {key for key in before.keys() if before[key] != after[key]} == {"state", "refunded_at", "updated_at"}
    assert [tuple(r) for r in await shop.entitlements(order_id)] == before_rows  # the entitlements are untouched
    for month in MAY_TO_OCT:
        for fmt in ("csv", "pdf"):
            refused = await shop.download(order_id, month, fmt)
            assert refused.status_code == 410 and refused.json()["detail"]["code"] == "order_refunded"
            assert "refunded" in refused.json()["detail"]["message"]
    view = (await shop.status(order_id)).json()
    assert view["state"] == "refunded" and {m["availability"] for m in view["months"]} == {"refunded"}
    assert (await shop.webhook(event)).status_code == 200  # replay: nothing more happens
    assert await shop.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE action = 'region_monthly.order.refund' AND target_id = $1", order_id) == 1
    # A replayed payment event cannot bring a refunded order back.
    assert (await shop.pay(session_id, event_id="evt_late_pay")).status_code == 200
    assert (await shop.order(order_id))["state"] == "refunded" and len(await shop.entitlements(order_id)) == 6


async def test_a_partial_refund_changes_nothing_here(shop):
    order_id, session_id = await shop.buy()
    assert (await shop.refund(session_id, event_id="evt_partial", full=False)).status_code == 200
    assert (await shop.order(order_id))["state"] == "paid"
    assert (await shop.download(order_id, "2026-10", "csv")).status_code == 200
    assert await shop.conn.fetchval(
        "SELECT metadata->>'fully_refunded' FROM audit_log WHERE action = 'billing.charge.refund' "
        "AND metadata->>'payment_intent' = $1", shop.stub.payment_intent_for(session_id)) == "false"


async def test_a_refund_that_arrives_before_the_payment_event_means_nothing_is_granted(shop):
    created = (await shop.checkout()).json()
    intent = shop.stub.payment_intent_for(created["session_id"])
    assert (await shop.refund(created["session_id"], event_id="evt_refund_first")).status_code == 200
    assert (await shop.order(created["order_id"]))["state"] == "pending_payment"  # no order is bound to it yet
    assert (await shop.pay(created["session_id"], event_id="evt_pay_after")).status_code == 200
    order = await shop.order(created["order_id"])
    assert order["state"] == "refunded" and order["stripe_payment_intent_id"] == intent
    assert await shop.count("region_monthly_entitlements") == 0
    assert (await shop.download(created["order_id"], "2026-10", "csv")).status_code == 410


# --- the database keeps the purchase immutable ----------------------------------------


async def test_the_database_refuses_to_rewrite_a_paid_order_or_its_entitlements(shop):
    order_id, _ = await shop.buy()
    c = shop.conn
    for statement in (
        "UPDATE region_monthly_orders SET months = ARRAY['2026-05-01'::date]",
        "UPDATE region_monthly_orders SET months = ARRAY['2026-04-01', '2026-05-01', '2026-06-01', '2026-07-01', "
        "'2026-08-01', '2026-09-01']::date[]",
        "UPDATE region_monthly_orders SET price_pence = 1",
        "UPDATE region_monthly_orders SET kind = 'single', month_count = 1",
        "UPDATE region_monthly_orders SET region = 'East'",
        "UPDATE region_monthly_orders SET service_slug = 'home-care'",
        "UPDATE region_monthly_orders SET terms_version = 'other'",
        "UPDATE region_monthly_orders SET terms_sha256 = repeat('b', 64)",
        "UPDATE region_monthly_orders SET stripe_price_id = 'price_other'",
        "UPDATE region_monthly_orders SET future_months = ARRAY['2026-10-01']::date[], "
        "future_available_from = ARRAY['2026-11-07']::date[], future_months_accepted = true",
        "UPDATE region_monthly_orders SET user_id = user_id + 1",
        "UPDATE region_monthly_orders SET stripe_payment_intent_id = 'pi_other'",
        "UPDATE region_monthly_orders SET amount_total = 1",
        "UPDATE region_monthly_orders SET paid_at = NOW() - INTERVAL '1 day'",
        "UPDATE region_monthly_orders SET state = 'pending_payment'",
        "UPDATE region_monthly_orders SET state = 'expired'",
        "DELETE FROM region_monthly_orders",
        "TRUNCATE region_monthly_orders CASCADE",
        "UPDATE region_monthly_entitlements SET period_month = '2026-04-01'",
        "UPDATE region_monthly_entitlements SET order_id = order_id",
        "DELETE FROM region_monthly_entitlements",
        "TRUNCATE region_monthly_entitlements",
    ):
        with pytest.raises(asyncpg.PostgresError):
            await c.execute(statement)
    assert (await shop.order(order_id))["state"] == "paid" and len(await shop.entitlements(order_id)) == 6
    # A refund is the only allowed move, it changes state only, and it cannot be undone.
    await c.execute("UPDATE region_monthly_orders SET state = 'refunded', refunded_at = NOW()")
    for statement in ("UPDATE region_monthly_orders SET state = 'paid'", "UPDATE region_monthly_orders SET state = 'expired'",
                      "UPDATE region_monthly_orders SET refunded_at = NOW() + INTERVAL '1 day'"):
        with pytest.raises(asyncpg.PostgresError):
            await c.execute(statement)


async def test_the_database_allows_an_entitlement_only_for_a_month_of_a_paid_order(shop):
    created = (await shop.checkout()).json()
    c = shop.conn
    with pytest.raises(asyncpg.PostgresError):  # the order is not paid
        await c.execute("INSERT INTO region_monthly_entitlements (order_id, period_month) VALUES ($1::uuid, '2026-05-01')",
                        created["order_id"])
    await shop.pay(created["session_id"], event_id="evt_ok")
    with pytest.raises(asyncpg.PostgresError):  # not a month of this order
        await c.execute("INSERT INTO region_monthly_entitlements (order_id, period_month) VALUES ($1::uuid, '2026-04-01')",
                        created["order_id"])
    with pytest.raises(asyncpg.UniqueViolationError):  # one per order and month
        await c.execute("INSERT INTO region_monthly_entitlements (order_id, period_month) VALUES ($1::uuid, '2026-05-01')",
                        created["order_id"])
    with pytest.raises(asyncpg.PostgresError):  # not the first day of a month
        await c.execute("INSERT INTO region_monthly_entitlements (order_id, period_month) VALUES ($1::uuid, '2026-05-02')",
                        created["order_id"])


async def _insert_order(conn, user_id: int, **overrides):
    values = {
        "user_id": user_id, "customer_email": "buyer.a@example.com", "region": "London", "service_slug": None,
        "kind": "single", "month_count": 1, "months": [d(2026, 10)], "future_months": [], "future_available_from": [],
        "future_months_accepted": False, "state": "pending_payment", "price_pence": 4900, "currency": "gbp",
        "stripe_price_id": "price_x", "terms_version": "t", "terms_sha256": "a" * 64,
        "checkout_expires_at": datetime(2030, 1, 1, tzinfo=UTC),
    }
    values.update(overrides)
    columns = ", ".join(values)
    marks = ", ".join(f"${i + 1}" for i in range(len(values)))
    return await conn.fetchval(f"INSERT INTO region_monthly_orders ({columns}) VALUES ({marks}) RETURNING id", *values.values())


async def test_the_database_refuses_a_malformed_order(shop):
    c, user = shop.conn, shop.users["a"]["user_id"]
    assert await _insert_order(c, shop.users["b"]["user_id"])  # a well-formed order goes in
    cases = {
        "not consecutive": dict(kind="six", month_count=6, months=months(d(2026, 4), 5) + [d(2026, 10)]),
        "not first of month": dict(months=[d(2026, 10, 2)]),
        "wrong count": dict(kind="six", month_count=6, months=months(d(2026, 4), 3)),
        "kind and count disagree": dict(kind="six", month_count=1),
        "born paid": dict(state="paid", stripe_payment_intent_id="pi_x", paid_at=datetime(2026, 11, 1, tzinfo=UTC)),
        "future not accepted": dict(future_months=[d(2026, 10)], future_available_from=[d(2026, 11, 7)]),
        "future not in months": dict(future_months=[d(2026, 12)], future_available_from=[d(2027, 1, 7)],
                                     future_months_accepted=True),
        "future dates mismatch": dict(future_months=[d(2026, 10)], future_available_from=[], future_months_accepted=True),
        "wales": dict(region="Wales"), "bad slug": dict(service_slug="Not A Slug"), "bad kind": dict(kind="weekly"),
        "bad currency": dict(currency="usd"), "no price": dict(price_pence=0), "uppercase email": dict(customer_email="A@B.C"),
    }
    for name, overrides in cases.items():
        with pytest.raises(asyncpg.PostgresError) as refused:
            await _insert_order(c, user, **overrides)
        assert not isinstance(refused.value, asyncpg.UniqueViolationError), name  # refused for its own fault
    assert await shop.count("region_monthly_orders") == 1


# --- the migration ---------------------------------------------------------------------


async def test_migration_077_applies_cleanly_and_its_down_script_reverses_it(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        applied = await apply_full_schema(conn)
        assert applied.index("077_region_monthly_orders.sql") == applied.index("076_region_monthly_builds.sql") + 1
        tables = {"region_monthly_orders", "region_monthly_entitlements"}
        present = {r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
        assert tables <= present and "region_monthly_builds" in present
        down = (Path(MIGRATIONS_DIR) / "down" / "077_region_monthly_orders.down.sql").read_text(encoding="utf-8")
        await conn.execute(down)
        present = {r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
        assert not tables & present and "region_monthly_builds" in present  # stage 1 is untouched
        functions = {r["proname"] for r in await conn.fetch(
            "SELECT proname FROM pg_proc WHERE proname LIKE 'region_monthly_orders%' OR proname LIKE 'region_monthly_entitlements%'")}
        assert functions == set()
        up = (Path(MIGRATIONS_DIR) / "077_region_monthly_orders.sql").read_text(encoding="utf-8")
        await conn.execute(up)
        await conn.execute(up)  # idempotent
        assert tables <= {r["tablename"] for r in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    finally:
        await conn.close()
