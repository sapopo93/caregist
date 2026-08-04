"""Tests for Stripe checkout tier routing."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.config import settings
from api.middleware.auth import validate_billing_identity
from api.routers.billing import (
    PRICE_TO_TIER,
    CheckoutRequest,
    ProfileCheckoutRequest,
    _handle_checkout_completed,
    create_checkout,
    create_profile_checkout,
    router,
)


def test_all_account_billing_routes_use_non_metering_identity_dependency():
    guarded_paths = {
        "/api/v1/billing/checkout",
        "/api/v1/billing/profile-checkout",
        "/api/v1/billing/subscription",
    }
    routes = {route.path: route for route in router.routes if route.path in guarded_paths}

    assert routes.keys() == guarded_paths
    for route in routes.values():
        assert any(
            dependency.call is validate_billing_identity
            for dependency in route.dependant.dependencies
        )


@pytest.mark.asyncio
async def test_free_tier_checkout_is_rejected_without_stripe_or_db(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")

    with pytest.raises(HTTPException) as exc:
        await create_checkout(
            CheckoutRequest(email="alice@example.com", tier="free"),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True},
        )

    assert exc.value.status_code == 422
    assert "does not require checkout" in exc.value.detail


@pytest.mark.asyncio
async def test_checkout_accepts_display_alias_and_uses_canonical_stripe_tier(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_alerts_pro", "price_alerts")
    monkeypatch.setattr(settings, "stripe_price_starter", "price_starter")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")
    monkeypatch.setattr(settings, "stripe_price_business", "price_business")
    monkeypatch.setattr(settings, "app_url", "https://caregist.co.uk")

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

    created_session = SimpleNamespace(url="https://checkout.stripe.test/session", id="cs_test_123")

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create", return_value=created_session) as create_session:
        result = await create_checkout(
            CheckoutRequest(email="alice@example.com", tier=" Data Pro "),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True},
        )

    assert result["checkout_url"] == "https://checkout.stripe.test/session"
    create_session.assert_called_once()
    kwargs = create_session.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_pro", "quantity": 1}]
    assert kwargs["mode"] == "subscription"
    assert "automatic_tax" not in kwargs
    assert all("tax_rates" not in item for item in kwargs["line_items"])
    assert kwargs["metadata"]["tier"] == "pro"
    assert kwargs["metadata"]["price_id"] == "price_pro"
    assert kwargs["idempotency_key"] == "caregist-checkout-user-42-pro-0"
    audit_args = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_args[1] == "billing.checkout.create"
    assert "price_pro" not in repr(audit_args)


@pytest.mark.asyncio
async def test_alerts_pro_safe_local_purchase_contract_activates_exact_selected_tier(monkeypatch):
    """Exercise checkout creation through entitlement activation without network or live data."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_alerts_pro", "price_alerts")
    monkeypatch.setattr(settings, "app_url", "https://preview.caregist.test")
    monkeypatch.setitem(PRICE_TO_TIER, "price_alerts", "alerts-pro")

    checkout_conn = AsyncMock()
    checkout_conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_test"},
            None,
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield checkout_conn

    created_session = SimpleNamespace(url="https://checkout.stripe.test/alerts", id="cs_alerts_test")
    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create", return_value=created_session) as create_session:
        checkout_result = await create_checkout(
            CheckoutRequest(email="alice@example.com", tier="alerts-pro"),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True},
        )

    assert checkout_result["stripe_mode"] == "test"
    checkout_metadata = create_session.call_args.kwargs["metadata"]
    assert checkout_metadata == {
        "user_id": "42",
        "tier": "alerts-pro",
        "extra_seats": "0",
        "price_id": "price_alerts",
    }

    entitlement_conn = AsyncMock()
    await _handle_checkout_completed(
        entitlement_conn,
        {
            "metadata": checkout_metadata,
            "subscription": "sub_alerts_test",
            "customer": "cus_test",
        },
    )

    subscription_insert = next(
        call.args for call in entitlement_conn.execute.await_args_list
        if "INSERT INTO subscriptions" in call.args[0]
    )
    assert subscription_insert[1:6] == (
        42,
        "sub_alerts_test",
        "price_alerts",
        "alerts-pro",
        "active",
    )


@pytest.mark.asyncio
async def test_checkout_rejects_another_account_email_without_enumerating(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"})

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                CheckoutRequest(email="bob@example.com", tier="pro"),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True},
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Checkout is only available for the authenticated account."
    assert "bob@example.com" not in exc.value.detail
    assert "not found" not in exc.value.detail.lower()
    create_session.assert_not_called()


