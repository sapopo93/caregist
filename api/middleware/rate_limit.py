"""Rate limiter with in-memory burst controls and persistent quota storage."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

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


def _recent_day_values(days: int) -> set[date]:
    now = datetime.now(timezone.utc).date()
    return {now - timedelta(days=offset) for offset in range(days)}


def _month_start() -> date:
    now = datetime.now(timezone.utc).date()
    return now.replace(day=1)


def _record_in_memory(api_key: str, today: str, month: str, daily_used: int, monthly_used: int) -> None:
    _daily_counts[api_key][today] = daily_used + 1
    _rolling_7d_counts[api_key][today] = _rolling_7d_counts[api_key].get(today, 0) + 1
    _monthly_counts[api_key][month] = monthly_used + 1


def _check_persistent_windows(api_key: str, tier: str) -> dict[str, int]:
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
            detail=f"Rate limit exceeded ({config['rate']} requests/sec). Upgrade at /pricing",
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
    _record_in_memory(api_key, today, month, daily_used, monthly_used)

    return {
        "burst_remaining": burst_remaining - 1,
        "daily_remaining": daily_remaining - 1,
        "rolling_7d_remaining": rolling_7d_remaining - 1,
        "monthly_remaining": monthly_remaining - 1,
    }


async def _load_persisted_counts(api_key: str) -> tuple[int, int, int]:
    from api.database import get_connection

    today = datetime.now(timezone.utc).date()
    valid_days = _recent_day_values(7)
    month_start = _month_start()

    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT usage_date, request_count
            FROM api_rate_usage_daily
            WHERE api_key = $1
              AND usage_date >= $2
            """,
            api_key,
            month_start,
        )

    daily_used = 0
    rolling_used = 0
    monthly_used = 0
    for row in rows:
        usage_date = row["usage_date"]
        count = int(row["request_count"] or 0)
        monthly_used += count
        if usage_date == today:
            daily_used = count
        if usage_date in valid_days:
            rolling_used += count
    return daily_used, rolling_used, monthly_used


async def _persist_request(api_key: str) -> None:
    from api.database import get_connection

    today = datetime.now(timezone.utc).date()
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO api_rate_usage_daily (api_key, usage_date, request_count, updated_at)
            VALUES ($1, $2, 1, NOW())
            ON CONFLICT (api_key, usage_date)
            DO UPDATE SET
              request_count = api_rate_usage_daily.request_count + 1,
              updated_at = NOW()
            """,
            api_key,
            today,
        )
        await conn.execute(
            "DELETE FROM api_rate_usage_daily WHERE usage_date < $1",
            today - timedelta(days=45),
        )


async def check_rate_limit(api_key: str, tier: str) -> dict[str, int]:
    """Check all rate limits. Raise 429 if exceeded. Returns remaining counts."""
    _cleanup_stale()
    config = get_tier_config(tier)
    now = time.monotonic()

    window_seconds = config.get("rate_window_seconds", 1)
    window_start = now - window_seconds
    _burst_requests[api_key] = [t for t in _burst_requests[api_key] if t > window_start]
    burst_remaining = config["rate"] - len(_burst_requests[api_key])

    if burst_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({config['rate']} requests/sec). Upgrade at /pricing",
            headers={"Retry-After": str(window_seconds)},
        )

    try:
        daily_used, rolling_7d_used, monthly_used = await _load_persisted_counts(api_key)
        persistent_store = True
    except RuntimeError:
        persistent_store = False
        return _check_persistent_windows(api_key, tier)

    daily_remaining = config["daily"] - daily_used
    if daily_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded ({config['daily']}/day). Upgrade at /pricing",
            headers={"Retry-After": "3600"},
        )

    rolling_7d_remaining = config["rolling_7d"] - rolling_7d_used
    if rolling_7d_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"7-day limit exceeded ({config['rolling_7d']}/7 days). Upgrade at /pricing",
            headers={"Retry-After": "86400"},
        )

    monthly_remaining = config["monthly"] - monthly_used
    if monthly_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit exceeded ({config['monthly']}/month). Upgrade at /pricing",
            headers={"Retry-After": "86400"},
        )

    _burst_requests[api_key].append(now)
    if persistent_store:
        await _persist_request(api_key)

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
