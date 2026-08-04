"""Adversarial regression tests for Stripe billing state reconciliation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.config import settings
from api.routers import billing


class _Transaction:
    def __init__(self):
        self.exit_type = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.exit_type = exc_type
        return False


def _transactional(conn: AsyncMock) -> AsyncMock:
    conn.transaction = lambda: _Transaction()
    return conn


class _WebhookConn:
    def transaction(self):
        return _Transaction()

    async def fetchval(self, _query, event_id):
        return event_id

    async def execute(self, *_args):
        return "UPDATE 1"


def _webhook_request():
    from starlette.requests import Request

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
async def test_subscription_update_webhook_uses_current_retrieved_state(monkeypatch):
    """A delayed event must not overwrite newer Stripe state carried by retrieve()."""
    conn = _WebhookConn()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    delivered = {
        "id": "evt_old_active",
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_123", "status": "active"}},
    }
    authoritative = {
        "id": "sub_123",
        "status": "past_due",
        "items": {"data": [{"price": {"id": "price_pro"}, "quantity": 1}]},
    }
    handler = AsyncMock()
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(billing, "get_connection", mock_get_connection)
    monkeypatch.setattr(billing.stripe.Webhook, "construct_event", lambda *_args: delivered)
    monkeypatch.setattr(billing.stripe.Subscription, "retrieve", lambda _id: authoritative)
    monkeypatch.setattr(billing, "_handle_subscription_updated", handler)

    assert await billing.stripe_webhook(_webhook_request()) == {"status": "ok"}
    handler.assert_awaited_once_with(conn, authoritative)


@pytest.mark.asyncio
async def test_checkout_completion_persists_authoritative_non_entitled_status(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_pro", "pro")
    monkeypatch.setattr(
        billing.stripe.Subscription,
        "retrieve",
        lambda _id: {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "past_due",
            "items": {"data": [{"id": "si_base", "price": {"id": "price_pro"}, "quantity": 1}]},
        },
    )

    await billing._handle_checkout_completed(
        conn,
        {
            "id": "cs_123",
            "payment_status": "paid",
            "customer": "cus_123",
            "subscription": "sub_123",
            "metadata": {
                "user_id": "42",
                "tier": "pro",
                "extra_seats": "0",
                "price_id": "price_pro",
            },
        },
    )

    persisted = next(
        call.args
        for call in conn.execute.await_args_list
        if "INSERT INTO subscriptions" in call.args[0]
    )
    assert persisted[4:6] == ("pro", "past_due")
    entitlement_update = next(
        call.args
        for call in conn.execute.await_args_list
        if "UPDATE api_keys" in call.args[0]
    )
    assert "status IN ('active', 'trialing')" in entitlement_update[0]


@pytest.mark.asyncio
async def test_existing_account_change_rejects_subscription_customer_mismatch(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")

    connections = []
    for row in (
        {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_owned"},
        {
            "tier": "starter",
            "status": "active",
            "stripe_subscription_id": "sub_123",
            "stripe_price_id": "price_starter",
            "extra_seats": 0,
        },
    ):
        conn = _transactional(AsyncMock())
        conn.fetchrow = AsyncMock(return_value=row)
        connections.append(conn)

    @asynccontextmanager
    async def mock_get_connection():
        yield connections.pop(0)

    with patch.object(billing, "get_connection", mock_get_connection), patch.object(
        billing.stripe.Subscription,
        "retrieve",
        return_value={"customer": "cus_someone_else", "status": "active", "items": {"data": []}},
    ), patch.object(billing.stripe.Subscription, "modify") as modify:
        with pytest.raises(HTTPException) as exc:
            await billing.create_checkout(
                billing.CheckoutRequest(email="alice@example.com", tier="pro"),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True},
            )

    assert exc.value.status_code == 409
    assert "authenticated billing customer" in exc.value.detail
    modify.assert_not_called()


@pytest.mark.asyncio
async def test_existing_provider_change_rejects_subscription_customer_mismatch(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_profile_sponsored", "price_sponsored")

    connections = []
    for row in (
        {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_owned"},
        {
            "id": "LOC123",
            "is_claimed": True,
            "profile_tier": "enhanced",
            "profile_subscription_id": "sub_profile",
        },
        {"id": 88},
    ):
        conn = _transactional(AsyncMock())
        conn.fetchrow = AsyncMock(return_value=row)
        connections.append(conn)

    @asynccontextmanager
    async def mock_get_connection():
        yield connections.pop(0)

    with patch.object(billing, "get_connection", mock_get_connection), patch.object(
        billing.stripe.Subscription,
        "retrieve",
        return_value={"customer": "cus_someone_else", "status": "active", "items": {"data": []}},
    ), patch.object(billing.stripe.Subscription, "modify") as modify:
        with pytest.raises(HTTPException) as exc:
            await billing.create_profile_checkout(
                billing.ProfileCheckoutRequest(
                    slug="claimed-provider", tier="sponsored", email="alice@example.com"
                ),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True},
            )

    assert exc.value.status_code == 409
    assert "different billing customer" in exc.value.detail
    modify.assert_not_called()


@pytest.mark.asyncio
async def test_price_rotation_replaces_persisted_old_base_item_by_id(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_new_pro")
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_new_pro", "pro")
    monkeypatch.delitem(billing.PRICE_TO_TIER, "price_old_starter", raising=False)

    connections = []
    for row in (
        {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
        {
            "tier": "starter",
            "status": "active",
            "stripe_subscription_id": "sub_123",
            "stripe_price_id": "price_old_starter",
            "extra_seats": 0,
        },
        None,
        None,
    ):
        conn = _transactional(AsyncMock())
        conn.fetchrow = AsyncMock(return_value=row)
        connections.append(conn)

    @asynccontextmanager
    async def mock_get_connection():
        yield connections.pop(0)

    source = {
        "id": "sub_123",
        "customer": "cus_123",
        "status": "active",
        "items": {
            "data": [
                {"id": "si_old_base", "price": {"id": "price_old_starter"}, "quantity": 1},
            ]
        },
    }
    changed = {
        "id": "sub_123",
        "customer": "cus_123",
        "status": "active",
        "items": {
            "data": [
                {"id": "si_old_base", "price": {"id": "price_new_pro"}, "quantity": 1},
            ]
        },
    }

    async def reserve(*_args, **kwargs):
        return {"id": "op_rotation", "request_fingerprint": kwargs["fingerprint"]}

    async def noop(*_args, **_kwargs):
        return None

    with patch.object(billing, "get_connection", mock_get_connection), patch.object(
        billing, "_reserve_billing_operation", reserve
    ), patch.object(billing, "_record_operation_object", noop), patch.object(
        billing, "_complete_operation", noop
    ), patch.object(billing.stripe.Subscription, "retrieve", return_value=source), patch.object(
        billing.stripe.Subscription, "modify", return_value=changed
    ) as modify:
        result = await billing.create_checkout(
            billing.CheckoutRequest(email="alice@example.com", tier="pro"),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True},
        )

    assert result["tier"] == "pro"
    assert modify.call_args.kwargs["items"] == [
        {"id": "si_old_base", "price": "price_new_pro", "quantity": 1}
    ]


@pytest.mark.asyncio
async def test_account_plan_finalization_rolls_back_as_one_unit_on_audit_failure(monkeypatch):
    """A post-Stripe local failure must leave the transaction to roll everything back."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_new_pro")
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_new_pro", "pro")

    rows = [
        {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
        {
            "tier": "starter",
            "status": "active",
            "stripe_subscription_id": "sub_123",
            "stripe_price_id": "price_old_starter",
            "extra_seats": 0,
        },
        None,
        None,
    ]
    connections = []
    for row in rows:
        conn = _transactional(AsyncMock())
        conn.fetchrow = AsyncMock(return_value=row)
        connections.append(conn)
    final_transaction = _Transaction()
    connections[-1].transaction = lambda: final_transaction

    @asynccontextmanager
    async def mock_get_connection():
        yield connections.pop(0)

    source = {
        "customer": "cus_123",
        "status": "active",
        "items": {"data": [{"id": "si_base", "price": {"id": "price_old_starter"}, "quantity": 1}]},
    }
    changed = {
        "customer": "cus_123",
        "status": "active",
        "items": {"data": [{"id": "si_base", "price": {"id": "price_new_pro"}, "quantity": 1}]},
    }

    async def reserve(*_args, **_kwargs):
        return {"id": "op_atomic"}

    async def noop(*_args, **_kwargs):
        return None

    complete = AsyncMock()
    with patch.object(billing, "get_connection", mock_get_connection), patch.object(
        billing, "_reserve_billing_operation", reserve
    ), patch.object(billing, "_record_operation_object", noop), patch.object(
        billing, "_complete_operation", complete
    ), patch.object(billing.stripe.Subscription, "retrieve", return_value=source), patch.object(
        billing.stripe.Subscription, "modify", return_value=changed
    ), patch.object(
        billing, "write_audit_log", AsyncMock(side_effect=RuntimeError("audit unavailable"))
    ):
        with pytest.raises(RuntimeError, match="audit unavailable"):
            await billing.create_checkout(
                billing.CheckoutRequest(email="alice@example.com", tier="pro"),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True},
            )

    assert final_transaction.exit_type is RuntimeError
    complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_inflight_account_checkout_survives_price_rotation(monkeypatch):
    """A paid session keeps its approved historical Price after deployment rotates config."""
    conn = AsyncMock()
    monkeypatch.delitem(billing.PRICE_TO_TIER, "price_old_pro", raising=False)
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_new_pro", "pro")
    monkeypatch.setattr(
        billing.stripe.Subscription,
        "retrieve",
        lambda _id: {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "items": {
                "data": [
                    {"id": "si_base", "price": {"id": "price_old_pro"}, "quantity": 1},
                ]
            },
        },
    )

    await billing._handle_checkout_completed(
        conn,
        {
            "id": "cs_123",
            "payment_status": "paid",
            "customer": "cus_123",
            "subscription": "sub_123",
            "metadata": {
                "user_id": "42",
                "tier": "pro",
                "extra_seats": "0",
                "price_id": "price_old_pro",
            },
        },
    )

    persisted = next(
        call.args
        for call in conn.execute.await_args_list
        if "INSERT INTO subscriptions" in call.args[0]
    )
    assert persisted[3:6] == ("price_old_pro", "pro", "active")


