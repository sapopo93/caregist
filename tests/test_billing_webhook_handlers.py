"""Focused tests for Stripe webhook handler failure semantics."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from api.routers import billing


class _Conn:
    async def fetchrow(self, *args, **kwargs):
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
async def test_stripe_event_deduplication_covers_delayed_redelivery_window(monkeypatch):
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
    assert "INTERVAL '30 days'" in cleanup_query


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
async def test_alerts_pro_checkout_completion_activates_paid_entitlements(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts", "alerts-pro")

    await billing._handle_checkout_completed(
        conn,
        {
            "metadata": {
                "user_id": "123",
                "tier": "alerts-pro",
                "extra_seats": "0",
                "price_id": "price_alerts",
            },
            "subscription": "sub_alerts",
            "customer": "cus_alerts",
        },
    )

    subscription_insert = next(
        call.args for call in conn.execute.await_args_list
        if "INSERT INTO subscriptions" in call.args[0]
    )
    assert subscription_insert[1:6] == (123, "sub_alerts", "price_alerts", "alerts-pro", "active")
    assert subscription_insert[6:10] == (1, 0, 1, 0)
    api_key_update = next(
        call.args for call in conn.execute.await_args_list
        if "UPDATE api_keys SET tier" in call.args[0]
    )
    assert api_key_update[1] == "alerts-pro"
    assert api_key_update[3] == 123


@pytest.mark.asyncio
async def test_alerts_pro_subscription_update_preserves_entitlements(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"user_id": 123})
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts", "alerts-pro")

    await billing._handle_subscription_updated(
        conn,
        {
            "id": "sub_alerts",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_alerts"}, "quantity": 1}]},
        },
    )

    subscription_insert = next(
        call.args for call in conn.execute.await_args_list
        if "INSERT INTO subscriptions" in call.args[0]
    )
    assert subscription_insert[1:6] == (123, "sub_alerts", "price_alerts", "alerts-pro", "active")


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
@pytest.mark.parametrize(
    "subscription_status",
    ["past_due", "incomplete", "incomplete_expired", "unpaid", "paused", "canceled"],
)
async def test_profile_subscription_update_downgrades_non_entitled_status_to_claimed(
    subscription_status,
):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": "LOC123", "slug": "claimed-provider"},
        ]
    )

    await billing._handle_subscription_updated(
        conn,
        {
            "id": "sub_profile",
            "status": subscription_status,
            "items": {
                "data": [
                    {"price": {"id": "price_unknown_or_stale"}, "quantity": 1},
                ]
            },
        },
    )

    profile_update = next(
        call.args for call in conn.execute.await_args_list
        if "UPDATE care_providers SET profile_tier = 'claimed'" in call.args[0]
    )
    assert profile_update[1:] == ("LOC123", "sub_profile")


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
