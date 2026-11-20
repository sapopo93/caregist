"""Region Monthly coverage preview (flag-gated, no auth, read-only).

Off unless ``region_monthly_enabled``; when off every route answers 404, the same
plain "Not Found" as an unknown route, so the surface does not advertise itself.
Stage 1 has no checkout, no payment and no download: this route only tells a
visitor which months a purchase would include, which are built, which are still
to be built and when, and what the data can and cannot say.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import settings
from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries import region_monthly as q
from api.services import region_monthly as svc

router = APIRouter(prefix="/api/v1/region-monthly", tags=["region-monthly"])


def _require_enabled() -> None:
    if not settings.region_monthly_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _refusal(error: svc.RegionMonthlyError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message})


@router.get("/coverage", dependencies=[Depends(_require_enabled), Depends(check_public_rate_limit)])
async def coverage(
    region: str = Query("", max_length=60),
    service: str = Query("", max_length=60),
    first_month: str = Query("", max_length=40),
    kind: str = Query("", max_length=12),
    accept_future_months: bool = False,
) -> dict:
    """What a purchase would include. ``first_month`` is ``YYYY-MM``; ``kind`` sets the run length."""
    try:
        svc.require_kind(kind)
        canonical_region = svc.normalise_region(region)
        slug = svc.normalise_service(service)
        first = svc.parse_month(first_month)
    except svc.RegionMonthlyError as error:
        raise _refusal(error)

    async with get_connection() as conn:
        if not await conn.fetchval(q.BUILDS_TABLE_PRESENT):
            raise _refusal(svc.RegionMonthlyError("source_unavailable"))
        built = [r["period_month"] for r in await conn.fetch(q.BUILT_MONTHS, canonical_region, slug)]
    try:
        return svc.coverage_preview(
            kind,
            first,
            _now(),
            region=canonical_region,
            service_slug=slug,
            built_months=built,
            accept_future_months=accept_future_months,
        )
    except svc.RegionMonthlyError as error:
        raise _refusal(error)
