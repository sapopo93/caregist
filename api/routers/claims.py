"""Provider claiming endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.claims import (
    GET_CLAIM_STATUS,
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
    fast_track: bool = False


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
                req.fast_track,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Claim submission failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Failed to submit claim.")

    # Queue claim email sequence.
    # Idempotency keys are scoped to (provider_id, email) so that retried
    # submissions or concurrent requests do not deliver duplicate drip emails.
    try:
        from api.utils.analytics import log_event
        from api.utils.email_queue import queue_email
        from datetime import datetime, timedelta, timezone
        await log_event("claim_submitted", "provider", email=req.claimant_email, provider_id=provider["id"], meta={"crm_state": "provider_acquisition_lead"})
        now = datetime.now(timezone.utc)
        provider_name = slug.replace("-", " ").title()
        claim_key = f"claim:{provider['id']}:{req.claimant_email}"
        await queue_email(
            req.claimant_email,
            f"Claim received for {provider_name}",
            f"<p>Hi {req.claimant_name},</p>"
            f"<p>We've received your claim for <strong>{provider_name}</strong> on CareGist. "
            f"We'll review it within {'24 hours (fast-track)' if req.fast_track else '24–48 hours'}.</p>"
            f"<p>— The CareGist Team</p>",
            idempotency_key=f"{claim_key}:day0",
        )
        # Day 3: benchmark report prompt
        await queue_email(
            req.claimant_email,
            f"{provider_name} vs local average — your benchmark report",
            f"<p>Hi {req.claimant_name},</p>"
            f"<p>Your claim for {provider_name} is being reviewed. In the meantime, "
            f"see how your provider compares to the local average:</p>"
            f"<p><a href='https://caregist.co.uk/provider/{slug}'>View provider profile →</a></p>",
            send_after=now + timedelta(days=3),
            idempotency_key=f"{claim_key}:day3",
        )
        # Day 7: upgrade prompt
        await queue_email(
            req.claimant_email,
            "Unlock visibility analytics for your listing",
            f"<p>Hi {req.claimant_name},</p>"
            f"<p>Upgrade your claimed listing to unlock richer profile content, "
            f"competitor benchmarking, and higher-visibility placement for {provider_name}.</p>"
            f"<p><a href='https://caregist.co.uk/pricing#provider-plans'>See provider plans →</a></p>",
            send_after=now + timedelta(days=7),
            idempotency_key=f"{claim_key}:day7",
        )
    except Exception:
        pass

    return {
        "data": dict(row),
        "message": "Claim submitted successfully. We'll review it within 2 business days.",
    }


@router.get("/claims/my-providers")
async def my_claimed_providers(auth: dict = Depends(validate_api_key)) -> dict:
    """Return approved claimed providers for the authenticated user."""
    email = auth.get("email")
    if not email or not auth.get("user_id"):
        raise HTTPException(status_code=401, detail="User account required.")
    try:
        async with get_connection() as conn:
            rows = await conn.fetch(
                """SELECT cp.id, cp.slug, cp.name, cp.profile_tier
                   FROM provider_claims pc
                   JOIN care_providers cp ON cp.id = pc.provider_id
                   WHERE pc.claimant_email = $1 AND pc.status = 'approved' AND cp.is_claimed = true
                   ORDER BY pc.created_at""",
                email,
            )
    except Exception as exc:
        logger.error("my_claimed_providers failed: %s", exc)
        raise HTTPException(status_code=503, detail="Failed to load claimed providers.")
    return {"providers": [dict(r) for r in rows]}


@router.get("/providers/{slug}/claim-status")
async def claim_status(
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Check claim status for a provider (by the authenticated user's email)."""
    claimant_email = _auth.get("email")
    if not claimant_email:
        return {"data": None}

    try:
        async with get_connection() as conn:
            provider = await conn.fetchrow(PROVIDER_ID_BY_SLUG, slug)
            if not provider:
                raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")
            row = await conn.fetchrow(GET_CLAIM_STATUS, claimant_email, provider["id"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Claim status check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Failed to check claim status.")

    return {"data": dict(row) if row else None}
