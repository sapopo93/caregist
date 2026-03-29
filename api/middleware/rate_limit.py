"""In-memory rate limiter with per-minute, daily, and monthly caps."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from starlette.responses import Response

from api.config import get_tier_config

# Per-minute: key -> list of timestamps
_minute_requests: dict[str, list[float]] = defaultdict(list)

# Daily: key -> {date_str: count}
_daily_counts: dict[str, dict[str, int]] = defaultdict(dict)

# Monthly: key -> {month_str: count}
_monthly_counts: dict[str, dict[str, int]] = defaultdict(dict)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _this_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def check_rate_limit(api_key: str, tier: str) -> dict[str, int]:
    """Check all rate limits. Raise 429 if exceeded. Returns remaining counts."""
    config = get_tier_config(tier)
    now = time.monotonic()
    today = _today()
    month = _this_month()

    # Per-minute check
    window_start = now - 60
    _minute_requests[api_key] = [t for t in _minute_requests[api_key] if t > window_start]
    minute_remaining = config["rate"] - len(_minute_requests[api_key])

    if minute_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({config['rate']}/min). Upgrade at /pricing",
            headers={"Retry-After": "60"},
        )

    # Daily check
    daily_used = _daily_counts[api_key].get(today, 0)
    daily_remaining = config["daily"] - daily_used

    if daily_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded ({config['daily']}/day). Upgrade at /pricing",
            headers={"Retry-After": "3600"},
        )

    # Monthly check
    monthly_used = _monthly_counts[api_key].get(month, 0)
    monthly_remaining = config["monthly"] - monthly_used

    if monthly_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit exceeded ({config['monthly']}/month). Upgrade at /pricing",
            headers={"Retry-After": "86400"},
        )

    # Record the request
    _minute_requests[api_key].append(now)
    _daily_counts[api_key][today] = daily_used + 1
    _monthly_counts[api_key][month] = monthly_used + 1

    return {
        "minute_remaining": minute_remaining - 1,
        "daily_remaining": daily_remaining - 1,
        "monthly_remaining": monthly_remaining - 1,
    }


def add_rate_limit_headers(response: Response, tier: str, remaining: dict[str, int]) -> None:
    """Add rate limit headers to a response."""
    config = get_tier_config(tier)
    response.headers["X-Tier"] = tier
    response.headers["X-RateLimit-Limit"] = str(config["rate"])
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining["minute_remaining"]))
    response.headers["X-DailyLimit-Limit"] = str(config["daily"])
    response.headers["X-DailyLimit-Remaining"] = str(max(0, remaining["daily_remaining"]))
    response.headers["X-MonthlyLimit-Limit"] = str(config["monthly"])
    response.headers["X-MonthlyLimit-Remaining"] = str(max(0, remaining["monthly_remaining"]))
