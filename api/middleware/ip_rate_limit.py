"""IP-based rate limiter for unauthenticated endpoints (auth routes)."""

from __future__ import annotations

import ipaddress
import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request

_ip_requests: dict[str, list[float]] = defaultdict(list)
_request_count = 0
_CLEANUP_INTERVAL = 500
_MAX_PER_MINUTE = 5
_MAX_PUBLIC_PER_MINUTE = 30

# Number of trusted reverse proxies in front of this service.
# The rightmost N entries in X-Forwarded-For are added by trusted proxies;
# the entry just before them is the real client IP.
_TRUSTED_PROXY_COUNT = 1


def _parse_trusted_proxy_cidrs() -> list[ipaddress._BaseNetwork]:
    """Networks whose connections are allowed to set X-Forwarded-For.

    Defaults to RFC1918 private ranges + loopback, where an ALB or internal
    proxy terminates. Override with TRUSTED_PROXY_CIDRS to match production.
    An empty override trusts nothing, so the direct peer IP is always used.
    """
    raw = os.getenv("TRUSTED_PROXY_CIDRS")
    if raw is None:
        defaults = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "::1/128"]
    else:
        defaults = [part.strip() for part in raw.split(",") if part.strip()]
    networks: list[ipaddress._BaseNetwork] = []
    for cidr in defaults:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            continue
    return networks


_TRUSTED_PROXY_CIDRS = _parse_trusted_proxy_cidrs()


def _is_trusted_proxy(peer: str | None) -> bool:
    if not peer:
        return False
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(addr in net for net in _TRUSTED_PROXY_CIDRS)


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For only behind a trusted proxy."""
    peer = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and _is_trusted_proxy(peer):
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            idx = max(0, len(ips) - _TRUSTED_PROXY_COUNT)
            return ips[idx]
    return peer or "unknown"


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
    ip = _get_client_ip(request)
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


_public_ip_requests: dict[str, list[float]] = defaultdict(list)


async def check_public_rate_limit(request: Request) -> None:
    """Looser rate limit for public non-auth endpoints. 30 req/min."""
    _cleanup()
    ip = _get_client_ip(request)
    now = time.monotonic()
    window_start = now - 60

    _public_ip_requests[ip] = [t for t in _public_ip_requests[ip] if t > window_start]

    if len(_public_ip_requests[ip]) >= _MAX_PUBLIC_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute.",
            headers={"Retry-After": "60"},
        )

    _public_ip_requests[ip].append(now)
