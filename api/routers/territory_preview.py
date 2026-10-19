"""Free, read-only Territory Brief preview (flag-gated, no auth).

Off unless ``territory_preview_enabled``; when off every route returns 404 so the
surface does not advertise itself. Opens no checkout, delivery or export path.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import settings
from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries import territory_preview as q
from api.services.territory_preview import PreviewScope, build_preview, window_for

logger = logging.getLogger("caregist.territory_preview")
router = APIRouter(prefix="/api/v1/territory-preview", tags=["territory-preview"])


def _require_enabled() -> None:
    if not settings.territory_preview_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/territories", dependencies=[Depends(_require_enabled), Depends(check_public_rate_limit)])
async def list_territories() -> dict:
    async with get_connection() as conn:
        rows = await conn.fetch(q.TERRITORIES)
    regions = [{"name": r["name"], "organisations": r["organisations"]} for r in rows if r["kind"] == "region"]
    las = [{"name": r["name"], "organisations": r["organisations"]} for r in rows if r["kind"] == "local_authority"]
    return {
        "regions": regions,
        "local_authorities": las,
        "services": [{"key": k, "label": v} for k, v in q.SERVICE_TYPES.items()],
    }


@router.get("", dependencies=[Depends(_require_enabled), Depends(check_public_rate_limit)])
async def preview(
    kind: Literal["region", "local_authority"],
    name: str = Query(..., min_length=2, max_length=80, pattern=r"^[A-Za-z0-9 .,'()&/-]+$"),
    service: Literal["homecare", "residential", "nursing", "supported_living"] | None = None,
) -> dict:
    column = q.SCOPE_COLUMNS[kind]
    service_label = q.SERVICE_TYPES[service] if service else None
    async with get_connection() as conn:
        counts = await conn.fetchrow(q.scope_counts(column), name, service_label)
        if not counts or not counts["locations"]:
            raise HTTPException(
                status_code=404,
                detail=f"No active England care locations match {name!r} for that service.",
            )
        as_of = await conn.fetchval(q.SOURCE_AS_OF)
        if as_of is None:
            raise HTTPException(status_code=503, detail="Source dates are unavailable.")
        start, end = window_for(as_of)
        events = [dict(r) for r in await conn.fetch(q.new_registrations(column), name, service_label, start, end)]
        events += [dict(r) for r in await conn.fetch(q.rating_changes(column), name, service_label, start, end)]
    scope = PreviewScope(
        kind=kind, name=counts["canonical_name"] or name, service_key=service, service_label=service_label,
    )
    return build_preview(
        scope,
        organisations=counts["organisations"],
        locations=counts["locations"],
        as_of=as_of,
        events=events,
    )
