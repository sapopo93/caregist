"""Public tool endpoints (no auth required)."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.public_tools import (
    CHANGE_FREQUENCY_COLLECTION_COVERAGE,
    CHANGE_FREQUENCY_DAILY,
    GET_CACHED_POSTCODE,
    INSERT_POSTCODE_CACHE,
    NEARBY_PUBLIC_COUNT,
    NEARBY_PUBLIC_QUERY,
)
from api.services.cqc_freshness import get_cqc_freshness
from api.services.postcode_geocode import (
    compact_uk_postcode,
    postcodes_io_fallback_path,
    postcodes_io_lookup_path,
)
from api.utils.analytics import log_event

logger = logging.getLogger("caregist.public_tools")
router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


def _longest_quiet_streak(event_counts: list[int]) -> int:
    longest = 0
    current = 0
    for count in event_counts:
        if count == 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _coords_from_postcodes_io(payload: dict) -> tuple[float, float] | None:
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return None
    try:
        return float(result["latitude"]), float(result["longitude"])
    except (KeyError, TypeError, ValueError):
        return None


async def _fetch_postcodes_io(path: str) -> tuple[float, float] | None:
    async with httpx.AsyncClient(timeout=3) as client:
        resp = await client.get(f"https://api.postcodes.io{path}")
    if resp.status_code != 200:
        return None
    return _coords_from_postcodes_io(resp.json())


async def _geocode_postcode(postcode: str) -> tuple[float, float]:
    """Geocode a UK postcode or outward district. Cache, then postcodes.io."""
    clean = compact_uk_postcode(postcode)

    try:
        async with get_connection() as conn:
            cached = await conn.fetchrow(GET_CACHED_POSTCODE, clean)
            if cached:
                return float(cached["latitude"]), float(cached["longitude"])
    except Exception as exc:
        logger.warning("Postcode cache lookup failed for %s: %s", clean, exc)

    try:
        coords = await _fetch_postcodes_io(postcodes_io_lookup_path(clean))
        if coords is None:
            fallback = postcodes_io_fallback_path(clean)
            if fallback:
                coords = await _fetch_postcodes_io(fallback)
        if coords is None:
            raise HTTPException(status_code=422, detail="Invalid or unrecognised postcode.")
        lat, lon = coords
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


@router.get("/cqc-change-frequency")
async def cqc_change_frequency(
    days: int = Query(90, ge=1, le=365),
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Report aggregate substantive CQC changes and collection coverage."""
    try:
        async with get_connection() as conn:
            daily_rows = await conn.fetch(CHANGE_FREQUENCY_DAILY, days)
            coverage_rows = await conn.fetch(CHANGE_FREQUENCY_COLLECTION_COVERAGE, days)
            authoritative_freshness = await get_cqc_freshness(conn)
    except Exception as exc:
        logger.error("CQC change-frequency report failed: %s", exc)
        raise HTTPException(status_code=503, detail="Change-frequency report is unavailable.")

    daily = []
    event_type_totals = {
        "newRegistration": 0,
        "ratingChanged": 0,
        "statusChanged": 0,
        "ownershipChanged": 0,
        "groupMovement": 0,
    }
    event_counts: list[int] = []
    for row in daily_rows:
        event_count = int(row["events"] or 0)
        event_counts.append(event_count)
        event_types = {
            "newRegistration": int(row["new_registrations"] or 0),
            "ratingChanged": int(row["rating_changes"] or 0),
            "statusChanged": int(row["status_changes"] or 0),
            "ownershipChanged": int(row["ownership_changes"] or 0),
            "groupMovement": int(row["group_movements"] or 0),
        }
        for event_type, count in event_types.items():
            event_type_totals[event_type] += count
        daily.append(
            {
                "date": row["day"].isoformat(),
                "eventCount": event_count,
                "byEventType": event_types,
            }
        )

    completed_collection_days = {
        row["day"] for row in coverage_rows if row["status"] == "completed"
    }
    completed_runs = sum(
        int(row["runs"] or 0) for row in coverage_rows if row["status"] == "completed"
    )
    failed_runs = sum(
        int(row["runs"] or 0) for row in coverage_rows if row["status"] == "failed"
    )
    latest_successful_run = max(
        (
            row["latest_run_at"]
            for row in coverage_rows
            if row["status"] == "completed" and row["latest_run_at"] is not None
        ),
        default=None,
    )
    active_change_days = sum(1 for count in event_counts if count > 0)
    quiet_days = len(event_counts) - active_change_days
    longest_quiet_streak = _longest_quiet_streak(event_counts)
    event_count = sum(event_counts)
    observed_any_change = event_count > 0
    coverage_days = len(completed_collection_days)
    coverage_ratio = round(coverage_days / days, 5)
    authoritative_status = str(authoritative_freshness.get("status") or "unknown")
    interpretation_reliable = coverage_days == days and authoritative_status == "fresh"

    return {
        "data": {
            "period": {
                "from": daily[0]["date"] if daily else None,
                "to": daily[-1]["date"] if daily else None,
                "days": days,
            },
            "summary": {
                "eventCount": event_count,
                "activeChangeDays": active_change_days,
                "quietDays": quiet_days,
                "longestQuietStreakDays": longest_quiet_streak,
                "changesEveryDay": (
                    observed_any_change and quiet_days == 0
                    if interpretation_reliable
                    else None
                ),
                "changesAtLeastEveryThreeDays": (
                    observed_any_change and longest_quiet_streak <= 2
                    if interpretation_reliable
                    else None
                ),
                "changesAtLeastWeekly": (
                    observed_any_change and longest_quiet_streak <= 6
                    if interpretation_reliable
                    else None
                ),
            },
            "byEventType": event_type_totals,
            "collectionCoverage": {
                "daysWithSuccessfulCollection": coverage_days,
                "coverageRatio": coverage_ratio,
                "interpretationReliable": interpretation_reliable,
                "completedRuns": completed_runs,
                "failedRuns": failed_runs,
                "latestSuccessfulRunAt": (
                    latest_successful_run.isoformat() if latest_successful_run else None
                ),
                "authoritativeStatus": authoritative_status,
                "sourceRetrievedAt": authoritative_freshness.get("sourceRetrievedAt"),
                "reconciledAt": authoritative_freshness.get("reconciledAt"),
                "authoritativeCoveragePercentage": authoritative_freshness.get(
                    "coveragePercentage"
                ),
                "countsReconciled": bool(authoritative_freshness.get("countsReconciled")),
                "reason": authoritative_freshness.get("reason"),
            },
            "daily": daily,
            "methodology": {
                "changeSource": "trusted_event_ledger",
                "changeTime": "observed_at",
                "refreshWritesExcluded": True,
                "warning": (
                    "Observed change cadence is conclusive only when collection coverage is complete."
                ),
            },
        }
    }
