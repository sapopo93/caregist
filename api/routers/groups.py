"""Care group benchmarking — aggregate data by parent organisation."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.middleware.rate_limit import add_rate_limit_headers

logger = logging.getLogger("caregist.groups")
router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


@router.get("")
async def list_groups(
    response: Response,
    q: str | None = Query(None, max_length=200),
    min_locations: int = Query(2, ge=2),
    sort: str = Query("locations"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """List care groups with aggregate ratings. Sortable by size, quality, or name."""
    add_rate_limit_headers(response, _auth["tier"], _auth["remaining"])

    sort_map = {
        "locations": "location_count DESC",
        "quality": "avg_quality_score DESC NULLS LAST",
        "name": "group_name ASC",
        "pct_good": "pct_good_or_outstanding DESC NULLS LAST",
    }
    order = sort_map.get(sort)
    if not order:
        raise HTTPException(status_code=400, detail=f"Invalid sort. Choose from: {', '.join(sort_map.keys())}")

    offset = (page - 1) * per_page

    try:
        async with get_connection() as conn:
            if q:
                rows = await conn.fetch(
                    f"""SELECT * FROM care_groups
                        WHERE group_name ILIKE '%' || $1 || '%'
                          AND location_count >= $2
                        ORDER BY {order}
                        LIMIT $3 OFFSET $4""",
                    q, min_locations, per_page, offset,
                )
                count = await conn.fetchval(
                    """SELECT COUNT(*) FROM care_groups
                       WHERE group_name ILIKE '%' || $1 || '%'
                         AND location_count >= $2""",
                    q, min_locations,
                )
            else:
                rows = await conn.fetch(
                    f"""SELECT * FROM care_groups
                        WHERE location_count >= $1
                        ORDER BY {order}
                        LIMIT $2 OFFSET $3""",
                    min_locations, per_page, offset,
                )
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM care_groups WHERE location_count >= $1",
                    min_locations,
                )
    except Exception as exc:
        logger.error("Groups query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Query failed.")

    data = []
    for r in rows:
        d = dict(r)
        # Convert arrays to lists for JSON
        d["regions"] = list(d.get("regions") or [])
        d["provider_types"] = list(d.get("provider_types") or [])
        data.append(d)

    total = count or 0
    pages = max(1, (total + per_page - 1) // per_page)

    return {
        "data": data,
        "meta": {"total": total, "page": page, "per_page": per_page, "pages": pages},
    }


@router.get("/{slug}")
async def get_group(
    response: Response,
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Get a care group with benchmark data and all locations."""
    add_rate_limit_headers(response, _auth["tier"], _auth["remaining"])

    try:
        async with get_connection() as conn:
            group = await conn.fetchrow("SELECT * FROM care_groups WHERE slug = $1", slug)
            if not group:
                raise HTTPException(status_code=404, detail="Group not found.")

            # Get all locations for this group
            locations = await conn.fetch(
                """SELECT id, name, slug, type, town, county, postcode, region,
                          overall_rating, quality_score, quality_tier, number_of_beds,
                          service_types, last_inspection_date, phone
                   FROM care_providers
                   WHERE provider_id = $1
                   ORDER BY overall_rating ASC, name ASC""",
                group["provider_id"],
            )

            # National benchmarks for comparison
            national = await conn.fetchrow(
                """SELECT
                     ROUND(AVG(quality_score)::numeric, 1) as avg_quality_score,
                     ROUND((COUNT(*) FILTER (WHERE overall_rating IN ('Outstanding','Good'))::numeric /
                            NULLIF(COUNT(*) FILTER (WHERE overall_rating IS NOT NULL AND overall_rating != 'Not Yet Inspected'), 0)) * 100, 1
                     ) as pct_good_or_outstanding
                   FROM care_providers
                   WHERE overall_rating IS NOT NULL AND overall_rating != 'Not Yet Inspected'"""
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Group detail query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Query failed.")

    g = dict(group)
    g["regions"] = list(g.get("regions") or [])
    g["provider_types"] = list(g.get("provider_types") or [])

    location_data = []
    for r in locations:
        d = dict(r)
        for k, v in d.items():
            if hasattr(v, "as_tuple"):
                d[k] = float(v)
        location_data.append(d)

    return {
        "data": {
            **g,
            "locations": location_data,
            "benchmark": {
                "national_avg_quality": float(national["avg_quality_score"]) if national["avg_quality_score"] else None,
                "national_pct_good": float(national["pct_good_or_outstanding"]) if national["pct_good_or_outstanding"] else None,
            },
        },
    }
