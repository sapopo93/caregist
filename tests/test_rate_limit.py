"""Tests for plan quota enforcement."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

import api.middleware.rate_limit as rate_limit


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    rate_limit._burst_requests.clear()
    rate_limit._daily_counts.clear()
    rate_limit._rolling_7d_counts.clear()
    rate_limit._monthly_counts.clear()
    yield
    rate_limit._burst_requests.clear()
    rate_limit._daily_counts.clear()
    rate_limit._rolling_7d_counts.clear()
    rate_limit._monthly_counts.clear()


@pytest.mark.asyncio
async def test_free_plan_allows_two_requests_per_second():
    key = "cg_free_test"
    first = await rate_limit.check_rate_limit(key, "free")
    second = await rate_limit.check_rate_limit(key, "free")

    assert first["burst_remaining"] == 1
    assert second["burst_remaining"] == 0

    with pytest.raises(HTTPException) as exc:
        await rate_limit.check_rate_limit(key, "free")

    assert exc.value.status_code == 429
    assert "2 requests/sec" in exc.value.detail


@pytest.mark.asyncio
async def test_free_plan_blocks_when_rolling_seven_day_cap_is_reached():
    key = "cg_free_weekly"
    today = rate_limit._today()
    rate_limit._rolling_7d_counts[key][today] = 60

    with pytest.raises(HTTPException) as exc:
        await rate_limit.check_rate_limit(key, "free")

    assert exc.value.status_code == 429
    assert "60/7 days" in exc.value.detail
