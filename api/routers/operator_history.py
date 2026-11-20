"""Free, read-only Operator History coverage preview (flag-gated, no auth).

Off unless ``operator_history_enabled``; when off every route returns the same
404 as an unknown route, so the surface does not advertise itself. It opens no
checkout, delivery or export path. Same public rate limit as the Territory Brief
preview.

An operator is identified by its CQC Provider ID. A name search that matches
more than one Provider ID is refused with the candidates' ID, name and location
count only, so the caller chooses by ID.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import settings
from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.services import operator_history as service

logger = logging.getLogger("caregist.operator_history")
router = APIRouter(prefix="/api/v1/operator-history", tags=["operator-history"])


def _require_enabled() -> None:
    if not settings.operator_history_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


@router.get("/coverage", dependencies=[Depends(_require_enabled), Depends(check_public_rate_limit)])
async def coverage(
    provider_id: str | None = Query(None, max_length=32),
    name: str | None = Query(None, max_length=service.NAME_MAX_LENGTH * 2),
) -> dict:
    try:
        async with get_connection() as conn, conn.transaction(isolation="repeatable_read", readonly=True):
            return await service.coverage_preview(conn, provider_id=provider_id, name=name)
    except service.OperatorRefusal as refusal:
        raise HTTPException(status_code=refusal.http_status, detail=refusal.as_detail())