@pytest.mark.parametrize("stale_tier", ["starter", "pro"])
@pytest.mark.asyncio
async def test_business_seat_update_keeps_business_when_client_tier_is_stale(monkeypatch, stale_tier):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_starter", "price_starter")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")
    monkeypatch.setattr(settings, "stripe_price_business", "price_business")
    monkeypatch.setattr(settings, "stripe_price_pro_seat", "price_team_seat")
    monkeypatch.setitem(PRICE_TO_TIER, "price_starter", "starter")
    monkeypatch.setitem(PRICE_TO_TIER, "price_pro", "pro")
    monkeypatch.setitem(PRICE_TO_TIER, "price_business", "business")
    monkeypatch.setitem(PRICE_TO_TIER, "price_team_seat", "pro-seat")

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            {"tier": "business", "status": "active", "stripe_subscription_id": "sub_business", "extra_seats": 0},
        ]
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    subscription = {
        "items": {
            "data": [
                {"id": "si_base", "price": {"id": "price_business"}, "quantity": 1},
            ]
        }
    }

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Subscription.retrieve", return_value=subscription), \
        patch("api.routers.billing.stripe.Subscription.modify") as modify:
        result = await create_checkout(
            CheckoutRequest(email="alice@example.com", tier=stale_tier, extra_seats=2),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True, "tier": stale_tier},
        )

    assert result == {"updated": True, "tier": "business", "extra_seats": 2}
    modify.assert_called_once()
    kwargs = modify.call_args.kwargs
    assert kwargs["items"] == [
        {"id": "si_base", "price": "price_business", "quantity": 1},
        {"price": "price_team_seat", "quantity": 2},
    ]
    assert kwargs["metadata"]["tier"] == "business"
    persist_call = next(call.args for call in conn.execute.await_args_list if "INSERT INTO subscriptions" in call.args[0])
    assert persist_call[4] == "business"
    assert persist_call[6] == 10
    assert persist_call[7] == 2
    assert persist_call[8] == 12


@pytest.mark.asyncio
async def test_business_seat_update_does_not_require_configured_business_price(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_starter", "price_starter")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro")
    monkeypatch.setattr(settings, "stripe_price_business", "")
    monkeypatch.setattr(settings, "stripe_price_pro_seat", "price_team_seat")
    monkeypatch.setitem(PRICE_TO_TIER, "price_starter", "starter")
    monkeypatch.setitem(PRICE_TO_TIER, "price_pro", "pro")
    monkeypatch.delitem(PRICE_TO_TIER, "price_business", raising=False)
    monkeypatch.setitem(PRICE_TO_TIER, "price_team_seat", "pro-seat")

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            {
                "tier": "business",
                "status": "active",
                "stripe_subscription_id": "sub_business",
                "stripe_price_id": "price_live_business",
                "extra_seats": 0,
            },
        ]
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    subscription = {
        "items": {
            "data": [
                {"id": "si_base", "price": {"id": "price_live_business"}, "quantity": 1},
            ]
        }
    }

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Subscription.retrieve", return_value=subscription), \
         patch("api.routers.billing.stripe.Subscription.modify") as modify:
        result = await create_checkout(
            CheckoutRequest(email="alice@example.com", tier="business", extra_seats=1),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True, "tier": "business"},
        )

    assert result == {"updated": True, "tier": "business", "extra_seats": 1}
    modify.assert_called_once()
    assert modify.call_args.kwargs["items"] == [{"price": "price_team_seat", "quantity": 1}]
    persist_call = next(call.args for call in conn.execute.await_args_list if "INSERT INTO subscriptions" in call.args[0])
    assert persist_call[3] == "price_live_business"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "alice@example.com", "tier": "pro", "price_id": "price_business"},
        {"email": "alice@example.com", "tier": "starter", "price": "price_business"},
        {"email": "alice@example.com", "tier": "starter", "amount": 0},
        {"email": "alice@example.com", "tier": "starter", "billing_cadence": "yearly"},
        {"email": "alice@example.com", "tier": "starter", "mode": "payment"},
    ],
)
def test_checkout_rejects_client_supplied_pricing_or_cadence_fields(payload):
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)


def test_profile_checkout_rejects_client_supplied_price():
    with pytest.raises(ValidationError):
        ProfileCheckoutRequest.model_validate(
            {
                "slug": "claimed-provider",
                "tier": "enhanced",
                "email": "alice@example.com",
                "price_id": "price_profile_sponsored",
            }
        )


