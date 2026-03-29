"""IP-based rate limiter for unauthenticated endpoints (auth routes)."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

_ip_requests: dict[str, list[float]] = defaultdict(list)
_request_count = 0
_CLEANUP_INTERVAL = 500
_MAX_PER_MINUTE = 5


def _cleanup():
    global _request_count
    _request_count += 1
    if _request_count < _CLEANUP_INTERVAL:
        return
    _request_count = 0
    cutoff = time.monotonic() - 120
    for ip in list(_ip_requests.keys()):
        _ip_requests[ip] = [t for t in _ip_requests[ip] if t > cutoff]
        if not _ip_requests[ip]:
            del _ip_requests[ip]


async def check_ip_rate_limit(request: Request) -> None:
    """FastAPI dependency: rate limit by client IP. 5 req/min."""
    _cleanup()
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - 60

    _ip_requests[ip] = [t for t in _ip_requests[ip] if t > window_start]

    if len(_ip_requests[ip]) >= _MAX_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute.",
            headers={"Retry-After": "60"},
        )

    _ip_requests[ip].append(now)
