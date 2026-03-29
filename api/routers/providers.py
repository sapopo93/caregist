"""Provider search, detail, nearby, compare, and export endpoints."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from api.config import filter_fields, get_tier_config, settings
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.middleware.rate_limit import add_rate_limit_headers
from api.queries.providers import (
    COMPARE_QUERY,
    DEFAULT_SORT,
    DETAIL_BY_SLUG,
    NEARBY_COUNT,
    NEARBY_QUERY,
    SEARCH_COUNT,
    SEARCH_EXPORT,
    SORT_OPTIONS,
    build_search_query,
)

logger = logging.getLogger("caregist.api")
router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


def _row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "as_tuple"):
            d[k] = float(v)
    return d


def _paginated_response(data: list, total: int, page: int, per_page: int, tier: str | None = None) -> dict:
    pages = max(1, (total + per_page - 1) // per_page)
    resp: dict[str, Any] = {
        "data": data,
        "meta": {"total": total, "page": page, "per_page": per_page, "pages": pages},
    }
    if tier:
        resp["meta"]["tier"] = tier
    return resp


@router.get("/search")
async def search_providers(
    response: Response,
    q: str | None = Query(None, max_length=500),
    region: str | None = Query(None),
    rating: str | None = Query(None),
    type: str | None = Query(None),
    service_type: str | None = Query(None),
    postcode: str | None = Query(None, max_length=10),
    sort: str = Query(DEFAULT_SORT),
    page: int = Query(1, ge=1),
    per_page: int | None = Query(None, ge=1),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Search care providers. Field visibility depends on your tier."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    # Enforce page size limit per tier
    max_page = config["page_size"]
    per_page = min(per_page or max_page, max_page)
    offset = (page - 1) * per_page

    query_sql = build_search_query(sort)

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(query_sql, q, region, rating, type, service_type, postcode, per_page, offset)
            count_row = await conn.fetchrow(SEARCH_COUNT, q, region, rating, type, service_type, postcode)
    except Exception as exc:
        logger.error("Search query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    total = count_row["total"] if count_row else 0
    data = [filter_fields(_row_to_dict(r), tier) for r in rows]
    return _paginated_response(data, total, page, per_page, tier)


@router.get("/export.csv")
async def export_providers_csv(
    response: Response,
    q: str | None = Query(None, max_length=500),
    region: str | None = Query(None),
    rating: str | None = Query(None),
    type: str | None = Query(None),
    service_type: str | None = Query(None),
    postcode: str | None = Query(None, max_length=10),
    _auth: dict = Depends(validate_api_key),
) -> StreamingResponse:
    """Export search results as CSV. Row limit depends on tier."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    if config["export"] == 0:
        raise HTTPException(status_code=403, detail="CSV export requires Starter tier or above. Upgrade at /pricing")

    row_limit = config["export"]

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(SEARCH_EXPORT + f" LIMIT {row_limit}", q, region, rating, type, service_type, postcode)
    except Exception as exc:
        logger.error("Export query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Export failed.")

    if not rows:
        raise HTTPException(status_code=404, detail="No results to export.")

    buf = io.StringIO()
    data = [filter_fields(_row_to_dict(r), tier) for r in rows]
    fieldnames = [k for k in data[0].keys() if data[0][k] is not None]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in data:
        writer.writerow({k: v for k, v in row.items() if v is not None})

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=caregist_export.csv"},
    )


@router.get("/compare")
async def compare_providers(
    response: Response,
    slugs: str = Query(..., max_length=1000),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Compare providers side-by-side. Max count depends on tier."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    if config["compare"] == 0:
        raise HTTPException(status_code=403, detail="Compare requires Starter tier or above. Upgrade at /pricing")

    slug_list = [s.strip() for s in slugs.split(",") if s.strip()][:config["compare"]]
    if not slug_list:
        raise HTTPException(status_code=400, detail="Provide at least one provider slug.")

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(COMPARE_QUERY, slug_list)
    except Exception as exc:
        logger.error("Compare query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    if not rows:
        raise HTTPException(status_code=404, detail="No matching providers found.")

    return {"data": [filter_fields(_row_to_dict(r), tier) for r in rows]}


@router.get("/{slug}")
async def get_provider(response: Response, slug: str, _auth: dict = Depends(validate_api_key)) -> dict:
    """Get a single provider by slug. Field visibility depends on tier."""
    tier = _auth["tier"]
    add_rate_limit_headers(response, tier, _auth["remaining"])

    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(DETAIL_BY_SLUG, slug)
    except Exception as exc:
        logger.error("Detail query failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    if not row:
        raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")
    return {"data": filter_fields(_row_to_dict(row), tier)}


@router.get("/nearby/search")
async def nearby_providers(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, ge=0.1, le=100),
    type: str | None = Query(None),
    rating: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int | None = Query(None, ge=1),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Find providers near a point. Requires Starter tier or above."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    if not config["nearby"]:
        raise HTTPException(status_code=403, detail="Nearby search requires Starter tier or above. Upgrade at /pricing")

    max_page = config["page_size"]
    per_page = min(per_page or max_page, max_page)
    offset = (page - 1) * per_page

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(NEARBY_QUERY, lon, lat, radius_km, type, rating, per_page, offset)
            count_row = await conn.fetchrow(NEARBY_COUNT, lon, lat, radius_km, type, rating)
    except Exception as exc:
        logger.error("Nearby query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    total = count_row["total"] if count_row else 0
    data = [filter_fields(_row_to_dict(r), tier) for r in rows]
    return _paginated_response(data, total, page, per_page, tier)
