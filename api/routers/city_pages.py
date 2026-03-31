"""City-level provider listing endpoints for SEO pages."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.city_pages import (
    CITY_NAME_FROM_SLUG,
    COUNT_BY_CITY,
    PROVIDERS_BY_CITY,
    RATING_DIST_BY_CITY,
    TOP_CITIES,
)

logger = logging.getLogger("caregist.city_pages")
router = APIRouter(prefix="/api/v1/cities", tags=["cities"])


@router.get("/{city_slug}/providers")
async def city_providers(
    city_slug: str,
    rating: str | None = Query(None),
    type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Get providers in a city, optionally filtered by rating."""
    offset = (page - 1) * per_page

    async with get_connection() as conn:
        city_row = await conn.fetchrow(CITY_NAME_FROM_SLUG, city_slug.lower())
        if not city_row:
            raise HTTPException(status_code=404, detail=f"City not found: {city_slug}")

        rows = await conn.fetch(PROVIDERS_BY_CITY, city_slug.lower(), rating, type, per_page, offset)
        count_row = await conn.fetchrow(COUNT_BY_CITY, city_slug.lower(), rating, type)
        rating_rows = await conn.fetch(RATING_DIST_BY_CITY, city_slug.lower())

    total = count_row["total"] if count_row else 0
    pages = max(1, (total + per_page - 1) // per_page)

    return {
        "data": [dict(r) for r in rows],
        "meta": {
            "city": city_row["town"],
            "slug": city_slug,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "rating_filter": rating,
            "rating_distribution": {r["overall_rating"]: r["count"] for r in rating_rows},
        },
    }


@router.get("")
async def list_top_cities(
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """List top 500 cities by provider count."""
    async with get_connection() as conn:
        rows = await conn.fetch(TOP_CITIES)

    return {"data": [dict(r) for r in rows]}
