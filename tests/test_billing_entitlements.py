from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from api.routers.billing import get_subscription


@pytest.mark.asyncio
async def test_get_subscription_uses_higher_key_tier_when_subscription_row_is_stale():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "tier": "free",
            "status": "active",
            "included_users": 1,
            "extra_seats": 0,
            "max_users": 1,
            "seat_price_gbp": 0,
            "stripe_subscription_id": None,
            "cancel_at_period_end": False,
            "current_period_end": None,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection):
        result = await get_subscription({"user_id": 1, "tier": "business"})

    assert result["tier"] == "business"
    assert result["entitlements"]["included_users"] == 10
    assert result["entitlements"]["max_users"] == 10
    assert result["cancel_at_period_end"] is False
    assert result["current_period_end"] is None


@pytest.mark.asyncio
async def test_get_subscription_does_not_collapse_paid_alerts_pro_to_free():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "tier": "alerts-pro",
            "status": "active",
            "included_users": 1,
            "extra_seats": 0,
            "max_users": 1,
            "seat_price_gbp": 0,
            "stripe_subscription_id": "sub_alerts",
            "cancel_at_period_end": False,
            "current_period_end": None,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection):
        result = await get_subscription({"user_id": 1, "tier": "free"})

    assert result["tier"] == "alerts-pro"
    assert result["stripe_subscription_id"] == "sub_alerts"
    assert result["entitlements"]["tier"] == "alerts-pro"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["past_due", "incomplete", "unpaid", "paused", "canceled", "unknown"])
async def test_get_subscription_fails_closed_for_non_entitled_billing_status(status):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "tier": "business",
            "status": status,
            "included_users": 10,
            "extra_seats": 8,
            "max_users": 18,
            "seat_price_gbp": 49,
            "stripe_subscription_id": "sub_business",
            "cancel_at_period_end": False,
            "current_period_end": None,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.billing.get_connection", mock_get_connection):
        result = await get_subscription({"user_id": 1, "tier": "business"})

    assert result["tier"] == "free"
    assert result["status"] == status
    assert result["stripe_subscription_id"] == "sub_business"
    assert result["entitlements"]["tier"] == "free"
    assert result["entitlements"]["extra_seats"] == 0
