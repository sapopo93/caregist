"""Region and service type lookup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.providers import REGIONS_QUERY, SERVICE_TYPES_QUERY

router = APIRouter(prefix="/api/v1", tags=["lookups"])


@router.get("/regions")
async def list_regions(_auth: dict = Depends(validate_api_key)) -> dict:
    """List all regions with provider counts."""
    async with get_connection() as conn:
        rows = await conn.fetch(REGIONS_QUERY)
    return {"data": [dict(r) for r in rows]}


@router.get("/service-types")
async def list_service_types(_auth: dict = Depends(validate_api_key)) -> dict:
    """List all service types with provider counts."""
    async with get_connection() as conn:
        rows = await conn.fetch(SERVICE_TYPES_QUERY)
    return {"data": [dict(r) for r in rows]}
