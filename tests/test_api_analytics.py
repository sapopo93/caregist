"""Tests for the analytics ingestion endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_analytics_event_accepts_payload():
    with patch("api.routers.analytics.log_event", new=AsyncMock()) as mock_log:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analytics/events",
                json={
                    "event_type": "pricing_cta_click",
                    "event_source": "pricing_page",
                    "meta": {"tier": "pro"},
                },
            )

    assert resp.status_code == 202
    assert resp.json() == {"accepted": True}
    mock_log.assert_awaited_once()


def test_enterprise_prefix_uses_enterprise_tier():
    from api.config import get_tier_config

    assert get_tier_config("enterprise-public-sector") == get_tier_config("enterprise")
