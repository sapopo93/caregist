"""Health check endpoint (no auth required)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
import stripe

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.config import settings
from api.database import get_connection
from api.services.pipeline_health import get_pipeline_health

logger = logging.getLogger("caregist.health")
router = APIRouter(tags=["health"])

# ---------------------------------------------------------------------------
# Simple in-memory TTL cache for external dependency pings (30 s)
# ---------------------------------------------------------------------------
_CACHE_TTL = 30  # seconds

_cache: dict[str, tuple[float, Any]] = {}  # key -> (expires_at, value)


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic() + _CACHE_TTL, value)


# ---------------------------------------------------------------------------
# External dependency checks
# ---------------------------------------------------------------------------

def _check_stripe() -> str:
    """Return 'ok' or 'down'. Uses 30 s in-memory cache."""
    cached = _cache_get("stripe")
    if cached is not None:
        return cached

    try:
        stripe.Customer.list(limit=1)
        result = "ok"
    except Exception as exc:
        logger.warning("Stripe health probe failed: %s", exc)
        result = "down"

    _cache_set("stripe", result)
    return result


def _check_resend() -> str:
    """Return 'ok' or 'down'. Uses 30 s in-memory cache."""
    cached = _cache_get("resend")
    if cached is not None:
        return cached

    resend_api_key = getattr(settings, "resend_api_key", None) or os.environ.get("RESEND_API_KEY", "")
    try:
        resp = httpx.get(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {resend_api_key}"},
            timeout=5,
        )
        # 200 or 401/403 both mean the service is reachable; network errors are the concern.
        result = "ok" if resp.status_code < 500 else "down"
    except Exception as exc:
        logger.warning("Resend health probe failed: %s", exc)
        result = "down"

    _cache_set("resend", result)
    return result


def _check_sentry() -> str:
    """Presence-only check — no live ping."""
    dsn = getattr(settings, "sentry_dsn", None) or os.environ.get("SENTRY_DSN", "")
    return "ok" if dsn else "missing"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/v1/health")
async def health_check() -> JSONResponse:
    """Health check — verifies database connectivity and freshness indicators."""
    try:
        async with get_connection() as conn:
            snapshot = await get_pipeline_health(conn)
        return JSONResponse(
            status_code=200,
            content=snapshot,
        )
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
            },
        )


@router.get("/api/v1/health/readiness")
async def readiness_check() -> JSONResponse:
    """Readiness check for traffic and automation dependencies.

    Verifies:
    - DB pipeline freshness (pipeline_runs / trusted_event_ledger) — existing checks.
    - Stripe API reachability (stripe.Customer.list probe, cached 30 s).
    - Resend API reachability (GET /domains probe, cached 30 s).
    - Sentry DSN presence (env-var check only, no live ping).

    Redis is intentionally excluded (removed per Cinder PR #2).

    Returns HTTP 200 when overall == 'ok'; 503 otherwise.
    Response shape:
    {
        "stripe":  "ok" | "down",
        "resend":  "ok" | "down",
        "sentry":  "ok" | "missing",
        "db":      "ok" | "degraded" | "down",
        "overall": "ok" | "degraded" | "down"
    }
    """
    # --- DB check (preserve existing pipeline logic) ---
    db_status = "ok"
    try:
        async with get_connection() as conn:
            snapshot = await get_pipeline_health(conn)
        if not snapshot.get("readiness_ok", False):
            db_status = "degraded"
    except Exception as exc:
        logger.error("Readiness DB check failed: %s", exc)
        db_status = "down"

    # --- External dependency checks (synchronous probes; cached) ---
    stripe_status = _check_stripe()
    resend_status = _check_resend()
    sentry_status = _check_sentry()

    # --- Derive overall ---
    ext_statuses = {stripe_status, resend_status}
    all_statuses = {db_status} | ext_statuses

    if "down" in all_statuses:
        overall = "down"
    elif "degraded" in all_statuses or sentry_status == "missing":
        overall = "degraded"
    else:
        overall = "ok"

    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "stripe": stripe_status,
            "resend": resend_status,
            "sentry": sentry_status,
            "db": db_status,
            "overall": overall,
        },
    )


@router.get("/api/v1/health/freshness")
async def freshness_check() -> JSONResponse:
    """Freshness check focused on the new-registration wedge SLA."""
    try:
        async with get_connection() as conn:
            snapshot = await get_pipeline_health(conn)
        status_code = 200 if snapshot["feed_fresh"] else 503
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if snapshot["feed_fresh"] else "stale",
                "feed_fresh": snapshot["feed_fresh"],
                "checks": snapshot["checks"],
            },
        )
    except Exception as exc:
        logger.error("Freshness check failed: %s", exc)
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
