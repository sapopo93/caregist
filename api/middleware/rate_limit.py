"""In-memory rate limiter with burst, daily, rolling-7-day, and monthly caps."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from starlette.responses import Response

from api.config import get_tier_config

# Burst window: key -> list of timestamps
_burst_requests: dict[str, list[float]] = defaultdict(list)

# Daily: key -> {date_str: count}
_daily_counts: dict[str, dict[str, int]] = defaultdict(dict)

# Rolling 7-day: key -> {date_str: count}
_rolling_7d_counts: dict[str, dict[str, int]] = defaultdict(dict)

# Monthly: key -> {month_str: count}
_monthly_counts: dict[str, dict[str, int]] = defaultdict(dict)


_request_count = 0
_CLEANUP_INTERVAL = 1000


def _cleanup_stale():
    """Remove entries outside the active burst/day/week/month windows."""
    global _request_count
    _request_count += 1
    if _request_count < _CLEANUP_INTERVAL:
        return
    _request_count = 0
    today = _today()
    month = _this_month()
    valid_days = _recent_days(7)
    for key in list(_daily_counts.keys()):
        _daily_counts[key] = {d: c for d, c in _daily_counts[key].items() if d == today}
        if not _daily_counts[key]:
            del _daily_counts[key]
    for key in list(_rolling_7d_counts.keys()):
        _rolling_7d_counts[key] = {d: c for d, c in _rolling_7d_counts[key].items() if d in valid_days}
        if not _rolling_7d_counts[key]:
            del _rolling_7d_counts[key]
    for key in list(_monthly_counts.keys()):
        _monthly_counts[key] = {m: c for m, c in _monthly_counts[key].items() if m == month}
        if not _monthly_counts[key]:
            del _monthly_counts[key]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _this_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _recent_days(days: int) -> set[str]:
    now = datetime.now(timezone.utc)
    return {
        (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=offset)).strftime("%Y-%m-%d")
        for offset in range(days)
    }


def check_rate_limit(api_key: str, tier: str) -> dict[str, int]:
    """Check all rate limits. Raise 429 if exceeded. Returns remaining counts."""
    _cleanup_stale()
    config = get_tier_config(tier)
    now = time.monotonic()
    today = _today()
    month = _this_month()

    # Burst check
    window_seconds = config.get("rate_window_seconds", 1)
    window_start = now - window_seconds
    _burst_requests[api_key] = [t for t in _burst_requests[api_key] if t > window_start]
    burst_remaining = config["rate"] - len(_burst_requests[api_key])

    if burst_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({config['rate']}/sec). Upgrade at /pricing",
            headers={"Retry-After": str(window_seconds)},
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

    # Rolling 7-day check
    rolling_7d_used = sum(_rolling_7d_counts[api_key].values())
    rolling_7d_remaining = config["rolling_7d"] - rolling_7d_used

    if rolling_7d_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"7-day limit exceeded ({config['rolling_7d']}/7 days). Upgrade at /pricing",
            headers={"Retry-After": "86400"},
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
    _burst_requests[api_key].append(now)
    _daily_counts[api_key][today] = daily_used + 1
    _rolling_7d_counts[api_key][today] = _rolling_7d_counts[api_key].get(today, 0) + 1
    _monthly_counts[api_key][month] = monthly_used + 1

    return {
        "burst_remaining": burst_remaining - 1,
        "daily_remaining": daily_remaining - 1,
        "rolling_7d_remaining": rolling_7d_remaining - 1,
        "monthly_remaining": monthly_remaining - 1,
    }


def add_rate_limit_headers(response: Response, tier: str, remaining: dict[str, int]) -> None:
    """Add rate limit headers to a response."""
    config = get_tier_config(tier)
    response.headers["X-Tier"] = tier
    response.headers["X-RateLimit-Limit"] = str(config["rate"])
    response.headers["X-RateLimit-Window"] = f"{config.get('rate_window_seconds', 1)}s"
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining["burst_remaining"]))
    response.headers["X-DailyLimit-Limit"] = str(config["daily"])
    response.headers["X-DailyLimit-Remaining"] = str(max(0, remaining["daily_remaining"]))
    response.headers["X-7DayLimit-Limit"] = str(config["rolling_7d"])
    response.headers["X-7DayLimit-Remaining"] = str(max(0, remaining["rolling_7d_remaining"]))
    response.headers["X-MonthlyLimit-Limit"] = str(config["monthly"])
    response.headers["X-MonthlyLimit-Remaining"] = str(max(0, remaining["monthly_remaining"]))
