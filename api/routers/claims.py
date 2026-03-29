"""Provider claiming endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.claims import (
    HAS_PENDING_CLAIM,
    INSERT_CLAIM,
    PROVIDER_ID_BY_SLUG,
)

logger = logging.getLogger("caregist.claims")
router = APIRouter(prefix="/api/v1", tags=["claims"])


class ClaimRequest(BaseModel):
    claimant_name: str = Field(..., max_length=255)
    claimant_email: EmailStr
    claimant_phone: str | None = Field(None, max_length=20)
    claimant_role: str = Field(..., max_length=100)
    organisation_name: str | None = Field(None, max_length=255)
    proof_of_association: str = Field(..., max_length=2000)


@router.post("/providers/{slug}/claim", status_code=201)
async def submit_claim(
    slug: str,
    req: ClaimRequest,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Submit a claim for a provider listing."""
    try:
        async with get_connection() as conn:
            provider = await conn.fetchrow(PROVIDER_ID_BY_SLUG, slug)
            if not provider:
                raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")

            if provider["is_claimed"]:
                raise HTTPException(status_code=409, detail="This provider has already been claimed.")

            existing = await conn.fetchrow(HAS_PENDING_CLAIM, provider["id"])
            if existing:
                raise HTTPException(status_code=409, detail="A claim is already pending for this provider.")

            row = await conn.fetchrow(
                INSERT_CLAIM,
                provider["id"],
                req.claimant_name,
                req.claimant_email,
                req.claimant_phone,
                req.claimant_role,
                req.organisation_name,
                req.proof_of_association,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Claim submission failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Failed to submit claim.")

    return {
        "data": dict(row),
        "message": "Claim submitted successfully. We'll review it within 2 business days.",
    }
