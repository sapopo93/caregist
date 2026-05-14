"""Rate limiter — in-memory only (single-worker uvicorn deployment).

Redis was intentionally dropped. See docs/scaling.md for when and how to
reintroduce it. The startup assertion below enforces the single-worker
contract; if you raise UVICORN_WORKERS above 1 without restoring Redis,
per-worker token buckets will diverge and effective rate limits will
multiply by the worker count.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from starlette.responses import Response

from api.config import get_tier_config, settings

logger = logging.getLogger("caregist.rate_limit")

# ---------------------------------------------------------------------------
# Startup assertion — single-worker contract
# ---------------------------------------------------------------------------

def _assert_single_worker() -> None:
    """Raise RuntimeError if the process is not running as a single uvicorn worker.

    Set UVICORN_WORKERS=1 (or leave it unset) in the environment.
    See docs/scaling.md before changing this.
    """
    workers_env = os.getenv("UVICORN_WORKERS")
    if workers_env is not None and workers_env.strip() != "1":
        raise RuntimeError(
            f"UVICORN_WORKERS is set to {workers_env!r}, but Caregist currently uses "
            "in-memory rate limiting which only works correctly with a single worker. "
            "See docs/scaling.md to reintroduce Redis before scaling beyond 1 worker."
        )


_assert_single_worker()

# ---------------------------------------------------------------------------
# In-memory state (process-local, single-worker safe)
# ---------------------------------------------------------------------------

# Sliding-window burst tracker: api_key -> list of request timestamps (monotonic)
_burst_requests: dict[str, list[float]] = defaultdict(list)

# Persistent quota cache: api_key -> (daily_used, rolling_7d_used, monthly_used)
_quota_cache: dict[str, tuple[int, int, int]] = {}
# Last-write timestamps so we can skip redundant DB writes within a second
_quota_write_ts: dict[str, float] = {}


def _today() -> str:
    return date.today().isoformat()


def _this_month() -> str:
    return date.today().strftime("%Y-%m")


def _cleanup_stale() -> None:
    """Evict burst entries older than the longest possible window (60 s)."""
    cutoff = time.monotonic() - 60
    stale = [k for k, ts_list in _burst_requests.items() if ts_list and ts_list[-1] < cutoff]
    for k in stale:
        del _burst_requests[k]


# ---------------------------------------------------------------------------
# DB persistence helpers (unchanged from original DB-fallback path)
# ---------------------------------------------------------------------------

async def _load_persisted_counts(api_key: str) -> tuple[int, int, int]:
    """Load today's daily, rolling-7d, and monthly counts from the DB."""
    from api.database import pool  # local import to avoid circular deps

    if pool is None:
        raise RuntimeError("DB pool not initialised")

    today = _today()
    month = _this_month()
    seven_days_ago = (date.today() - timedelta(days=7)).isoformat()

    async with pool.acquire() as conn:
        daily = await conn.fetchval(
            "SELECT COUNT(*) FROM api_requests WHERE api_key=$1 AND created_date=$2",
            api_key, today,
        )
        rolling = await conn.fetchval(
            "SELECT COUNT(*) FROM api_requests WHERE api_key=$1 AND created_date>=$2",
            api_key, seven_days_ago,
        )
        monthly = await conn.fetchval(
            "SELECT COUNT(*) FROM api_requests WHERE api_key=$1 AND created_month=$2",
            api_key, month,
        )

    return int(daily or 0), int(rolling or 0), int(monthly or 0)


async def _persist_request(api_key: str) -> None:
    """Write a single request record to the DB for quota tracking."""
    from api.database import pool

    if pool is None:
        return

    today = _today()
    month = _this_month()

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_requests (api_key, created_date, created_month) VALUES ($1,$2,$3)",
            api_key, today, month,
        )


def _log_background_task(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.warning("Background persist failed: %s", task.exception())


# ---------------------------------------------------------------------------
# In-memory rate-limit logic
# ---------------------------------------------------------------------------

def _check_persistent_windows(api_key: str, tier: str) -> dict[str, int]:
    config = get_tier_config(tier)
    now = time.monotonic()
    today = _today()
    month = _this_month()

    # Burst check (sliding window)
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

    # Record burst timestamp
    _burst_requests[api_key].append(now)

    # In-memory quota (best-effort without DB)
    cached = _quota_cache.get(api_key)
    if cached is None:
        return {
            "burst_remaining": burst_remaining - 1,
            "daily_remaining": config["daily"],
            "rolling_7d_remaining": config["rolling_7d"],
            "monthly_remaining": config["monthly"],
        }

    daily_used, rolling_7d_used, monthly_used = cached
    return {
        "burst_remaining": burst_remaining - 1,
        "daily_remaining": max(0, config["daily"] - daily_used),
        "rolling_7d_remaining": max(0, config["rolling_7d"] - rolling_7d_used),
        "monthly_remaining": max(0, config["monthly"] - monthly_used),
    }


async def check_rate_limit(api_key: str, tier: str) -> dict[str, int]:
    """Check all rate limits. Raise 429 if exceeded. Returns remaining counts.

    Single-worker in-memory path only. Redis was intentionally removed.
    See docs/scaling.md for how to reintroduce it when scaling beyond 1 worker.
    """
    _cleanup_stale()
    config = get_tier_config(tier)

    # --- Burst check (sliding window, in-memory) ---
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

    # --- Quota checks (DB-backed) ---
    try:
        daily_used, rolling_7d_used, monthly_used = await _load_persisted_counts(api_key)
    except RuntimeError:
        # DB pool not ready — degrade gracefully, burst limiting still applies
        _burst_requests[api_key].append(now)
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

    # Record burst timestamp and persist to DB
    _burst_requests[api_key].append(now)
    task = asyncio.create_task(_persist_request(api_key))
    task.add_done_callback(_log_background_task)

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
