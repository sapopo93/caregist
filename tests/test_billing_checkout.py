"""Tests for Stripe checkout tier routing."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from api.config import settings
from api.routers.billing import (
    CheckoutRequest,
    ProfileCheckoutRequest,
    cancel_subscription,
    create_checkout,
    create_profile_checkout,
)

TERMS_VERSION = "b2b-2026-08-02"
TERMS_SHA256 = "a" * 64


def _request() -> Request:
    return Request({"type": "http", "headers": [(b"user-agent", b"pytest")], "client": ("203.0.113.10", 443)})


def _checkout(**values) -> CheckoutRequest:
    return CheckoutRequest(terms_version=TERMS_VERSION, business_use_confirmed=True, **values)


def _profile(**values) -> ProfileCheckoutRequest:
    return ProfileCheckoutRequest(terms_version=TERMS_VERSION, business_use_confirmed=True, **values)


def _browser_auth(**values) -> dict:
    return {
        "user_id": 42,
        "email": "alice@example.com",
        "is_verified": True,
        "auth_method": "session",
        **values,
    }


@pytest.fixture(autouse=True)
def _enable_checkout_for_endpoint_unit_tests():
    with patch("api.routers.billing.settings.billing_checkout_enabled", True), \
         patch("api.routers.billing.settings.b2b_terms_version", TERMS_VERSION), \
         patch("api.routers.billing.settings.b2b_terms_sha256", TERMS_SHA256):
        yield


@pytest.mark.asyncio
async def test_checkout_fails_closed_before_any_billing_mutation():
    with patch("api.routers.billing.settings.billing_checkout_enabled", False), \
         patch("api.routers.billing.get_connection") as get_connection, \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                _checkout(email="alice@example.com", tier="starter"),
                _request(),
                _browser_auth(),
            )

    assert exc.value.status_code == 503
    assert "Human Gate" in exc.value.detail
    get_connection.assert_not_called()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_rejects_stale_terms_before_database_or_stripe():
    with patch("api.routers.billing.get_connection") as get_connection, \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                CheckoutRequest(
                    email="alice@example.com",
                    tier="starter",
                    terms_version="superseded-version",
                    business_use_confirmed=True,
                ),
                _request(),
                _browser_auth(),
            )

    assert exc.value.status_code == 409
    get_connection.assert_not_called()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_free_tier_checkout_is_rejected_without_stripe_or_db(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")

    with pytest.raises(HTTPException) as exc:
        await create_checkout(
            _checkout(email="alice@example.com", tier="free"),
            _request(),
            _browser_auth(),
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
            _checkout(email="alice@example.com", tier=" Data Pro "),
            _request(),
            _browser_auth(),
        )

    assert result["checkout_url"] == "https://checkout.stripe.test/session"
    create_session.assert_called_once()
    kwargs = create_session.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_pro", "quantity": 1}]
    assert kwargs["mode"] == "subscription"
    assert "payment_method_types" not in kwargs
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
                _checkout(email="bob@example.com", tier="pro"),
                _request(),
                _browser_auth(),
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Checkout is only available for the authenticated account."
    assert "bob@example.com" not in exc.value.detail
    assert "not found" not in exc.value.detail.lower()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_profile_checkout_uses_dynamic_payment_methods(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_profile_enhanced", "price_profile_enhanced")
    monkeypatch.setattr(settings, "app_url", "https://caregist.co.uk")

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            {"id": "LOC123", "is_claimed": True, "profile_tier": "claimed", "profile_subscription_id": None},
            {"id": 1},
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    created_session = SimpleNamespace(url="https://checkout.stripe.test/profile", id="cs_profile_123")

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create", return_value=created_session) as create_session:
        result = await create_profile_checkout(
            _profile(slug="claimed-provider", tier="enhanced", email="alice@example.com"),
            _request(),
            _browser_auth(),
        )

    assert result["checkout_url"] == "https://checkout.stripe.test/profile"
    kwargs = create_session.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_profile_enhanced", "quantity": 1}]
    assert kwargs["mode"] == "subscription"
    assert "payment_method_types" not in kwargs


@pytest.mark.asyncio
async def test_existing_subscription_change_is_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            {
                "tier": "business",
                "status": "active",
                "stripe_subscription_id": "sub_business",
                "stripe_price_id": "price_business",
                "extra_seats": 0,
            },
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Subscription.modify") as modify:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                _checkout(email="alice@example.com", tier="pro", extra_seats=2),
                _request(),
                _browser_auth(tier="pro"),
            )

    assert exc.value.status_code == 409
    assert "Contact support" in exc.value.detail
    modify.assert_not_called()


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


def test_paid_checkout_requires_explicit_business_acceptance_fields():
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate({"email": "alice@example.com", "tier": "starter"})
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(
            {
                "email": "alice@example.com",
                "tier": "starter",
                "terms_version": TERMS_VERSION,
                "business_use_confirmed": False,
            }
        )


@pytest.mark.asyncio
async def test_cancel_subscription_sets_period_end_with_stable_idempotency_key(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    conn = AsyncMock()
    conn.transaction = Mock(return_value=AsyncMock())
    conn.fetchrow.return_value = {
        "stripe_subscription_id": "sub_123",
        "cancel_at_period_end": False,
        "current_period_end": None,
        "status": "active",
        "stripe_customer_id": "cus_123",
    }

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch(
             "api.routers.billing.stripe.Subscription.retrieve",
             return_value={"customer": "cus_123", "status": "active", "cancel_at_period_end": False},
         ), \
         patch(
             "api.routers.billing.stripe.Subscription.modify",
             return_value={"current_period_end": 1788220800},
         ) as modify:
        result = await cancel_subscription(_browser_auth())

    assert result["cancel_at_period_end"] is True
    assert result["current_period_end"].startswith("2026-")
    modify.assert_called_once_with(
        "sub_123",
        cancel_at_period_end=True,
        idempotency_key="caregist-cancel-42-sub_123",
    )
    assert any("cancel_at_period_end = TRUE" in call.args[0] for call in conn.execute.await_args_list)


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
            _checkout(email="alice@example.com", tier="pro"),
            _request(),
            {},
        )

    assert exc.value.status_code == 401
    assert "Authenticated user account required" in exc.value.detail


@pytest.mark.asyncio
async def test_checkout_rejects_team_api_key_before_database_or_stripe(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    with patch("api.routers.billing.get_connection") as get_connection, \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                _checkout(email="alice@example.com", tier="pro"),
                _request(),
                {"user_id": 42, "email": "alice@example.com", "is_verified": True, "auth_method": "api_key"},
            )

    assert exc.value.status_code == 403
    get_connection.assert_not_called()
    create_session.assert_not_called()


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
                _profile(slug="claimed-provider", tier="enhanced", email="bob@example.com"),
                _request(),
                _browser_auth(),
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Checkout is only available for the authenticated account."
    assert "bob@example.com" not in exc.value.detail
    assert "not found" not in exc.value.detail.lower()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_profile_checkout_requires_approved_claim_ownership(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_profile_enhanced", "price_profile_enhanced")

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            {"id": "LOC123", "is_claimed": True, "profile_tier": "claimed", "profile_subscription_id": None},
            None,
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_profile_checkout(
                _profile(slug="claimed-provider", tier="enhanced", email="alice@example.com"),
                _request(),
                _browser_auth(),
            )

    assert exc.value.status_code == 403
    assert "approved claim" in exc.value.detail
    create_session.assert_not_called()
