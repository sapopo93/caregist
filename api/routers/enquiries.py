"""Enquiry (lead-gen) endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.claims import PROVIDER_ID_BY_SLUG
from api.queries.enquiries import INSERT_ENQUIRY, UPDATE_PROVIDER_ENQUIRY_COUNT

logger = logging.getLogger("caregist.enquiries")
router = APIRouter(prefix="/api/v1", tags=["enquiries"])

VALID_URGENCIES = {"exploring", "within_month", "urgent"}
VALID_RELATIONSHIPS = {"family_member", "self", "professional", "friend", "other"}


class EnquiryRequest(BaseModel):
    enquirer_name: str = Field(..., max_length=255)
    enquirer_email: EmailStr
    enquirer_phone: str | None = Field(None, max_length=20)
    relationship: str | None = Field(None, max_length=50)
    care_type: str | None = Field(None, max_length=100)
    urgency: str | None = Field("exploring", max_length=20)
    message: str = Field(..., max_length=5000)


@router.post("/providers/{slug}/enquire", status_code=201)
async def submit_enquiry(
    slug: str,
    req: EnquiryRequest,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Submit an enquiry about a care provider."""
    if req.urgency and req.urgency not in VALID_URGENCIES:
        raise HTTPException(status_code=422, detail=f"Invalid urgency. Choose from: {', '.join(VALID_URGENCIES)}")

    try:
        async with get_connection() as conn:
            provider = await conn.fetchrow(PROVIDER_ID_BY_SLUG, slug)
            if not provider:
                raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")

            row = await conn.fetchrow(
                INSERT_ENQUIRY,
                provider["id"],
                req.enquirer_name,
                req.enquirer_email,
                req.enquirer_phone,
                req.relationship,
                req.care_type,
                req.urgency,
                req.message,
            )

            await conn.execute(UPDATE_PROVIDER_ENQUIRY_COUNT, provider["id"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Enquiry submission failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Failed to submit enquiry.")

    return {
        "data": dict(row),
        "message": "Your enquiry has been sent. The provider will be in touch soon.",
    }
