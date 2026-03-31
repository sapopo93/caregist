"""API access application endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.database import get_connection
from api.middleware.ip_rate_limit import check_public_rate_limit
from api.queries.api_applications import INSERT_APPLICATION
from api.utils.analytics import log_event
from api.utils.email_queue import queue_email

logger = logging.getLogger("caregist.api_applications")
router = APIRouter(prefix="/api/v1", tags=["api-applications"])


class ApiApplicationRequest(BaseModel):
    company_name: str = Field(..., max_length=255)
    contact_name: str = Field(..., max_length=255)
    contact_email: EmailStr
    use_case: str = Field(..., max_length=5000)
    expected_volume: str | None = Field(None, max_length=50)


@router.post("/api-applications", status_code=201)
async def submit_api_application(
    req: ApiApplicationRequest,
    _ip=Depends(check_public_rate_limit),
) -> dict:
    """Submit an API access application."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(
                INSERT_APPLICATION,
                req.company_name,
                req.contact_name,
                req.contact_email,
                req.use_case,
                req.expected_volume,
            )
    except Exception as exc:
        logger.error("API application failed: %s", exc)
        raise HTTPException(status_code=503, detail="Application submission failed.")

    await log_event(
        "api_application",
        "api_landing",
        email=req.contact_email,
        meta={"company": req.company_name, "volume": req.expected_volume, "crm_state": "enterprise_data_prospect"},
    )

    await queue_email(
        req.contact_email,
        "CareGist API — Application Received",
        f"<p>Hi {req.contact_name},</p>"
        f"<p>Thanks for applying for CareGist API access. We'll review your application within 48 hours.</p>"
        f"<p>Company: {req.company_name}<br>Use case: {req.use_case[:200]}</p>"
        f"<p>— The CareGist Team</p>",
    )

    return {
        "data": dict(row) if row else {},
        "message": "Application received. We'll be in touch within 2 business days.",
    }