@pytest.mark.asyncio
async def test_checkout_rejects_unauthenticated_request(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")

    with pytest.raises(HTTPException) as exc:
        await create_checkout(
            CheckoutRequest(email="alice@example.com", tier="pro"),
            {},
        )

    assert exc.value.status_code == 401
    assert "Authenticated user account required" in exc.value.detail


@pytest.mark.asyncio
async def test_profile_checkout_rejects_another_account_email_without_enumerating(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_profile_enhanced", "price_profile_enhanced")

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"})

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_profile_checkout(
                ProfileCheckoutRequest(slug="claimed-provider", tier="enhanced", email="bob@example.com"),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True},
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Checkout is only available for the authenticated account."
    assert "bob@example.com" not in exc.value.detail
    assert "not found" not in exc.value.detail.lower()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_profile_checkout_requires_verified_email_before_database_or_stripe(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")

    with patch("api.routers.billing.get_connection") as get_connection, \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_profile_checkout(
                ProfileCheckoutRequest(slug="claimed-provider", tier="enhanced", email="alice@example.com"),
                {"user_id": 42, "email": "alice@example.com", "is_verified": False},
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Verify your email before starting billing."
    get_connection.assert_not_called()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_profile_checkout_requires_approved_claim_owned_by_authenticated_user(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_profile_enhanced", "price_profile_enhanced")

    connections = []
    for fetchrow_result in (
        {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
        {"id": "LOC123", "is_claimed": True, "profile_tier": "claimed"},
        None,
    ):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        connections.append(conn)

    @asynccontextmanager
    async def mock_get_connection():
        yield connections.pop(0)

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Customer.create") as create_customer, \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_profile_checkout(
                ProfileCheckoutRequest(slug="claimed-provider", tier="enhanced", email="alice@example.com"),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True},
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "You don't have an approved claim for this provider."
    create_customer.assert_not_called()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_profile_checkout_rejects_second_paid_subscription(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_profile_sponsored", "price_profile_sponsored")

    connections = []
    for fetchrow_result in (
        {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
        {
            "id": "LOC123",
            "is_claimed": True,
            "profile_tier": "enhanced",
            "profile_subscription_id": "sub_existing",
        },
        {"id": 88},
    ):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        connections.append(conn)

    @asynccontextmanager
    async def mock_get_connection():
        yield connections.pop(0)

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_profile_checkout(
                ProfileCheckoutRequest(slug="claimed-provider", tier="sponsored", email="alice@example.com"),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True},
            )

    assert exc.value.status_code == 409
    assert "already has a paid listing subscription" in exc.value.detail
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_profile_checkout_safe_test_mode_journey_uses_owned_claim_and_server_price(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_profile_enhanced", "price_profile_enhanced")
    monkeypatch.setattr(settings, "app_url", "https://preview.caregist.test")

    connections = []
    for fetchrow_result in (
        {"id": 42, "email": "alice@example.com", "stripe_customer_id": None},
        {
            "id": "LOC123",
            "is_claimed": True,
            "profile_tier": "claimed",
            "profile_subscription_id": None,
        },
        {"id": 88},
        None,
        None,
    ):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=fetchrow_result)
        connections.append(conn)

    @asynccontextmanager
    async def mock_get_connection():
        yield connections.pop(0)

    created_session = SimpleNamespace(url="https://checkout.stripe.test/profile", id="cs_profile_test")
    created_customer = SimpleNamespace(id="cus_profile_test")
    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Customer.create", return_value=created_customer) as create_customer, \
         patch("api.routers.billing.stripe.checkout.Session.create", return_value=created_session) as create_session:
        result = await create_profile_checkout(
            ProfileCheckoutRequest(slug="claimed-provider", tier="enhanced", email="alice@example.com"),
            {"user_id": 42, "email": "alice@example.com", "is_verified": True},
        )

    assert result == {
        "checkout_url": "https://checkout.stripe.test/profile",
        "session_id": "cs_profile_test",
        "stripe_mode": "test",
    }
    assert create_customer.call_args.kwargs == {
        "email": "alice@example.com",
        "idempotency_key": "caregist-customer-user-42",
    }
    checkout = create_session.call_args.kwargs
    assert checkout["line_items"] == [{"price": "price_profile_enhanced", "quantity": 1}]
    assert "automatic_tax" not in checkout
    assert "tax_rates" not in checkout["line_items"][0]
    assert checkout["metadata"] == {
        "type": "profile",
        "slug": "claimed-provider",
        "provider_id": "LOC123",
        "tier": "enhanced",
    }
    assert checkout["idempotency_key"] == "caregist-profile-checkout-LOC123-enhanced"
