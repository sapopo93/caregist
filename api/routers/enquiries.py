"""Enquiry (lead-gen) endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_api_key
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

    provider_name = slug  # fallback
    try:
        async with get_connection() as conn:
            provider = await conn.fetchrow(
                "SELECT id, name, is_claimed FROM care_providers WHERE slug = $1", slug,
            )
            if not provider:
                raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")

            provider_data = dict(provider)
            provider_name = provider_data.get("name") or slug

            row = await conn.fetchrow(
                INSERT_ENQUIRY,
                provider_data["id"],
                req.enquirer_name,
                req.enquirer_email,
                req.enquirer_phone,
                req.relationship,
                req.care_type,
                req.urgency,
                req.message,
            )

            await conn.execute(UPDATE_PROVIDER_ENQUIRY_COUNT, provider_data["id"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Enquiry submission failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Failed to submit enquiry.")

    # Send confirmation email (best-effort, never crashes the request)
    await _send_enquiry_confirmation(req.enquirer_name, req.enquirer_email, provider_name)

    return {
        "data": dict(row),
        "message": "Your enquiry has been sent. The provider will be in touch soon.",
    }


async def _send_enquiry_confirmation(name: str, email: str, provider_name: str) -> None:
    """Send a confirmation email via Resend. Fails silently."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — skipping enquiry confirmation email")
        return

    from_email = settings.enquiry_from_email or "noreply@caregist.co.uk"
    subject = f"Your enquiry about {provider_name} has been received"
    body = (
        f"Hi {name},\n\n"
        f"Thank you for your enquiry about {provider_name}. "
        f"We've passed your details on and they'll be in touch soon.\n\n"
        f"If you have any questions in the meantime, just reply to this email.\n\n"
        f"Best wishes,\nThe CareGist Team"
    )

    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": from_email,
                    "to": [email],
                    "subject": subject,
                    "text": body,
                },
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error("Resend API error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Failed to send enquiry confirmation email: %s", exc)
