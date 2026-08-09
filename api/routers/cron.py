"""Authenticated entry points for Vercel Cron operational jobs."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException

from api.config import settings
from api.utils.email_queue import process_email_queue
from tools.run_new_registration_feed_cycle import run_cycle as run_feed_cycle

router = APIRouter(prefix="/api/v1/cron", tags=["cron"])


def _require_cron_secret(authorization: str | None) -> None:
    expected = settings.cron_secret
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not expected or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid cron authorization.")


@router.get("/email-queue")
async def drain_email_queue(authorization: str | None = Header(default=None)) -> dict[str, int | bool]:
    _require_cron_secret(authorization)
    sent = await process_email_queue(batch_size=50)
    return {"ok": True, "sent": sent}


@router.get("/feed-cycle")
async def run_registration_feed_cycle(authorization: str | None = Header(default=None)) -> dict[str, int | bool]:
    _require_cron_secret(authorization)
    result = await run_feed_cycle(settings.database_url, skip_digests=False)
    return {"ok": True, **result}