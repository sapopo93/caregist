"""Focused tests for Stripe webhook handler failure semantics."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from api.routers import billing

TERMS_SHA256 = "a" * 64


class _Conn:
    async def fetchrow(self, query, *args, **kwargs):
        if "b2b_contract_acceptances" in query:
            return {
                "user_id": 123,
                "terms_version": "b2b-2026-08-02",
                "terms_sha256": TERMS_SHA256,
                "business_use_confirmed": True,
            }
        return {"user_id": 123}

    async def execute(self, *args, **kwargs):
        return "UPDATE 1"


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _WebhookConn:
    def __init__(self):
        self.delivery_count = 0
        self.executed_queries: list[tuple] = []

    def transaction(self):
        return _Transaction()

    async def fetchval(self, query, event_id):
        self.delivery_count += 1
        return event_id if self.delivery_count == 1 else None

    async def execute(self, *args, **kwargs):
        self.executed_queries.append(args)
        return "DELETE 0"


def _webhook_request() -> Request:
    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

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


def test_profile_tier_normalizes_legacy_premium_to_enhanced():
    assert billing._normalize_profile_tier("premium") == "enhanced"
    assert billing._normalize_profile_tier("provider_pro") == "enhanced"


@pytest.mark.asyncio
async def test_duplicate_stripe_event_changes_entitlement_once(monkeypatch):
    conn = _WebhookConn()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    event = {
        "id": "evt_checkout_once",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_once"}},
    }
    handler = AsyncMock()
    monkeypatch.setattr(billing.settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(billing.settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(billing, "get_connection", mock_get_connection)
    monkeypatch.setattr(billing.stripe.Webhook, "construct_event", lambda *args: event)
    monkeypatch.setattr(billing, "_handle_checkout_completed", handler)

    first = await billing.stripe_webhook(_webhook_request())
    duplicate = await billing.stripe_webhook(_webhook_request())

    assert first == {"status": "ok"}
    assert duplicate == {"status": "ok"}
    handler.assert_awaited_once_with(conn, {"id": "cs_test_once"})


@pytest.mark.asyncio
async def test_stripe_event_deduplication_covers_seven_day_redelivery_window(monkeypatch):
    conn = _WebhookConn()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    event = {
        "id": "evt_delayed_retry",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_retry"}},
    }
    monkeypatch.setattr(billing.settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(billing.settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(billing, "get_connection", mock_get_connection)
    monkeypatch.setattr(billing.stripe.Webhook, "construct_event", lambda *args: event)
    monkeypatch.setattr(billing, "_handle_checkout_completed", AsyncMock())

    await billing.stripe_webhook(_webhook_request())

    cleanup_query = next(
        call[0] for call in conn.executed_queries
        if "DELETE FROM stripe_processed_events" in call[0]
    )
    assert "INTERVAL '7 days'" in cleanup_query


@pytest.mark.asyncio
async def test_checkout_completed_missing_user_id_raises_for_retry():
    with pytest.raises(RuntimeError, match="missing user_id"):
        await billing._handle_checkout_completed(
            _Conn(),
            {
                "metadata": {"tier": "starter", "price_id": "price_starter"},
                "subscription": "sub_123",
            },
        )


@pytest.mark.asyncio
async def test_checkout_completed_accepts_alerts_pro_metadata(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts_pro", "alerts-pro")
    monkeypatch.setattr(
        billing.stripe.Subscription,
        "retrieve",
        lambda _subscription_id: {
            "customer": "cus_alerts",
            "status": "active",
            "items": {"data": [{"id": "si_alerts", "price": {"id": "price_alerts_pro"}, "quantity": 1}]},
        },
    )
    persist = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(billing, "_persist_subscription_state", persist)
    monkeypatch.setattr(billing, "write_audit_log", audit)

    await billing._handle_checkout_completed(
        _Conn(),
        {
            "id": "cs_alerts",
            "metadata": {
                "user_id": "123",
                "tier": "alerts-pro",
                "extra_seats": "0",
                "price_id": "price_alerts_pro",
                "terms_version": "b2b-2026-08-02",
                "business_use_confirmed": "true",
                "terms_sha256": TERMS_SHA256,
            },
            "subscription": "sub_alerts",
            "customer": "cus_alerts",
            "payment_status": "paid",
        },
    )

    persist.assert_awaited_once()
    assert persist.await_args.args[1:5] == (123, "sub_alerts", "alerts-pro", "active")
    assert persist.await_args.kwargs["stripe_price_id"] == "price_alerts_pro"
    audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_checkout_completed_queues_idempotent_activation_email(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_radar_regional", "radar-regional")
    monkeypatch.setattr(billing.settings, "app_url", "https://www.caregist.co.uk")
    monkeypatch.setattr(
        billing.stripe.Subscription,
        "retrieve",
        lambda _subscription_id: {
            "customer": "cus_radar",
            "status": "active",
            "items": {"data": [{"id": "si_radar", "price": {"id": "price_radar_regional"}, "quantity": 1}]},
        },
    )
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "user_id": 123,
            "terms_version": "b2b-2026-08-02",
            "terms_sha256": TERMS_SHA256,
            "business_use_confirmed": True,
        }
    )
    monkeypatch.setattr(billing, "_persist_subscription_state", AsyncMock())
    monkeypatch.setattr(billing, "write_audit_log", AsyncMock())

    await billing._handle_checkout_completed(
        conn,
        {
            "id": "cs_radar",
            "metadata": {
                "user_id": "123",
                "tier": "radar-regional",
                "extra_seats": "0",
                "price_id": "price_radar_regional",
                "terms_version": "b2b-2026-08-02",
                "business_use_confirmed": "true",
                "terms_sha256": TERMS_SHA256,
            },
            "subscription": "sub_radar",
            "customer": "cus_radar",
            "customer_details": {"email": " Alice@Example.com "},
            "payment_status": "paid",
        },
    )

    email_call = next(call.args for call in conn.execute.await_args_list if "pending_emails" in call.args[0])
    assert email_call[1] == "alice@example.com"
    assert "Radar Regional" in email_call[2]
    assert email_call[3] == "radar-subscription-activated:sub_radar"


@pytest.mark.asyncio
async def test_subscription_deleted_queues_idempotent_cancellation_email(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "user_id": 123,
            "tier": "radar-regional",
            "stripe_price_id": "price_radar_regional",
            "email": "alice@example.com",
        }
    )
    monkeypatch.setattr(billing, "_persist_subscription_state", AsyncMock())
    monkeypatch.setattr(billing, "write_audit_log", AsyncMock())

    await billing._handle_subscription_deleted(conn, {"id": "sub_radar"})

    email_call = next(call.args for call in conn.execute.await_args_list if "pending_emails" in call.args[0])
    assert email_call[1] == "alice@example.com"
    assert "returned to Free" in email_call[2]
    assert email_call[3] == "radar-subscription-canceled:sub_radar"


@pytest.mark.asyncio
async def test_checkout_completed_without_valid_payment_fails_closed(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts_pro", "alerts-pro")
    persist = AsyncMock()
    retrieve = AsyncMock()
    monkeypatch.setattr(billing, "_persist_subscription_state", persist)
    monkeypatch.setattr(billing.stripe.Subscription, "retrieve", retrieve)

    with pytest.raises(RuntimeError, match="before payment became valid"):
        await billing._handle_checkout_completed(
            _Conn(),
            {
                "id": "cs_unpaid",
                "metadata": {
                    "user_id": "123",
                    "tier": "alerts-pro",
                    "price_id": "price_alerts_pro",
                    "terms_version": "b2b-2026-08-02",
                    "terms_sha256": TERMS_SHA256,
                    "business_use_confirmed": "true",
                },
                "subscription": "sub_unpaid",
                "payment_status": "unpaid",
            },
        )

    persist.assert_not_awaited()
    retrieve.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_completed_rejects_subscription_customer_mismatch(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts_pro", "alerts-pro")
    monkeypatch.setattr(
        billing.stripe.Subscription,
        "retrieve",
        lambda _subscription_id: {"customer": "cus_other", "status": "active", "items": {"data": []}},
    )
    persist = AsyncMock()
    monkeypatch.setattr(billing, "_persist_subscription_state", persist)

    with pytest.raises(RuntimeError, match="customer mismatch"):
        await billing._handle_checkout_completed(
            _Conn(),
            {
                "id": "cs_alerts",
                "metadata": {
                    "user_id": "123",
                    "tier": "alerts-pro",
                    "price_id": "price_alerts_pro",
                    "terms_version": "b2b-2026-08-02",
                    "business_use_confirmed": "true",
                    "terms_sha256": TERMS_SHA256,
                },
                "subscription": "sub_alerts",
                "customer": "cus_alerts",
                "payment_status": "paid",
            },
        )

    persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_subscription_updated_unknown_price_raises_for_retry(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_starter", "starter")

    with pytest.raises(RuntimeError, match="cannot map base price"):
        await billing._handle_subscription_updated(
            _Conn(),
            {
                "id": "sub_123",
                "status": "active",
                "items": {
                    "data": [
                        {"price": {"id": "price_new_plan"}, "quantity": 1},
                    ],
                },
            },
        )


@pytest.mark.asyncio
async def test_subscription_updated_accepts_alerts_pro_price(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts_pro", "alerts-pro")
    persist = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(billing, "_persist_subscription_state", persist)
    monkeypatch.setattr(billing, "write_audit_log", audit)

    await billing._handle_subscription_updated(
        _Conn(),
        {
            "id": "sub_alerts",
            "status": "active",
            "items": {
                "data": [
                    {"price": {"id": "price_alerts_pro"}, "quantity": 1},
                ],
            },
        },
    )

    persist.assert_awaited_once()
    assert persist.await_args.args[1:5] == (123, "sub_alerts", "alerts-pro", "active")
    assert persist.await_args.kwargs["stripe_price_id"] == "price_alerts_pro"
    assert persist.await_args.kwargs["cancel_at_period_end"] is False
    audit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["past_due", "incomplete", "unpaid", "paused", "canceled", "unknown"])
async def test_subscription_updated_removes_entitlements_when_not_entitled(monkeypatch, status):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts_pro", "alerts-pro")
    persist = AsyncMock()
    monkeypatch.setattr(billing, "_persist_subscription_state", persist)
    monkeypatch.setattr(billing, "write_audit_log", AsyncMock())

    await billing._handle_subscription_updated(
        _Conn(),
        {
            "id": "sub_alerts",
            "status": status,
            "items": {"data": [{"price": {"id": "price_alerts_pro"}, "quantity": 1}]},
        },
    )

    assert persist.await_args.args[1:5] == (123, "sub_alerts", "free", status)
    assert persist.await_args.kwargs["extra_seats"] == 0


@pytest.mark.asyncio
async def test_profile_subscription_past_due_removes_paid_visibility(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": "LOC123", "profile_tier": "sponsored"},
        ]
    )
    audit = AsyncMock()
    monkeypatch.setattr(billing, "write_audit_log", audit)

    await billing._handle_subscription_updated(
        conn,
        {
            "id": "sub_profile",
            "status": "past_due",
            "metadata": {"type": "profile", "tier": "sponsored"},
            "items": {"data": []},
        },
    )

    update = conn.execute.await_args.args
    assert update[1:] == ("LOC123", "sub_profile")
    audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_subscription_update_reconciles_changed_plan(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": "LOC123", "slug": "claimed-provider"},
        ]
    )
    monkeypatch.setitem(billing.PRICE_TO_PROFILE_TIER, "price_profile_sponsored", "sponsored")

    await billing._handle_subscription_updated(
        conn,
        {
            "id": "sub_profile",
            "status": "active",
            "items": {
                "data": [
                    {"price": {"id": "price_profile_sponsored"}, "quantity": 1},
                ]
            },
        },
    )

    profile_update = next(
        call.args for call in conn.execute.await_args_list
        if "UPDATE care_providers SET profile_tier" in call.args[0]
    )
    assert profile_update[1:] == ("sponsored", "LOC123", "sub_profile")


@pytest.mark.asyncio
async def test_profile_subscription_update_with_unknown_price_raises_for_retry():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": "LOC123", "slug": "claimed-provider"},
        ]
    )

    with pytest.raises(RuntimeError, match="cannot map one profile price"):
        await billing._handle_subscription_updated(
            conn,
            {
                "id": "sub_profile",
                "status": "active",
                "items": {
                    "data": [
                        {"price": {"id": "price_unknown"}, "quantity": 1},
                    ]
                },
            },
        )


@pytest.mark.asyncio
async def test_profile_checkout_missing_metadata_raises_for_retry():
    with pytest.raises(RuntimeError, match="missing slug or tier"):
        await billing._handle_profile_checkout_completed(
            _Conn(),
            {
                "metadata": {"type": "profile", "slug": "provider-slug"},
                "subscription": "sub_123",
            },
        )


@pytest.mark.asyncio
async def test_profile_checkout_completed_normalizes_legacy_premium_tier(monkeypatch):
    audit = AsyncMock()
    monkeypatch.setattr(billing, "write_audit_log", audit)

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    await billing._handle_profile_checkout_completed(
        conn,
        {
            "metadata": {"type": "profile", "slug": "provider-slug", "tier": "premium"},
            "subscription": "sub_profile",
        },
    )

    execute_args = conn.execute.await_args.args
    assert execute_args[1] == "enhanced"
    assert execute_args[2] == "sub_profile"
    assert execute_args[3] == "provider-slug"
    audit.assert_awaited_once()
