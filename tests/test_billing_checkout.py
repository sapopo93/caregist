"""Tests for Stripe checkout tier routing."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.config import settings
from api.routers.billing import PRICE_TO_TIER, CheckoutRequest, ProfileCheckoutRequest, create_checkout, create_profile_checkout


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
    assert kwargs["metadata"]["tier"] == "pro"
    assert kwargs["metadata"]["price_id"] == "price_pro"
    audit_args = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_args[1] == "billing.checkout.create"
    assert "price_pro" not in repr(audit_args)


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
