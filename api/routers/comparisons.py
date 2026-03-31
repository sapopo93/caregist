"""Saved comparison endpoints."""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.comparisons import (
    COUNT_BY_USER,
    DELETE_COMPARISON,
    GET_BY_TOKEN,
    INSERT_COMPARISON,
    LIST_BY_USER,
)

logger = logging.getLogger("caregist.comparisons")
router = APIRouter(prefix="/api/v1/comparisons", tags=["comparisons"])


class SaveComparisonRequest(BaseModel):
    slug_list: list[str] = Field(..., min_length=2, max_length=10)
    title: str | None = Field(None, max_length=255)


async def _get_user_id(auth: dict) -> int:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM api_keys WHERE name = $1 AND is_active = true",
            auth.get("name", ""),
        )
    if not row or not row["user_id"]:
        raise HTTPException(status_code=401, detail="User account required.")
    return row["user_id"]


@router.post("", status_code=201)
async def save_comparison(
    req: SaveComparisonRequest,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Save a comparison. Free tier: max 2 saved."""
    user_id = await _get_user_id(_auth)
    tier = _auth["tier"]

    async with get_connection() as conn:
        if tier == "free":
            count_row = await conn.fetchrow(COUNT_BY_USER, user_id)
            if count_row and count_row["total"] >= 2:
                raise HTTPException(
                    status_code=403,
                    detail="Free tier allows 2 saved comparisons. Upgrade to Pro Alerts for unlimited.",
                )

        token = secrets.token_urlsafe(16)
        row = await conn.fetchrow(
            INSERT_COMPARISON, user_id, token, req.slug_list, req.title,
        )

    try:
        from api.utils.analytics import log_event
        from api.utils.email_queue import queue_email
        from datetime import datetime, timedelta, timezone
        await log_event("comparison_saved", "compare", user_id=user_id, meta={"slugs": req.slug_list})
        # Schedule follow-up email
        try:
            async with get_connection() as conn:
                urow = await conn.fetchrow("SELECT email FROM users WHERE id = $1", user_id)
            if urow and urow["email"]:
                await queue_email(
                    urow["email"],
                    "Your comparison is saved — get rating alerts?",
                    "<p>Your provider comparison is saved on CareGist.</p>"
                    "<p>Want to be notified if any of these providers change their CQC rating?</p>"
                    "<p><a href='https://caregist.co.uk/pricing'>Set up monitoring alerts →</a></p>",
                    send_after=datetime.now(timezone.utc) + timedelta(hours=24),
                )
        except Exception:
            pass
    except Exception:
        pass

    return {"data": dict(row)}


@router.get("/mine")
async def list_my_comparisons(
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """List saved comparisons for the current user."""
    user_id = await _get_user_id(_auth)

    async with get_connection() as conn:
        rows = await conn.fetch(LIST_BY_USER, user_id)

    return {"data": [dict(r) for r in rows]}


@router.get("/{share_token}")
async def get_comparison(
    share_token: str,
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Get a saved comparison by share token (public)."""
    async with get_connection() as conn:
        row = await conn.fetchrow(GET_BY_TOKEN, share_token)
    if not row:
        raise HTTPException(status_code=404, detail="Comparison not found.")
    return {"data": dict(row)}


@router.delete("/{comparison_id}")
async def delete_comparison(
    comparison_id: int,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Delete a saved comparison (owner only)."""
    user_id = await _get_user_id(_auth)

    async with get_connection() as conn:
        await conn.execute(DELETE_COMPARISON, comparison_id, user_id)

    return {"deleted": True}
