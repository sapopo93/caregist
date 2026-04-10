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