@pytest.mark.asyncio
async def test_inflight_account_checkout_with_seats_survives_price_rotation(monkeypatch):
    """Historical base and seat Prices remain verifiable for an already-paid session."""
    conn = AsyncMock()
    monkeypatch.delitem(billing.PRICE_TO_TIER, "price_old_pro", raising=False)
    monkeypatch.delitem(billing.PRICE_TO_TIER, "price_old_seat", raising=False)
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_new_pro", "pro")
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_new_seat", "pro-seat")
    monkeypatch.setattr(
        billing.stripe.Subscription,
        "retrieve",
        lambda _id: {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "items": {
                "data": [
                    {"id": "si_base", "price": {"id": "price_old_pro"}, "quantity": 1},
                    {"id": "si_seat", "price": {"id": "price_old_seat"}, "quantity": 2},
                ]
            },
        },
    )

    await billing._handle_checkout_completed(
        conn,
        {
            "id": "cs_123",
            "payment_status": "paid",
            "customer": "cus_123",
            "subscription": "sub_123",
            "metadata": {
                "user_id": "42",
                "tier": "pro",
                "extra_seats": "2",
                "price_id": "price_old_pro",
                "seat_price_id": "price_old_seat",
            },
        },
    )

    persisted = next(
        call.args
        for call in conn.execute.await_args_list
        if "INSERT INTO subscriptions" in call.args[0]
    )
    assert persisted[3:8] == ("price_old_pro", "pro", "active", 3, 2)


