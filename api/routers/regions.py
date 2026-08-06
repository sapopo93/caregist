"""Region, service type, and rating lookup endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.providers import RATINGS_QUERY, REGIONS_QUERY, SERVICE_TYPES_QUERY
from api.service_taxonomy import canonical_service_rows, taxonomy

router = APIRouter(prefix="/api/v1", tags=["lookups"])
logger = logging.getLogger("caregist.api")

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
        return {"data": canonical_service_rows([dict(r) for r in rows])}
    except Exception as exc:
        logger.warning("Service types lookup failed; returning fallback list: %s", exc)
        return {
            "data": [
                {
                    "service_type": entry["slug"],
                    "service_name": entry["name"],
                    "category": entry["category"],
                    "provider_count": 0,
                    "source_aliases": entry["aliases"],
                }
                for entry in taxonomy()
            ]
        }


@router.get("/ratings")
async def list_ratings(_ip=Depends(check_public_rate_limit)) -> dict:
    """List all CQC ratings with provider counts."""
    async with get_connection() as conn:
        rows = await conn.fetch(RATINGS_QUERY)
    return {"data": [dict(r) for r in rows]}
