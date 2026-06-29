"""Health check endpoint (no auth required)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from api.database import get_connection
from api.metrics import render_latest, set_pending_emails
from api.middleware.internal_auth import validate_internal_token
from api.services.pipeline_health import get_pipeline_health

logger = logging.getLogger("caregist.health")
router = APIRouter(tags=["health"])


@router.get("/metrics")
async def metrics(_auth: dict = Depends(validate_internal_token)) -> Response:
    """Prometheus metrics endpoint.

    Refreshes the pending-email gauges from the DB, then renders all collectors.
    A DB hiccup must not break scraping, so gauge refresh failures are swallowed.
    """
    try:
        async with get_connection() as conn:
            rows = await conn.fetch(
                "SELECT status, COUNT(*) AS n FROM pending_emails GROUP BY status"
            )
        for row in rows:
            set_pending_emails(row["status"], int(row["n"]))
    except Exception as exc:
        logger.warning("Metrics gauge refresh failed: %s", exc)

    body, content_type = render_latest()
    return Response(content=body, media_type=content_type)


@router.get("/api/v1/health/liveness")
async def liveness_check() -> JSONResponse:
    """Liveness probe that does not touch external dependencies."""
    return JSONResponse(status_code=200, content={"status": "alive"})


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
    """Readiness check for traffic and automation dependencies."""
    try:
        async with get_connection() as conn:
            snapshot = await get_pipeline_health(conn)
        status_code = 200 if snapshot["readiness_ok"] else 503
        return JSONResponse(status_code=status_code, content=snapshot)
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return JSONResponse(status_code=503, content={"status": "unhealthy"})


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
