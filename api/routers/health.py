"""Health check endpoint (no auth required)."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.database import get_connection

logger = logging.getLogger("caregist.health")
router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check() -> JSONResponse:
    """Health check — verifies database connectivity."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) as total FROM care_providers")
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "providers_count": row["total"] if row else 0,
            },
        )
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
            },
        )
