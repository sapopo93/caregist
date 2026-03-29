"""Review submission and listing endpoints."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.claims import PROVIDER_ID_BY_SLUG
from api.queries.reviews import (
    COUNT_APPROVED_REVIEWS,
    INSERT_REVIEW,
    LIST_APPROVED_REVIEWS,
    REVIEW_SUMMARY,
    UPDATE_PROVIDER_REVIEW_STATS,
)

logger = logging.getLogger("caregist.reviews")
router = APIRouter(prefix="/api/v1", tags=["reviews"])

VALID_RELATIONSHIPS = {"family_member", "service_user", "professional", "other"}


class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: str = Field(..., max_length=200)
    body: str = Field(..., max_length=5000)
    reviewer_name: str = Field(..., max_length=100)
    reviewer_email: EmailStr
    relationship: str | None = Field(None, max_length=50)
    visit_date: date | None = None


@router.post("/providers/{slug}/reviews", status_code=201)
async def submit_review(
    slug: str,
    req: ReviewRequest,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Submit a review for a provider."""
    if req.relationship and req.relationship not in VALID_RELATIONSHIPS:
        raise HTTPException(status_code=422, detail=f"Invalid relationship. Choose from: {', '.join(VALID_RELATIONSHIPS)}")

    try:
        async with get_connection() as conn:
            provider = await conn.fetchrow(PROVIDER_ID_BY_SLUG, slug)
            if not provider:
                raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")

            row = await conn.fetchrow(
                INSERT_REVIEW,
                provider["id"],
                req.rating,
                req.title,
                req.body,
                req.reviewer_name,
                req.reviewer_email,
                req.relationship,
                req.visit_date,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Review submission failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Failed to submit review.")

    return {
        "data": dict(row),
        "message": "Thank you for your review. It will appear once moderated.",
    }


@router.get("/providers/{slug}/reviews")
async def list_reviews(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(None, ge=1, le=50),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """List approved reviews for a provider."""
    per_page = per_page or settings.default_page_size
    offset = (page - 1) * per_page

    try:
        async with get_connection() as conn:
            provider = await conn.fetchrow(PROVIDER_ID_BY_SLUG, slug)
            if not provider:
                raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")

            rows = await conn.fetch(LIST_APPROVED_REVIEWS, provider["id"], per_page, offset)
            count_row = await conn.fetchrow(COUNT_APPROVED_REVIEWS, provider["id"])
            summary = await conn.fetchrow(REVIEW_SUMMARY, provider["id"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Review listing failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Failed to load reviews.")

    total = count_row["total"] if count_row else 0
    pages = max(1, (total + per_page - 1) // per_page)

    return {
        "data": [dict(r) for r in rows],
        "summary": {
            "count": summary["count"] if summary else 0,
            "avg_rating": float(summary["avg_rating"]) if summary and summary["avg_rating"] else None,
        },
        "meta": {"total": total, "page": page, "per_page": per_page, "pages": pages},
    }
