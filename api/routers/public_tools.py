"""Public tool endpoints (no auth required)."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.public_tools import (
    GET_CACHED_POSTCODE,
    INSERT_POSTCODE_CACHE,
    NEARBY_PUBLIC_COUNT,
    NEARBY_PUBLIC_QUERY,
)
from api.utils.analytics import log_event

logger = logging.getLogger("caregist.public_tools")
router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


async def _geocode_postcode(postcode: str) -> tuple[float, float]:
    """Geocode a UK postcode. Checks cache first, then postcodes.io."""
    clean = postcode.strip().upper().replace(" ", "")

    try:
        async with get_connection() as conn:
            cached = await conn.fetchrow(GET_CACHED_POSTCODE, clean)
            if cached:
                return float(cached["latitude"]), float(cached["longitude"])
    except Exception as exc:
        logger.warning("Postcode cache lookup failed for %s: %s", clean, exc)

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"https://api.postcodes.io/postcodes/{clean}")
            if resp.status_code != 200:
                raise HTTPException(status_code=422, detail="Invalid or unrecognised postcode.")
            data = resp.json()
            lat = data["result"]["latitude"]
            lon = data["result"]["longitude"]
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Postcodes.io lookup failed for %s: %s", clean, exc)
        raise HTTPException(status_code=422, detail="Could not geocode postcode. Please try again.")

    try:
        async with get_connection() as conn:
            await conn.execute(INSERT_POSTCODE_CACHE, clean, lat, lon)
    except Exception:
        pass

    return lat, lon


@router.get("/radius-search")
async def radius_search(
    postcode: str = Query(..., max_length=10),
    radius_miles: float = Query(5, ge=0.5, le=50),
    type: str | None = Query(None),
    rating: str | None = Query(None),
    service_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=200),
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Search providers near a UK postcode. Public, no auth required."""
    lat, lon = await _geocode_postcode(postcode)

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(NEARBY_PUBLIC_QUERY, lon, lat, radius_miles, type, rating, service_type, limit)
            count_row = await conn.fetchrow(NEARBY_PUBLIC_COUNT, lon, lat, radius_miles, type, rating, service_type)
    except Exception as exc:
        logger.error("Radius search failed: %s", exc)
        raise HTTPException(status_code=503, detail="Search failed.")

    total = count_row["total"] if count_row else 0

    await log_event(
        "radius_tool_search",
        "radius_finder",
        meta={"postcode": postcode, "radius": radius_miles, "type": type, "rating": rating, "total": total},
    )

    TYPE_LABELS = {
        "Social Care Org": "Care Home",
        "Primary Medical Services": "GP Surgery",
        "Primary Dental Care": "Dental Practice",
        "Independent Ambulance": "Ambulance Service",
        "Independent Healthcare Org": "Private Healthcare",
        "NHS Healthcare Organisation": "NHS Service",
    }

    data = []
    for r in rows:
        d = dict(r)
        for k, v in d.items():
            if hasattr(v, "as_tuple"):
                d[k] = round(float(v), 2)
        if "type" in d and d["type"] in TYPE_LABELS:
            d["type"] = TYPE_LABELS[d["type"]]
        data.append(d)

    return {
        "data": data,
        "meta": {
            "total": total,
            "showing": len(data),
            "postcode": postcode.strip().upper(),
            "radius_miles": radius_miles,
            "lat": lat,
            "lon": lon,
        },
    }
