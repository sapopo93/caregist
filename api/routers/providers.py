"""Provider search, detail, and nearby endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.providers import (
    DETAIL_BY_SLUG,
    NEARBY_COUNT,
    NEARBY_QUERY,
    SEARCH_COUNT,
    SEARCH_QUERY,
)

logger = logging.getLogger("caregist.api")
router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


def _row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    # Convert Decimal to float for JSON serialization
    for k, v in d.items():
        if hasattr(v, "as_tuple"):  # Decimal
            d[k] = float(v)
    return d


def _paginated_response(data: list, total: int, page: int, per_page: int) -> dict:
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        },
    }


@router.get("/search")
async def search_providers(
    q: str | None = Query(None, description="Search query (name, town, postcode, service type)", max_length=500),
    region: str | None = Query(None, description="Filter by region"),
    rating: str | None = Query(None, description="Filter by overall CQC rating"),
    type: str | None = Query(None, description="Filter by provider type"),
    service_type: str | None = Query(None, description="Filter by service type"),
    postcode: str | None = Query(None, description="Filter by postcode prefix", max_length=10),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(None, ge=1, le=100, description="Results per page"),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Search care providers with text search and filters."""
    per_page = per_page or settings.default_page_size
    offset = (page - 1) * per_page

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(
                SEARCH_QUERY, q, region, rating, type, service_type, postcode, per_page, offset
            )
            count_row = await conn.fetchrow(
                SEARCH_COUNT, q, region, rating, type, service_type, postcode
            )
    except Exception as exc:
        logger.error("Search query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed. Please try again.")

    total = count_row["total"] if count_row else 0
    data = [_row_to_dict(r) for r in rows]
    return _paginated_response(data, total, page, per_page)


@router.get("/{slug}")
async def get_provider(
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Get a single provider by slug."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(DETAIL_BY_SLUG, slug)
    except Exception as exc:
        logger.error("Provider detail query failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Database query failed. Please try again.")

    if not row:
        raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")

    return {"data": _row_to_dict(row)}


@router.get("/nearby/search")
async def nearby_providers(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(10, ge=0.1, le=100, description="Radius in kilometres"),
    type: str | None = Query(None, description="Filter by provider type"),
    rating: str | None = Query(None, description="Filter by overall CQC rating"),
    page: int = Query(1, ge=1),
    per_page: int = Query(None, ge=1, le=100),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Find providers near a geographic point."""
    per_page = per_page or settings.default_page_size
    offset = (page - 1) * per_page

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(
                NEARBY_QUERY, lon, lat, radius_km, type, rating, per_page, offset
            )
            count_row = await conn.fetchrow(
                NEARBY_COUNT, lon, lat, radius_km, type, rating
            )
    except Exception as exc:
        logger.error("Nearby query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed. Please try again.")

    total = count_row["total"] if count_row else 0
    data = [_row_to_dict(r) for r in rows]
    return _paginated_response(data, total, page, per_page)
