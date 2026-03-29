"""Admin dashboard and moderation endpoints (master key only)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.admin import DASHBOARD_STATS, TOP_ENQUIRED_PROVIDERS
from api.queries.claims import (
    COUNT_CLAIMS,
    LIST_CLAIMS,
    MARK_PROVIDER_CLAIMED,
    MARK_PROVIDER_UNCLAIMED,
    UPDATE_CLAIM_STATUS,
)
from api.queries.enquiries import COUNT_ENQUIRIES, LIST_ENQUIRIES, UPDATE_ENQUIRY_STATUS
from api.queries.reviews import (
    COUNT_REVIEWS_ADMIN,
    LIST_REVIEWS_ADMIN,
    MODERATE_REVIEW,
    UPDATE_PROVIDER_REVIEW_STATS,
)

logger = logging.getLogger("caregist.admin")
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


async def require_admin(auth: dict = Depends(validate_api_key)) -> dict:
    """Only allow master key (admin tier) access."""
    if auth.get("tier") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return auth


# -- Dashboard --


@router.get("/stats")
async def dashboard_stats(_auth: dict = Depends(require_admin)) -> dict:
    """Overview stats for the admin dashboard."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(DASHBOARD_STATS)
            top = await conn.fetch(TOP_ENQUIRED_PROVIDERS, 10)
    except Exception as exc:
        logger.error("Dashboard stats failed: %s", exc)
        raise HTTPException(status_code=503, detail="Failed to load stats.")

    return {
        "data": dict(row),
        "top_enquired": [dict(r) for r in top],
    }


# -- Claims moderation --


@router.get("/claims")
async def list_claims(
    status: str | None = Query(None, description="Filter by status: pending, approved, rejected"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _auth: dict = Depends(require_admin),
) -> dict:
    """List provider claims."""
    offset = (page - 1) * per_page
    try:
        async with get_connection() as conn:
            rows = await conn.fetch(LIST_CLAIMS, status, per_page, offset)
            count_row = await conn.fetchrow(COUNT_CLAIMS, status)
    except Exception as exc:
        logger.error("List claims failed: %s", exc)
        raise HTTPException(status_code=503, detail="Failed to load claims.")

    total = count_row["total"] if count_row else 0
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "data": [dict(r) for r in rows],
        "meta": {"total": total, "page": page, "per_page": per_page, "pages": pages},
    }


class ClaimAction(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    admin_notes: str | None = Field(None, max_length=2000)


@router.patch("/claims/{claim_id}")
async def moderate_claim(
    claim_id: int,
    req: ClaimAction,
    auth: dict = Depends(require_admin),
) -> dict:
    """Approve or reject a provider claim."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(
                UPDATE_CLAIM_STATUS, claim_id, req.status, auth["name"], req.admin_notes
            )
            if not row:
                raise HTTPException(status_code=404, detail="Claim not found.")

            if req.status == "approved":
                await conn.execute(MARK_PROVIDER_CLAIMED, row["provider_id"])
            elif req.status == "rejected":
                await conn.execute(MARK_PROVIDER_UNCLAIMED, row["provider_id"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Moderate claim %d failed: %s", claim_id, exc)
        raise HTTPException(status_code=503, detail="Failed to update claim.")

    return {"data": dict(row), "message": f"Claim {req.status}."}


# -- Reviews moderation --


@router.get("/reviews")
async def list_reviews_admin(
    status: str | None = Query(None, description="Filter by status: pending, approved, rejected"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _auth: dict = Depends(require_admin),
) -> dict:
    """List reviews for moderation."""
    offset = (page - 1) * per_page
    try:
        async with get_connection() as conn:
            rows = await conn.fetch(LIST_REVIEWS_ADMIN, status, per_page, offset)
            count_row = await conn.fetchrow(COUNT_REVIEWS_ADMIN, status)
    except Exception as exc:
        logger.error("List reviews admin failed: %s", exc)
        raise HTTPException(status_code=503, detail="Failed to load reviews.")

    total = count_row["total"] if count_row else 0
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "data": [dict(r) for r in rows],
        "meta": {"total": total, "page": page, "per_page": per_page, "pages": pages},
    }


class ReviewAction(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    admin_notes: str | None = Field(None, max_length=2000)


@router.patch("/reviews/{review_id}")
async def moderate_review(
    review_id: int,
    req: ReviewAction,
    _auth: dict = Depends(require_admin),
) -> dict:
    """Approve or reject a review."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(MODERATE_REVIEW, review_id, req.status, req.admin_notes)
            if not row:
                raise HTTPException(status_code=404, detail="Review not found.")

            await conn.execute(UPDATE_PROVIDER_REVIEW_STATS, row["provider_id"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Moderate review %d failed: %s", review_id, exc)
        raise HTTPException(status_code=503, detail="Failed to update review.")

    return {"data": dict(row), "message": f"Review {req.status}."}


# -- Enquiries management --


@router.get("/enquiries")
async def list_enquiries(
    provider_id: str | None = Query(None, description="Filter by provider ID"),
    status: str | None = Query(None, description="Filter by status: new, read, responded, converted"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _auth: dict = Depends(require_admin),
) -> dict:
    """List enquiries."""
    offset = (page - 1) * per_page
    try:
        async with get_connection() as conn:
            rows = await conn.fetch(LIST_ENQUIRIES, provider_id, status, per_page, offset)
            count_row = await conn.fetchrow(COUNT_ENQUIRIES, provider_id, status)
    except Exception as exc:
        logger.error("List enquiries failed: %s", exc)
        raise HTTPException(status_code=503, detail="Failed to load enquiries.")

    total = count_row["total"] if count_row else 0
    pages = max(1, (total + per_page - 1) // per_page)
    return {
        "data": [dict(r) for r in rows],
        "meta": {"total": total, "page": page, "per_page": per_page, "pages": pages},
    }


class EnquiryAction(BaseModel):
    status: str = Field(..., pattern="^(read|responded|converted)$")


@router.patch("/enquiries/{enquiry_id}")
async def update_enquiry(
    enquiry_id: int,
    req: EnquiryAction,
    _auth: dict = Depends(require_admin),
) -> dict:
    """Update enquiry status."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(UPDATE_ENQUIRY_STATUS, enquiry_id, req.status)
            if not row:
                raise HTTPException(status_code=404, detail="Enquiry not found.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Update enquiry %d failed: %s", enquiry_id, exc)
        raise HTTPException(status_code=503, detail="Failed to update enquiry.")

    return {"data": dict(row), "message": f"Enquiry marked as {req.status}."}
