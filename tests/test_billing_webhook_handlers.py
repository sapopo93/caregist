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

    def transaction(self):
        return _Transaction()

    async def fetchval(self, query, event_id):
        self.delivery_count += 1
        return event_id if self.delivery_count == 1 else None

    async def execute(self, *args, **kwargs):
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
