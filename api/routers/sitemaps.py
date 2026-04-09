"""Public sitemap support endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.sitemaps import COUNT_ACTIVE_PROVIDER_SLUGS, LIST_ACTIVE_PROVIDER_SLUGS

router = APIRouter(prefix="/api/v1/sitemaps", tags=["sitemaps"])


@router.get("/providers/count")
async def provider_sitemap_count(_ip=Depends(check_public_rate_limit)) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(COUNT_ACTIVE_PROVIDER_SLUGS)
    return {"total": int(row["total"] or 0)}


@router.get("/providers")
async def provider_sitemap_page(
    offset: int = Query(0, ge=0),
    limit: int = Query(50000, ge=1, le=50000),
    _ip=Depends(check_public_rate_limit),
) -> dict:
    async with get_connection() as conn:
        rows = await conn.fetch(LIST_ACTIVE_PROVIDER_SLUGS, offset, limit)
    return {
        "data": [
            {
                "slug": row["slug"],
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ],
        "meta": {"offset": offset, "limit": limit, "returned": len(rows)},
    }
