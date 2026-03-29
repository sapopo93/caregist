"""Health check endpoint (no auth required)."""

from __future__ import annotations

from fastapi import APIRouter

from api.database import get_connection

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check() -> dict:
    """Health check — verifies database connectivity."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) as total FROM care_providers")
        return {
            "status": "healthy",
            "providers_count": row["total"] if row else 0,
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "error": str(exc),
        }
