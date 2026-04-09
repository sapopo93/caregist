"""First-party analytics ingestion endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.middleware.ip_rate_limit import check_public_rate_limit
from api.utils.analytics import log_event

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class AnalyticsEventRequest(BaseModel):
    event_type: str = Field(..., min_length=2, max_length=80)
    event_source: str = Field(..., min_length=2, max_length=80)
    email: str | None = Field(None, max_length=255)
    provider_id: str | None = Field(None, max_length=20)
    meta: dict = Field(default_factory=dict)


@router.post("/events", status_code=202)
async def ingest_event(
    req: AnalyticsEventRequest,
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Accept low-risk product analytics events from public or authenticated pages."""
    await log_event(
        req.event_type,
        req.event_source,
        email=req.email,
        provider_id=req.provider_id,
        meta=req.meta,
    )
    return {"accepted": True}
