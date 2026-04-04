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
        meta={"postcode": req.postcode, "new": is_new, "crm_state": "newsletter_lead"},
    )

    if is_new:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        if req.source == "radius_finder":
            await queue_email(
                req.email,
                "Your care provider search results — CareGist",
                "<p>Thanks for using the CareGist Radius Finder.</p>"
                "<p>Your search results are available on the site. Data sourced from the CQC public register.</p>"
                "<p style='color:#8a6a4a;font-size:12px'>Unsubscribe anytime by replying to this email.</p>",
            )
            # Day 3: monitor upsell
            await queue_email(
                req.email,
                "Ratings change — want to be notified?",
                "<p>Care provider ratings can change after inspections. "
                "Want to be notified when providers near you change rating?</p>"
                "<p><a href='https://caregist.co.uk/pricing'>Set up monitoring alerts →</a></p>",
                send_after=now + timedelta(days=3),
            )
            # Day 7: area movers
            await queue_email(
                req.email,
                "Weekly area movers — CQC rating changes near you",
                "<p>Get a weekly digest of CQC rating changes in your area.</p>"
                "<p><a href='https://caregist.co.uk/find-care'>Search again →</a></p>"
                "<p><a href='https://caregist.co.uk/pricing'>Upgrade for instant alerts →</a></p>",
                send_after=now + timedelta(days=7),
            )
        else:
            await queue_email(
                req.email,
                "Welcome to CareGist",
                "<p>Thanks for subscribing to CareGist. You'll receive weekly CQC rating changes.</p>"
                "<p>Data sourced from the CQC public register, refreshed weekly.</p>"
                "<p style='color:#8a6a4a;font-size:12px'>Unsubscribe anytime by replying to this email.</p>",
            )

    return {"success": True, "existing": not is_new}


class TrackRequest(BaseModel):
    slug: str = Field(..., max_length=300)
    event: str = Field("provider_profile_view", max_length=50)


@router.post("/track/profile-view")
async def track_profile_view(
    req: TrackRequest,
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Track a provider profile view. Public, no auth."""
    await log_event("provider_profile_view", "provider", provider_id=req.slug)
    return {"tracked": True}


@router.get("/unsubscribe")
async def unsubscribe(email: str, source: str = "weekly_movers") -> dict:
    """One-click unsubscribe. No auth required (PECR compliance)."""
    try:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE email_subscribers SET unsubscribed_at = NOW() WHERE email = $1 AND ($2 = '' OR source = $2) AND unsubscribed_at IS NULL",
                email, source,
            )
    except Exception as exc:
        logger.error("Unsubscribe failed: %s", exc)

    # Return a simple HTML page (not JSON) so clicking the link in email works
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        '<html><body style="font-family:system-ui;max-width:400px;margin:80px auto;text-align:center">'
        '<h1 style="color:#6B4C35">Unsubscribed</h1>'
        '<p style="color:#8a6a4a">You will no longer receive emails from CareGist.</p>'
        '<p><a href="https://caregist.co.uk" style="color:#C1784F">Back to CareGist</a></p>'
        '</body></html>'
    )


@router.get("/last-sync")
async def last_sync() -> dict:
    """Return the last pipeline sync date (public, no auth)."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(GET_LAST_SYNC_DATE)
    except Exception:
        return {"last_sync": None}

    return {"last_sync": row["completed_at"].isoformat() if row else None}
