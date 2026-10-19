"""Free, read-only Territory Brief preview (flag-gated, no auth).

Off unless ``territory_preview_enabled``; when off every route returns 404 so the
surface does not advertise itself. Opens no checkout, delivery or export path.
Fails closed (503) when the reconciliation quarantine table is missing, because
unconfirmed locations must not enter a public claim.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import settings
from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries import territory_preview as q
from api.service_taxonomy import resolve_service_filter
from api.services.cqc_freshness import get_cqc_freshness
from api.services.territory_preview import PreviewScope, build_preview, service_display_name, window_for

logger = logging.getLogger("caregist.territory_preview")
router = APIRouter(prefix="/api/v1/territory-preview", tags=["territory-preview"])

CACHE_TTL_SECONDS = 600
_cache: dict[tuple, tuple[float, dict[str, Any]]] = {}


def _cache_get(key: tuple) -> dict[str, Any] | None:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    _cache.pop(key, None)
    return None


def _cache_put(key: tuple, value: dict[str, Any]) -> None:
    if len(_cache) > 2000:
        _cache.clear()
    _cache[key] = (time.monotonic(), value)


def _require_enabled() -> None:
    if not settings.territory_preview_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


async def _require_quarantine_table(conn) -> None:
    if not await conn.fetchval(q.QUARANTINE_TABLE_PRESENT):
        raise HTTPException(
            status_code=503,
            detail="Territory preview is unavailable until unconfirmed CQC locations can be excluded.",
        )


@router.get("/territories", dependencies=[Depends(_require_enabled), Depends(check_public_rate_limit)])
async def list_territories() -> dict:
    cached = _cache_get(("territories",))
    if cached is not None:
        return cached
    async with get_connection() as conn:
        await _require_quarantine_table(conn)
        rows = await conn.fetch(q.TERRITORIES)
    regions = [{"name": r["name"], "organisations": r["organisations"]} for r in rows if r["kind"] == "region"]
    las = [{"name": r["name"], "organisations": r["organisations"]} for r in rows if r["kind"] == "local_authority"]
    body = {
        "regions": regions,
        "local_authorities": las,
        "services": [{"key": k, "label": service_display_name(v)} for k, v in q.SERVICE_SLUGS.items()],
    }
    _cache_put(("territories",), body)
    return body


@router.get("", dependencies=[Depends(_require_enabled), Depends(check_public_rate_limit)])
async def preview(
    kind: Literal["region", "local_authority"],
    name: str = Query(..., min_length=2, max_length=80, pattern=r"^[A-Za-z0-9 .,'()&/-]+$"),
    service: Literal["homecare", "residential", "nursing", "supported_living"] | None = None,
) -> dict:
    column = q.SCOPE_COLUMNS[kind]
    slug = q.SERVICE_SLUGS[service] if service else None
    aliases = list(resolve_service_filter(slug)) if slug else None
    async with get_connection() as conn:
        await _require_quarantine_table(conn)
        freshness = await get_cqc_freshness(conn)
        key = (kind, name.casefold(), service, freshness.get("status"), freshness.get("reconciledAt"))
        cached = _cache_get(key)
        if cached is not None:
            return cached
        scope_row = await conn.fetchrow(q.scope_counts(column), name, aliases)
        if not scope_row or not scope_row["locations"]:
            raise HTTPException(
                status_code=404,
                detail=f"No active England care locations match {name!r} for that service.",
            )
        window_end = await conn.fetchval(q.LATEST_REGISTRATION)
        if window_end is None:
            raise HTTPException(status_code=503, detail="Source dates are unavailable.")
        start, end = window_for(window_end)
        counts = dict(await conn.fetchrow(q.signal_counts(column), name, aliases, start, end))
        events = [dict(r) for r in await conn.fetch(q.new_registration_examples(column), name, aliases, start, end)]
        events += [dict(r) for r in await conn.fetch(q.rating_change_examples(column), name, aliases, start, end)]
    scope = PreviewScope(
        kind=kind, name=scope_row["canonical_name"] or name, service_key=service, service_slug=slug,
    )
    body = build_preview(
        scope,
        organisations=scope_row["organisations"],
        locations=scope_row["locations"],
        window_end=window_end,
        counts=counts,
        events=events,
        freshness=freshness,
    )
    _cache_put(key, body)
    return body
