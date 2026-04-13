"""Region, service type, and rating lookup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.providers import RATINGS_QUERY, REGIONS_QUERY, SERVICE_TYPES_QUERY

router = APIRouter(prefix="/api/v1", tags=["lookups"])


@router.get("/regions")
async def list_regions(_ip=Depends(check_public_rate_limit)) -> dict:
    """List all regions with provider counts."""
    async with get_connection() as conn:
        rows = await conn.fetch(REGIONS_QUERY)
    return {"data": [dict(r) for r in rows]}


@router.get("/service-types")
async def list_service_types(_ip=Depends(check_public_rate_limit)) -> dict:
    """List all service types with provider counts."""
    try:
        async with get_connection() as conn:
            rows = await conn.fetch(SERVICE_TYPES_QUERY)
        return {"data": [dict(r) for r in rows]}
    except Exception:
        raise HTTPException(status_code=503, detail="Service unavailable.")


@router.get("/ratings")
async def list_ratings(_ip=Depends(check_public_rate_limit)) -> dict:
    """List all CQC ratings with provider counts."""
    async with get_connection() as conn:
        rows = await conn.fetch(RATINGS_QUERY)
    return {"data": [dict(r) for r in rows]}
