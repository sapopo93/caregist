"""Email subscription endpoints (public, no auth required)."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.subscribe import GET_LAST_SYNC_DATE, INSERT_SUBSCRIBER
from api.utils.analytics import log_event
from api.utils.email_queue import queue_email

logger = logging.getLogger("caregist.subscribe")
router = APIRouter(prefix="/api/v1", tags=["subscribe"])


class SubscribeRequest(BaseModel):
    email: EmailStr
    source: str = Field("homepage", max_length=50)
    postcode: str | None = Field(None, max_length=10)


@router.post("/subscribe")
async def subscribe(
    req: SubscribeRequest,
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Subscribe an email address. Silently handles duplicates."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(
                INSERT_SUBSCRIBER,
                req.email,
                req.source,
                req.postcode,
                json.dumps({}),
            )
    except Exception as exc:
        logger.error("Subscribe failed: %s", exc)
        raise HTTPException(status_code=503, detail="Subscription failed. Please try again.")

    is_new = row is not None

    await log_event(
        "email_subscribe",
        req.source,
        email=req.email,
        meta={"postcode": req.postcode, "new": is_new},
    )

    if is_new:
        await queue_email(
            req.email,
            "Welcome to CareGist",
            "<p>Thanks for subscribing to CareGist. You'll receive weekly CQC rating changes.</p>"
            "<p>Data sourced from the CQC public register, refreshed weekly.</p>"
            "<p style='color:#8a6a4a;font-size:12px'>Unsubscribe anytime by replying to this email.</p>",
        )

    return {"success": True, "existing": not is_new}


@router.get("/last-sync")
async def last_sync() -> dict:
    """Return the last pipeline sync date (public, no auth)."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(GET_LAST_SYNC_DATE)
    except Exception:
        return {"last_sync": None}

    return {"last_sync": row["completed_at"].isoformat() if row else None}
