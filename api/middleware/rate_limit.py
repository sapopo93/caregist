"""In-memory sliding window rate limiter."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

# key -> list of timestamps
_requests: dict[str, list[float]] = defaultdict(list)
_window_seconds = 60


def check_rate_limit(api_key: str, limit: int) -> None:
    """Raise 429 if API key exceeds its rate limit within the sliding window."""
    now = time.monotonic()
    window_start = now - _window_seconds

    # Clean old entries
    _requests[api_key] = [t for t in _requests[api_key] if t > window_start]

    if len(_requests[api_key]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {limit} requests per minute.",
            headers={"Retry-After": "60"},
        )

    _requests[api_key].append(now)
