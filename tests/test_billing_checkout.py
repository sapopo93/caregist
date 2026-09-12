"""Tests for Stripe checkout tier routing."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from api.config import settings
from api.middleware.auth import validate_billing_identity
from api.routers import billing as billing_module
from api.routers.billing import (
    CheckoutRequest,
    ProfileCheckoutRequest,
    _require_radar_commerce_ready,
    cancel_subscription,
    create_billing_portal,
    create_checkout,
    create_profile_checkout,
    get_checkout_session_status,
    router,
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


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def _transactional(conn: AsyncMock) -> AsyncMock:
    conn.transaction = lambda: _Transaction()
    return conn


@pytest.fixture(autouse=True)
def isolate_persisted_billing_operations(monkeypatch):
    """Stub the reservation ledger so unit tests exercise routing, not storage.

    The concurrency-safe mutation ledger (billing_operations) is covered by
    its own tests; here it would otherwise require a real DB round-trip.
    """
    async def reserve(*_args, **kwargs):
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "request_fingerprint": kwargs["fingerprint"],
            "stripe_object_id": None,
            "stripe_object_url": None,
        }

    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(billing_module, "_reserve_billing_operation", reserve)
    monkeypatch.setattr(billing_module, "_record_operation_object", noop)
    monkeypatch.setattr(billing_module, "_complete_operation", noop)
    monkeypatch.setattr(billing_module, "_complete_pending_owner_operations", noop)


def test_all_billing_routes_use_non_metering_identity_dependency():
    guarded_paths = {
        "/api/v1/billing/checkout",
        "/api/v1/billing/checkout-session/{session_id}",
        "/api/v1/billing/profile-checkout",
        "/api/v1/billing/subscription",
        "/api/v1/billing/subscription/cancel",
        "/api/v1/billing/portal",
    }
    routes = {route.path: route for route in router.routes if route.path in guarded_paths}

    assert routes.keys() == guarded_paths
    for route in routes.values():
        assert any(
            dependency.call is validate_billing_identity
            for dependency in route.dependant.dependencies
        )


@pytest.mark.asyncio
async def test_radar_commerce_readiness_rejects_disabled_delivery():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), patch(
        "api.routers.billing.get_pipeline_health",
        new=AsyncMock(
            return_value={
                "commercialReadiness": {
                    "checkoutReady": True,
                    "deliveryEnabled": False,
                }
            }
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await _require_radar_commerce_ready()

    assert exc_info.value.status_code == 503
    assert "delivery activation" in exc_info.value.detail


@pytest.mark.asyncio
async def test_radar_commerce_readiness_accepts_delivery_and_evidence():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), patch(
        "api.routers.billing.get_pipeline_health",
        new=AsyncMock(
            return_value={
                "commercialReadiness": {
                    "checkoutReady": True,
                    "deliveryEnabled": True,
                }
            }
        ),
    ):
        await _require_radar_commerce_ready()


@pytest.fixture(autouse=True)
def _enable_checkout_for_endpoint_unit_tests():
    with patch("api.routers.billing.settings.billing_checkout_enabled", True), \
         patch("api.routers.billing.settings.radar_checkout_enabled", True), \
         patch("api.routers.billing.settings.radar_delivery_enabled", True), \
         patch("api.routers.billing.settings.b2b_terms_version", TERMS_VERSION), \
         patch("api.routers.billing.settings.b2b_terms_sha256", TERMS_SHA256), \
         patch("api.routers.billing._require_radar_commerce_ready", new=AsyncMock()):
        yield


@pytest.mark.asyncio
async def test_checkout_fails_closed_before_any_billing_mutation():
    with patch("api.routers.billing.settings.billing_checkout_enabled", False), \
         patch("api.routers.billing.get_connection") as get_connection, \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                _checkout(email="alice@example.com", tier="radar-regional"),
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
                    tier="radar-regional",
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
    monkeypatch.setattr(settings, "stripe_price_radar_national", "price_radar_national")
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
            _checkout(email="alice@example.com", tier=" Radar National "),
            _request(),
            _browser_auth(),
        )

    assert result["checkout_url"] == "https://checkout.stripe.test/session"
    create_session.assert_called_once()
    kwargs = create_session.call_args.kwargs
    assert kwargs["line_items"] == [{"price": "price_radar_national", "quantity": 1}]
    assert kwargs["mode"] == "subscription"
    assert "payment_method_types" not in kwargs
    assert kwargs["metadata"]["tier"] == "radar-national"
    assert kwargs["metadata"]["price_id"] == "price_radar_national"
    assert kwargs["idempotency_key"] == "caregist-checkout-00000000-0000-0000-0000-000000000001"
    audit_args = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_args[1] == "billing.checkout.create"
    assert "price_radar_national" not in repr(audit_args)


@pytest.mark.asyncio
async def test_checkout_can_use_explicit_operational_readiness_override(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_radar_regional", "price_radar_regional")
    monkeypatch.setattr(settings, "radar_checkout_require_operational_readiness", False)

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

    created_session = SimpleNamespace(url="https://checkout.stripe.test/session", id="cs_test_override")
    readiness = AsyncMock()
    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing._require_radar_commerce_ready", readiness), \
         patch("api.routers.billing.stripe.checkout.Session.create", return_value=created_session):
        result = await create_checkout(
            _checkout(email="alice@example.com", tier="radar-regional"),
            _request(),
            _browser_auth(),
        )

    assert result["session_id"] == "cs_test_override"
    readiness.assert_not_awaited()


@pytest.mark.asyncio
async def test_operational_override_cannot_bypass_disabled_delivery(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "radar_checkout_require_operational_readiness", False)
    monkeypatch.setattr(settings, "radar_delivery_enabled", False)
    get_connection = Mock()
    create_session = Mock()

    with patch("api.routers.billing.get_connection", get_connection), patch(
        "api.routers.billing.stripe.checkout.Session.create", create_session
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_checkout(
                _checkout(email="alice@example.com", tier="radar-regional"),
                _request(),
                _browser_auth(),
            )

    assert exc_info.value.status_code == 503
    assert "delivery-activation" in exc_info.value.detail
    get_connection.assert_not_called()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_return_requires_matching_stripe_and_local_entitlement(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"stripe_customer_id": "cus_123"},
            {"tier": "radar-regional", "status": "active"},
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch(
             "api.routers.billing.stripe.checkout.Session.retrieve",
             return_value={
                 "id": "cs_test_return123",
                 "customer": "cus_123",
                 "subscription": "sub_123",
                 "status": "complete",
                 "payment_status": "paid",
                 "metadata": {"user_id": "42"},
             },
         ):
        result = await get_checkout_session_status(
            "cs_test_return123",
            _browser_auth(),
        )

    assert result == {
        "checkout_status": "complete",
        "payment_status": "paid",
        "entitlement_ready": True,
        "tier": "radar-regional",
    }


@pytest.mark.asyncio
async def test_checkout_return_hides_another_accounts_session(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    conn = AsyncMock()
    conn.fetchrow.return_value = {"stripe_customer_id": "cus_123"}

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch(
             "api.routers.billing.stripe.checkout.Session.retrieve",
             return_value={
                 "id": "cs_test_other123",
                 "customer": "cus_other",
                 "subscription": "sub_other",
                 "status": "complete",
                 "payment_status": "paid",
                 "metadata": {"user_id": "99"},
             },
         ):
        with pytest.raises(HTTPException) as exc:
            await get_checkout_session_status(
                "cs_test_other123",
                _browser_auth(),
            )

    assert exc.value.status_code == 404
    assert "not found" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_checkout_rejects_another_account_email_without_enumerating(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_radar_national", "price_radar_national")

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"})

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                _checkout(email="bob@example.com", tier="radar-national"),
                _request(),
                _browser_auth(),
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Checkout is only available for the authenticated account."
    assert "bob@example.com" not in exc.value.detail
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_profile_checkout_is_retired_before_database_or_stripe():
    with patch("api.routers.billing.get_connection") as get_connection, \
         patch("api.routers.billing.stripe.checkout.Session.create") as create_session:
        with pytest.raises(HTTPException) as exc:
            await create_profile_checkout(
                _profile(slug="claimed-provider", tier="enhanced", email="alice@example.com"),
                _request(),
                _browser_auth(),
            )

    assert exc.value.status_code == 410
    get_connection.assert_not_called()
    create_session.assert_not_called()


@pytest.mark.asyncio
async def test_existing_b2b_same_plan_and_seats_is_noop(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_radar_national", "price_radar_national")

    conn = _transactional(AsyncMock())
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            {
                "tier": "radar-national",
                "status": "active",
                "stripe_subscription_id": "sub_radar_national",
                "stripe_price_id": "price_radar_national",
                "extra_seats": 0,
            },
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch(
             "api.routers.billing.stripe.Subscription.retrieve",
             return_value={
                 "customer": "cus_123",
                 "status": "active",
                 "items": {"data": [
                     {"id": "si_base", "price": {"id": "price_radar_national"}, "quantity": 1},
                 ]},
             },
         ), \
         patch("api.routers.billing.stripe.Subscription.modify") as modify, \
         patch(
             "api.routers.billing._complete_pending_owner_operations",
             new_callable=AsyncMock,
         ) as complete_pending:
        result = await create_checkout(
            _checkout(email="alice@example.com", tier="radar-national"),
            _request(),
            _browser_auth(tier="radar-national"),
        )

    assert result == {
        "updated": True,
        "tier": "radar-national",
        "extra_seats": 0,
        "unchanged": True,
    }
    modify.assert_not_called()
    assert any("INSERT INTO subscriptions" in call.args[0] for call in conn.execute.await_args_list)
    assert any("UPDATE api_keys" in call.args[0] for call in conn.execute.await_args_list)
    complete_pending.assert_awaited_once_with(
        conn,
        owner_type="account",
        owner_id="42",
        operation_type="subscription_change",
        stripe_object_id="sub_radar_national",
    )


@pytest.mark.asyncio
async def test_existing_b2b_change_revokes_stale_paid_access_when_stripe_is_past_due(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "stripe_price_radar_national", "price_radar_national")

    conn = _transactional(AsyncMock())
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"id": 42, "email": "alice@example.com", "stripe_customer_id": "cus_123"},
            {
                "tier": "radar-regional",
                "status": "active",
                "stripe_subscription_id": "sub_radar_regional",
                "stripe_price_id": "price_radar_regional",
                "extra_seats": 0,
            },
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch(
             "api.routers.billing.stripe.Subscription.retrieve",
             return_value={
                 "customer": "cus_123",
                 "status": "past_due",
                 "items": {"data": [{"id": "si_base", "price": {"id": "price_radar_regional"}, "quantity": 1}]},
             },
         ), \
         patch("api.routers.billing.stripe.Subscription.modify") as modify:
        with pytest.raises(HTTPException) as exc:
            await create_checkout(
                _checkout(email="alice@example.com", tier="radar-national"),
                _request(),
                _browser_auth(tier="radar-regional"),
            )

    assert exc.value.status_code == 409
    modify.assert_not_called()
    assert any("UPDATE api_keys" in call.args[0] for call in conn.execute.await_args_list)


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "alice@example.com", "tier": "radar-national", "price_id": "price_other"},
        {"email": "alice@example.com", "tier": "radar-regional", "price": "price_other"},
        {"email": "alice@example.com", "tier": "radar-regional", "amount": 0},
        {"email": "alice@example.com", "tier": "radar-regional", "billing_cadence": "yearly"},
        {"email": "alice@example.com", "tier": "radar-regional", "mode": "payment"},
    ],
)
def test_checkout_rejects_client_supplied_pricing_or_cadence_fields(payload):
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(payload)


def test_paid_checkout_requires_explicit_business_acceptance_fields():
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate({"email": "alice@example.com", "tier": "radar-regional"})
    with pytest.raises(ValidationError):
        CheckoutRequest.model_validate(
            {
                "email": "alice@example.com",
                "tier": "radar-regional",
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


@pytest.mark.asyncio
async def test_billing_portal_is_scoped_to_authenticated_customer(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_checkout")
    monkeypatch.setattr(settings, "app_url", "https://caregist.co.uk")
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"stripe_customer_id": "cus_owned"})

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch(
             "api.routers.billing.stripe.billing_portal.Session.create",
             return_value={"url": "https://billing.stripe.test/session"},
         ):
        result = await create_billing_portal(_browser_auth())

    assert result == {"portal_url": "https://billing.stripe.test/session"}


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
            _checkout(email="alice@example.com", tier="radar-regional"),
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
                _checkout(email="alice@example.com", tier="radar-regional"),
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

    assert exc.value.status_code == 410
    assert "no longer sold" in exc.value.detail
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

    assert exc.value.status_code == 410
    assert "no longer sold" in exc.value.detail
    create_session.assert_not_called()
