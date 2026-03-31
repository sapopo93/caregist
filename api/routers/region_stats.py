"""Region and local authority stats endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.region_stats import (
    ALL_LOCAL_AUTHORITIES,
    LA_NAME_FROM_SLUG,
    RATING_DIST_BY_LA,
    TOP_PROVIDERS_BY_LA,
    TOTAL_BY_LA,
    TYPE_DIST_BY_LA,
)

logger = logging.getLogger("caregist.region_stats")
router = APIRouter(prefix="/api/v1/regions", tags=["regions"])


@router.get("/{la_slug}/stats")
async def region_stats(
    la_slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Get stats for a local authority by slug."""
    async with get_connection() as conn:
        # Resolve slug to LA name
        la_row = await conn.fetchrow(LA_NAME_FROM_SLUG, la_slug.lower())
        if not la_row:
            raise HTTPException(status_code=404, detail=f"Local authority not found: {la_slug}")

        la_name = la_row["local_authority"]

        total_row = await conn.fetchrow(TOTAL_BY_LA, la_name)
        rating_rows = await conn.fetch(RATING_DIST_BY_LA, la_name)
        top_rows = await conn.fetch(TOP_PROVIDERS_BY_LA, la_name)
        type_rows = await conn.fetch(TYPE_DIST_BY_LA, la_name)

    total = total_row["total"] if total_row else 0
    rating_dist = {r["overall_rating"]: r["count"] for r in rating_rows}
    good_or_above = rating_dist.get("Outstanding", 0) + rating_dist.get("Good", 0)
    pct_good = round(good_or_above / total * 100, 1) if total > 0 else 0

    return {
        "data": {
            "local_authority": la_name,
            "slug": la_slug,
            "total_providers": total,
            "pct_good_or_outstanding": pct_good,
            "rating_distribution": rating_dist,
            "top_providers": [dict(r) for r in top_rows],
            "type_distribution": {r["type"]: r["count"] for r in type_rows},
        }
    }


@router.get("/local-authorities")
async def list_local_authorities(
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """List all local authorities with provider counts."""
    async with get_connection() as conn:
        rows = await conn.fetch(ALL_LOCAL_AUTHORITIES)

    return {
        "data": [
            {
                "name": r["local_authority"],
                "slug": r["local_authority"].lower().replace(" ", "-").replace("'", ""),
                "provider_count": r["provider_count"],
            }
            for r in rows
        ]
    }
