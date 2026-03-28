"""Provider search, detail, and nearby endpoints."""

from __future__ import annotations

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

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row)


def _paginated_response(data: list, total: int, page: int, per_page: int) -> dict:
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page),
        },
    }


@router.get("/search")
async def search_providers(
    q: str | None = Query(None, description="Search query (name, town, postcode, service type)"),
    region: str | None = Query(None, description="Filter by region"),
    rating: str | None = Query(None, description="Filter by overall CQC rating"),
    type: str | None = Query(None, description="Filter by provider type"),
    service_type: str | None = Query(None, description="Filter by service type"),
    postcode: str | None = Query(None, description="Filter by postcode prefix"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(None, ge=1, le=100, description="Results per page"),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Search care providers with text search and filters."""
    per_page = per_page or settings.default_page_size
    offset = (page - 1) * per_page

    async with get_connection() as conn:
        rows = await conn.fetch(
            SEARCH_QUERY, q, region, rating, type, service_type, postcode, per_page, offset
        )
        count_row = await conn.fetchrow(
            SEARCH_COUNT, q, region, rating, type, service_type, postcode
        )

    total = count_row["total"] if count_row else 0
    data = [_row_to_dict(r) for r in rows]
    return _paginated_response(data, total, page, per_page)


@router.get("/{slug}")
async def get_provider(
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Get a single provider by slug."""
    async with get_connection() as conn:
        row = await conn.fetchrow(DETAIL_BY_SLUG, slug)

    if not row:
        raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")

    return {"data": _row_to_dict(row)}


@router.get("/nearby/search")
async def nearby_providers(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
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

    async with get_connection() as conn:
        rows = await conn.fetch(
            NEARBY_QUERY, lon, lat, radius_km, type, rating, per_page, offset
        )
        count_row = await conn.fetchrow(
            NEARBY_COUNT, lon, lat, radius_km, type, rating
        )

    total = count_row["total"] if count_row else 0
    data = [_row_to_dict(r) for r in rows]
    return _paginated_response(data, total, page, per_page)
