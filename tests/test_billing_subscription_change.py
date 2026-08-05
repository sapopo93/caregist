"""Tests for the concurrency-safe existing-subscription plan/seat change endpoint."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from api.config import get_subscription_entitlements, settings
from api.routers.billing import SubscriptionChangeRequest, change_subscription


def _change(**values) -> SubscriptionChangeRequest:
    return SubscriptionChangeRequest(**values)


def _browser_auth(**values) -> dict:
    return {
        "user_id": 42,
        "email": "alice@example.com",
        "is_verified": True,
        "auth_method": "session",
        **values,
    }


def _api_key_auth(**values) -> dict:
    return {
        "user_id": 42,
        "email": "alice@example.com",
        "is_verified": True,
        "auth_method": "api_key",
        **values,
    }


def _subscription_row(**values) -> dict:
    return {
        "tier": "starter",
        "extra_seats": 0,
        "version": 3,
        "stripe_subscription_id": "sub_123",
        "stripe_customer_id": "cus_123",
        **values,
    }


@pytest.fixture(autouse=True)
def _enable_checkout_for_endpoint_unit_tests():
    with patch("api.routers.billing.settings.billing_checkout_enabled", True), \
         patch("api.routers.billing.settings.stripe_secret_key", "sk_test_change"):
        yield


def _mock_conn(fetchrow_return=None, execute_return="UPDATE 1"):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    conn.transaction = Mock(return_value=AsyncMock())
    conn.execute = AsyncMock(return_value=execute_return)

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    return conn, mock_get_connection


@pytest.mark.asyncio
async def test_change_fails_closed_when_checkout_disabled():
    with patch("api.routers.billing.settings.billing_checkout_enabled", False), \
         patch("api.routers.billing.get_connection") as get_connection:
        with pytest.raises(HTTPException) as exc:
            await change_subscription(_change(tier="pro"), _browser_auth())

    assert exc.value.status_code == 503
    get_connection.assert_not_called()


@pytest.mark.asyncio
async def test_change_rejects_team_api_key():
    with pytest.raises(HTTPException) as exc:
        await change_subscription(_change(tier="pro"), _api_key_auth())

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_change_rejects_invalid_tier():
    with pytest.raises(HTTPException) as exc:
        await change_subscription(_change(tier="not-a-real-tier"), _browser_auth())

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_change_returns_404_without_active_subscription():
    conn, mock_get_connection = _mock_conn(fetchrow_return=None)
    with patch("api.routers.billing.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await change_subscription(_change(tier="pro"), _browser_auth())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_change_is_a_noop_when_tier_and_seats_are_unchanged():
    conn, mock_get_connection = _mock_conn(fetchrow_return=_subscription_row(tier="pro", extra_seats=2))
    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.settings.stripe_price_pro_seat", "price_pro_seat"), \
         patch("api.routers.billing.stripe.Subscription.retrieve") as retrieve, \
         patch("api.routers.billing.stripe.Subscription.modify") as modify:
        result = await change_subscription(_change(tier="pro", extra_seats=2), _browser_auth())

    assert result["changed"] is False
    retrieve.assert_not_called()
    modify.assert_not_called()
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_change_rejects_ownership_mismatch_before_any_mutation():
    conn, mock_get_connection = _mock_conn(fetchrow_return=_subscription_row())
    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Subscription.retrieve", return_value={"customer": "cus_other"}), \
         patch("api.routers.billing.stripe.Subscription.modify") as modify:
        with pytest.raises(HTTPException) as exc:
            await change_subscription(_change(tier="pro"), _browser_auth())

    assert exc.value.status_code == 409
    modify.assert_not_called()
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_change_rejects_lost_update_race_without_writing_ledger():
    conn, mock_get_connection = _mock_conn(
        fetchrow_return=_subscription_row(),
        execute_return="UPDATE 0",
    )
    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Subscription.retrieve", return_value={"customer": "cus_123"}), \
         patch("api.routers.billing.stripe.Subscription.modify") as modify:
        with pytest.raises(HTTPException) as exc:
            await change_subscription(_change(tier="pro"), _browser_auth())

    assert exc.value.status_code == 409
    modify.assert_called_once()
    assert conn.execute.await_count == 1
    assert all("INSERT INTO subscription_mutations" not in call.args[0] for call in conn.execute.await_args_list)


@pytest.mark.asyncio
async def test_change_upgrades_tier_and_seats_with_stable_idempotency_key():
    conn, mock_get_connection = _mock_conn(fetchrow_return=_subscription_row(tier="starter", extra_seats=0, version=3))
    with patch("api.routers.billing.get_connection", mock_get_connection), \
         patch("api.routers.billing.stripe.Subscription.retrieve", return_value={"customer": "cus_123"}), \
         patch("api.routers.billing.stripe.Subscription.modify") as modify, \
         patch("api.routers.billing.settings.stripe_price_pro", "price_pro"), \
         patch("api.routers.billing.settings.stripe_price_pro_seat", "price_pro_seat"), \
         patch("api.routers.billing.PRICE_TO_TIER", {"price_pro": "pro"}):
        result = await change_subscription(_change(tier="pro", extra_seats=2), _browser_auth())

    assert result == {
        "tier": "pro",
        "extra_seats": 2,
        "entitlements": get_subscription_entitlements("pro", 2),
        "changed": True,
    }
    modify.assert_called_once_with(
        "sub_123",
        items=[
            {"price": "price_pro", "quantity": 1},
            {"price": "price_pro_seat", "quantity": 2},
        ],
        proration_behavior="create_prorations",
        idempotency_key="caregist-change-42-sub_123-3-pro-2",
    )
    queries = [call.args[0] for call in conn.execute.await_args_list]
    assert any("UPDATE subscriptions" in q and "version = version + 1" in q for q in queries)
    assert any("INSERT INTO subscription_mutations" in q for q in queries)
    assert any("INSERT INTO audit_log" in q for q in queries)