@pytest.mark.asyncio
async def test_inflight_provider_checkout_survives_price_rotation(monkeypatch):
    """Provider Checkout metadata preserves the historical approved Price mapping."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    monkeypatch.delitem(billing.PRICE_TO_PROFILE_TIER, "price_old_enhanced", raising=False)
    monkeypatch.setitem(billing.PRICE_TO_PROFILE_TIER, "price_new_enhanced", "enhanced")
    monkeypatch.setattr(
        billing.stripe.Subscription,
        "retrieve",
        lambda _id: {
            "id": "sub_profile",
            "customer": "cus_123",
            "status": "active",
            "items": {
                "data": [
                    {"id": "si_profile", "price": {"id": "price_old_enhanced"}, "quantity": 1},
                ]
            },
        },
    )

    await billing._handle_profile_checkout_completed(
        conn,
        {
            "id": "cs_profile",
            "payment_status": "paid",
            "customer": "cus_123",
            "subscription": "sub_profile",
            "metadata": {
                "type": "profile",
                "slug": "claimed-provider",
                "provider_id": "LOC123",
                "tier": "enhanced",
                "price_id": "price_old_enhanced",
            },
        },
    )

    profile_update = next(
        call.args
        for call in conn.execute.await_args_list
        if "UPDATE care_providers" in call.args[0]
    )
    assert profile_update[1:] == ("enhanced", "sub_profile", "claimed-provider", "LOC123")


@pytest.mark.asyncio
async def test_pending_operation_reuses_same_fingerprint_and_rejects_a_different_request():
    pending = {
        "id": "op_pending",
        "request_fingerprint": "same",
        "stripe_object_id": "cs_123",
        "stripe_object_url": "https://checkout.stripe.test/cs_123",
        "expires_at": None,
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[None, pending, None, pending])

    recovered = await billing._reserve_billing_operation(
        conn,
        owner_type="account",
        owner_id="42",
        operation_type="checkout",
        fingerprint="same",
        lifetime=timedelta(minutes=31),
    )
    assert recovered["stripe_object_id"] == "cs_123"

    with pytest.raises(HTTPException) as exc:
        await billing._reserve_billing_operation(
            conn,
            owner_type="account",
            owner_id="42",
            operation_type="checkout",
            fingerprint="different",
            lifetime=timedelta(minutes=31),
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_checkout_reuses_reserved_session_without_creating_another(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_starter", "price_starter")
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            None,
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    async def reserve(*_args, **_kwargs):
        return {
            "id": "op_pending",
            "stripe_object_id": "cs_123",
            "stripe_object_url": "https://checkout.stripe.test/cs_123",
        }

    with patch.object(billing, "get_connection", mock_get_connection), patch.object(
        billing, "_reserve_billing_operation", reserve
    ), patch.object(billing.stripe.checkout.Session, "create") as create_session:
        result = await billing.create_checkout(
            billing.CheckoutRequest(email="alice@example.com", tier="starter"),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True},
        )

    assert result["reused"] is True
    assert result["session_id"] == "cs_123"
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_billing_portal_requires_owned_customer_before_calling_stripe(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"stripe_customer_id": None})

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch.object(billing, "get_connection", mock_get_connection), patch.object(
        billing.stripe.billing_portal.Session, "create"
    ) as create_portal:
        with pytest.raises(HTTPException) as exc:
            await billing.create_billing_portal({"user_id": 42, "is_verified": True})

    assert exc.value.status_code == 409
    create_portal.assert_not_called()
