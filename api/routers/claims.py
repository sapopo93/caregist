"""Provider claiming endpoints — two-gate claim verification.

Gate 1: user email domain matches provider CQC-listed website domain → auto-approve.
Gate 2: domain mismatch → enqueue for admin manual review (status = 'pending_review').
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.queries.claims import (
    GET_CLAIM_STATUS,
    HAS_PENDING_CLAIM,
    INSERT_CLAIM,
    PROVIDER_ID_BY_SLUG,
    AUTO_APPROVE_CLAIM,
    SET_CLAIM_PENDING_REVIEW,
)
from api.utils.audit import write_audit_log

logger = logging.getLogger("caregist.claims")
router = APIRouter(prefix="/api/v1", tags=["claims"])


def _extract_domain(email: str) -> str:
    """Return the lowercased post-@ portion of an email address."""
    return email.split("@", 1)[-1].lower()


def _extract_website_domain(website: str | None) -> str | None:
    """Parse a website URL and return its bare hostname without www. prefix.

    Handles:
    - https://www.example.com/path → example.com
    - http://example.com          → example.com
    - www.example.com             (no scheme) → example.com
    - None / empty                → None
    """
    if not website:
        return None
    url = website.strip()
    if not url:
        return None
    # Prepend scheme if missing so urlparse works correctly.
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return None
    hostname = hostname.lower()
    # Strip leading www. (single level only — www2. etc. are not stripped).
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname or None


def _domains_match(user_domain: str, provider_domain: str) -> bool:
    """Return True if the user's email domain matches or is a subdomain of the provider domain.

    Examples:
    - user_domain="acme.co.uk",     provider_domain="acme.co.uk"     → True (exact)
    - user_domain="care.acme.co.uk", provider_domain="acme.co.uk"    → True (subdomain)
    - user_domain="acme.co.uk",     provider_domain="notacme.co.uk"  → False
    - user_domain="gmail.com",      provider_domain="acme.co.uk"     → False
    """
    if user_domain == provider_domain:
        return True
    # Subdomain: user_domain must end with ".<provider_domain>"
    return user_domain.endswith("." + provider_domain)


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
    """Submit a claim for a provider listing — two-gate domain-verification flow.

    Gate 1 (auto-approve): claimant email domain matches the provider's CQC-listed
    website domain (exact match or subdomain). The claim is immediately approved and
    the provider is marked as claimed.

    Gate 2 (manual review): domain mismatch or missing website → claim queued at
    'pending_review' for admin moderation.
    """
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

            # --- Two-gate domain verification ---
            user_domain = _extract_domain(str(req.claimant_email))
            provider_domain = _extract_website_domain(provider.get("website"))

            if provider_domain and _domains_match(user_domain, provider_domain):
                # Gate 1: auto-approve
                gate = "auto_approved"
                review_reason = f"Email domain '{user_domain}' matched CQC website domain '{provider_domain}'"
                row = await conn.fetchrow(
                    INSERT_CLAIM,
                    provider["id"],
                    req.claimant_name,
                    str(req.claimant_email),
                    req.claimant_phone,
                    req.claimant_role,
                    req.organisation_name,
                    req.proof_of_association,
                    req.fast_track,
                    "approved",
                    review_reason,
                )
                # Mark the provider as claimed immediately.
                await conn.execute(
                    "UPDATE care_providers SET is_claimed = true, claimed_at = NOW() WHERE id = $1",
                    provider["id"],
                )
                await write_audit_log(
                    action="CLAIM_AUTO_APPROVED",
                    outcome="success",
                    actor={"type": "system", "email": str(req.claimant_email)},
                    target_type="provider_claim",
                    target_id=row["id"],
                    metadata={
                        "user_domain": user_domain,
                        "provider_domain": provider_domain,
                        "provider_id": provider["id"],
                    },
                    conn=conn,
                )
            else:
                # Gate 2: queue for admin review
                gate = "pending_review"
                if not provider_domain:
                    review_reason = "Provider has no CQC-listed website — domain match not possible"
                else:
                    review_reason = (
                        f"Email domain '{user_domain}' does not match CQC website domain '{provider_domain}'"
                    )
                row = await conn.fetchrow(
                    INSERT_CLAIM,
                    provider["id"],
                    req.claimant_name,
                    str(req.claimant_email),
                    req.claimant_phone,
                    req.claimant_role,
                    req.organisation_name,
                    req.proof_of_association,
                    req.fast_track,
                    "pending_review",
                    review_reason,
                )
                await write_audit_log(
                    action="CLAIM_QUEUED_FOR_REVIEW",
                    outcome="success",
                    actor={"type": "system", "email": str(req.claimant_email)},
                    target_type="provider_claim",
                    target_id=row["id"],
                    metadata={
                        "user_domain": user_domain,
                        "provider_domain": provider_domain,
                        "provider_id": provider["id"],
                        "reason": review_reason,
                    },
                    conn=conn,
                )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Claim submission failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Failed to submit claim.")

    # Queue claim email sequence (idempotent per provider + email).
    try:
        from api.utils.analytics import log_event
        from api.utils.email_queue import queue_email
        from datetime import datetime, timedelta, timezone

        await log_event(
            "claim_submitted",
            "provider",
            email=str(req.claimant_email),
            provider_id=provider["id"],
            meta={"crm_state": "provider_acquisition_lead", "gate": gate},
        )
        now = datetime.now(timezone.utc)
        provider_name = slug.replace("-", " ").title()
        claim_key = f"claim:{provider['id']}:{req.claimant_email}"

        if gate == "auto_approved":
            day0_subject = f"Your claim for {provider_name} has been approved"
            day0_body = (
                f" Hi {req.claimant_name}, "
                f" Great news — your claim for {provider_name} on CareGist has been "
                f"automatically approved based on your verified domain. Your listing is now active. "
                f" — The CareGist Team "
            )
        else:
            day0_subject = f"Claim received for {provider_name} — pending admin review"
            day0_body = (
                f" Hi {req.claimant_name}, "
                f" We've received your claim for {provider_name} on CareGist. "
                f"Our team will review it and get back to you within 1–2 business days. "
                f" — The CareGist Team "
            )

        await queue_email(
            str(req.claimant_email),
            day0_subject,
            day0_body,
            idempotency_key=f"{claim_key}:day0",
        )
        # Day 3: benchmark report prompt
        await queue_email(
            str(req.claimant_email),
            f"{provider_name} vs local average — your benchmark report",
            (
                f" Hi {req.claimant_name}, "
                f" Your claim for {provider_name} is being reviewed. In the meantime, "
                f"see how your provider compares to the local average: "
                f" View provider profile → "
            ),
            send_after=now + timedelta(days=3),
            idempotency_key=f"{claim_key}:day3",
        )
        # Day 7: upgrade prompt
        await queue_email(
            str(req.claimant_email),
            "Unlock visibility analytics for your listing",
            (
                f" Hi {req.claimant_name}, "
                f" Upgrade your claimed listing to unlock richer profile content, "
                f"competitor benchmarking, and higher-visibility placement for {provider_name}. "
                f" See provider plans → "
            ),
            send_after=now + timedelta(days=7),
            idempotency_key=f"{claim_key}:day7",
        )
    except Exception:
        pass

    if gate == "auto_approved":
        message = "Your claim has been automatically approved — your email domain matches this provider's registered website."
    else:
        message = "Claim submitted successfully. Our team will review it within 1–2 business days."

    return {
        "data": dict(row),
        "gate": gate,
        "message": message,
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
