"""Internal, tenant-isolated CRM and fail-closed Twilio Voice endpoints."""

from __future__ import annotations

import json
import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from html import escape
from typing import Any, Literal
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field, model_validator

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_session_identity
from api.services.crm_calling import (
    TERMINAL_CALL_STATUSES,
    allowed_test_numbers,
    hash_call_authorization,
    hash_screening_number,
    map_twilio_status,
    normalize_e164,
    twilio_webhook_url,
    validate_twilio_call_sid,
    validate_twilio_request,
)
from api.services.tenant_context import OrganizationContext, resolve_organization_context, tenant_connection


router = APIRouter(prefix="/api/v1/crm", tags=["crm"])
MAX_TWILIO_WEBHOOK_BYTES = 64 * 1024
_OPEN_CALL_STATUSES = frozenset({"authorized", "initiated", "ringing", "in_progress"})


def close_status_for_disposition(status: str) -> str | None:
    """Return a terminal status to apply, or None when already terminal."""
    if status in TERMINAL_CALL_STATUSES:
        return None
    if status in _OPEN_CALL_STATUSES:
        return "failed"
    raise HTTPException(status_code=409, detail="A call can be dispositioned only after it ends.")


STAGES = (
    "new", "assigned", "attempting_contact", "connected", "qualified",
    "demo_booked", "proposal_sent", "negotiation", "won", "lost", "suppressed",
)


class ContactRequest(BaseModel):
    provider_id: str | None = Field(None, max_length=20)
    company_id: UUID | None = None
    first_name: str = Field("", max_length=120)
    last_name: str = Field("", max_length=120)
    job_title: str | None = Field(None, max_length=160)
    company_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    phone_e164: str | None = Field(None, max_length=20)

    model_config = {"extra": "forbid"}


class CompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str | None = Field(None, max_length=500)
    phone_e164: str | None = Field(None, max_length=20)
    address: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=4000)

    model_config = {"extra": "forbid"}


class TeamInviteRequest(BaseModel):
    email: EmailStr
    role: Literal["member", "admin"] = "member"

    model_config = {"extra": "forbid"}


class NoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    model_config = {"extra": "forbid"}


class TaskRequest(BaseModel):
    task_type: Literal["call", "email", "follow_up", "meeting", "general"] = "call"
    title: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(None, max_length=4000)
    due_at: datetime
    priority: Literal["low", "normal", "high"] = "normal"

    model_config = {"extra": "forbid"}


class StageRequest(BaseModel):
    stage: Literal[
        "new", "assigned", "attempting_contact", "connected", "qualified",
        "demo_booked", "proposal_sent", "negotiation", "won", "lost", "suppressed",
    ]

    model_config = {"extra": "forbid"}


class SuppressionRequest(BaseModel):
    channel: Literal["call", "email", "all"] = "call"
    reason: Literal["contact_objection", "tps", "ctps", "invalid", "legal", "manual"]
    evidence: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class DispositionRequest(BaseModel):
    disposition_group: Literal["no_contact", "connected", "callback", "do_not_call"]
    disposition: Literal[
        "connected", "no_answer", "busy", "voicemail", "wrong_number",
        "callback_requested", "gatekeeper", "qualified", "not_interested",
        "do_not_call", "meeting_booked", "sale_completed",
    ]
    callback_at: datetime | None = None
    notes: str | None = Field(None, max_length=4000)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_disposition_hierarchy(self) -> "DispositionRequest":
        allowed = {
            "no_contact": {"no_answer", "busy", "voicemail", "gatekeeper"},
            "connected": {
                "connected", "qualified", "not_interested", "meeting_booked", "sale_completed"
            },
            "callback": {"callback_requested"},
            "do_not_call": {"do_not_call", "wrong_number"},
        }
        if self.disposition not in allowed[self.disposition_group]:
            raise ValueError("The detailed disposition does not match its primary outcome.")
        if self.disposition == "callback_requested":
            if self.callback_at is None:
                raise ValueError("Callback date and time are required.")
            if self.callback_at.tzinfo is None:
                raise ValueError("Callback date and time must include a timezone.")
            callback_at = self.callback_at.astimezone(UTC)
            now = datetime.now(UTC)
            if callback_at <= now or callback_at > now + timedelta(days=365):
                raise ValueError("Callback date and time must be within the next 365 days.")
        elif self.callback_at is not None:
            raise ValueError("Callback date and time are allowed only for callback outcomes.")
        return self


def _require_crm_enabled() -> None:
    if not settings.crm_enabled:
        raise HTTPException(status_code=503, detail="The CareGist CRM is not enabled in this environment.")


def _require_calling_enabled() -> None:
    _require_crm_enabled()
    if not settings.crm_calling_enabled or not settings.outbound_communications_enabled:
        raise HTTPException(status_code=503, detail="CRM calling is awaiting its activation gate.")
    required = [
        settings.twilio_account_sid,
        settings.twilio_api_key_sid,
        settings.twilio_api_key_secret,
        settings.twilio_auth_token,
        settings.twilio_twiml_app_sid,
        settings.twilio_phone_number,
        settings.twilio_webhook_base_url,
    ]
    if settings.crm_pilot_mode:
        required.append(settings.crm_allowed_test_numbers)
    if not all(required):
        raise HTTPException(status_code=503, detail="CRM calling credentials and approved test numbers are incomplete.")


async def _context(auth: dict) -> OrganizationContext:
    _require_crm_enabled()
    if auth.get("auth_method") != "session" or not auth.get("user_id"):
        raise HTTPException(status_code=401, detail="A verified browser session is required for the CRM.")
    return await resolve_organization_context(int(auth["user_id"]), auth.get("tier", "free"))


async def _required_audit(
    conn: asyncpg.Connection,
    *,
    action: str,
    context: OrganizationContext,
    target_type: str,
    target_id: UUID,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write compliance-sensitive audit evidence in the caller's transaction."""
    await conn.execute(
        """
        INSERT INTO audit_log (
          action, outcome, actor_type, actor_user_id, target_type, target_id, metadata
        ) VALUES ($1, 'success', 'user', $2, $3, $4, $5::jsonb)
        """,
        action,
        context.user_id,
        target_type,
        str(target_id),
        json.dumps(metadata or {}),
    )


@asynccontextmanager
async def _twilio_connection():
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'twilio', true)")
            yield conn


@router.get("/summary")
async def summary(_auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    async with tenant_connection(context) as conn:
        counts = await conn.fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM crm_contacts WHERE organization_id = $1) AS contacts,
              (SELECT COUNT(*) FROM crm_companies WHERE organization_id = $1) AS companies,
              (SELECT COUNT(*) FROM crm_tasks WHERE organization_id = $1 AND status = 'open') AS open_tasks,
              (SELECT COUNT(*) FROM crm_deals WHERE organization_id = $1 AND stage = 'won') AS won_deals,
              (SELECT COUNT(*) FROM crm_call_sessions WHERE organization_id = $1) AS calls,
              (SELECT COUNT(*) FROM crm_email_campaigns WHERE organization_id = $1) AS campaigns
            """,
            context.organization_id,
        )
        contacts = await conn.fetch(
            """
            SELECT c.id, c.provider_id, c.company_id, c.first_name, c.last_name, c.job_title,
                   c.company_name, c.email, c.phone_e164, c.lifecycle_stage,
                   c.market_code, c.subscriber_type, c.email_marketing_basis,
                   c.phone_screening_status, c.phone_screened_at,
                   c.owner_user_id, c.updated_at,
                   cp.name AS provider_name, cp.slug AS provider_slug,
                   cp.region, cp.local_authority, cp.overall_rating,
                   EXISTS (
                     SELECT 1 FROM crm_suppressions s
                     WHERE s.organization_id = c.organization_id
                       AND s.phone_e164 = c.phone_e164
                       AND s.channel IN ('call', 'all')
                   ) AS call_suppressed
                   , EXISTS (
                     SELECT 1 FROM crm_suppressions s
                     WHERE s.organization_id = c.organization_id
                       AND LOWER(s.email) = LOWER(c.email)
                       AND s.channel IN ('email', 'all')
                   ) AS email_suppressed
            FROM crm_contacts c
            LEFT JOIN care_providers cp ON cp.id = c.provider_id
            WHERE c.organization_id = $1
            ORDER BY c.updated_at DESC
            LIMIT 100
            """,
            context.organization_id,
        )
        tasks = await conn.fetch(
            """
            SELECT t.id, t.contact_id, t.task_type, t.title, t.due_at, t.priority,
                   t.status, c.first_name, c.last_name, c.company_name,
                   cp.name AS provider_name
            FROM crm_tasks t
            JOIN crm_contacts c ON c.id = t.contact_id
            LEFT JOIN care_providers cp ON cp.id = c.provider_id
            WHERE t.organization_id = $1 AND t.status = 'open'
              AND (t.assigned_user_id = $2 OR t.assigned_user_id IS NULL OR $3 IN ('owner', 'admin'))
            ORDER BY t.due_at ASC
            LIMIT 100
            """,
            context.organization_id,
            context.user_id,
            context.role,
        )
        deals = await conn.fetch(
            """
            SELECT d.id, d.contact_id, d.title, d.stage, d.value_pence, d.loss_reason,
                   d.created_at, d.updated_at, d.closed_at,
                   c.first_name, c.last_name, c.company_name, cp.name AS provider_name
            FROM crm_deals d
            JOIN crm_contacts c ON c.id = d.contact_id
            LEFT JOIN care_providers cp ON cp.id = c.provider_id
            WHERE d.organization_id = $1
            ORDER BY d.updated_at DESC
            LIMIT 200
            """,
            context.organization_id,
        )
        recent_calls = await conn.fetch(
            """
            SELECT calls.id, calls.contact_id, calls.agent_user_id, calls.status,
                   calls.duration_seconds, calls.disposition, calls.started_at, calls.ended_at,
                   c.first_name, c.last_name, c.company_name, cp.name AS provider_name,
                   recording.id AS recording_id, recording.status AS recording_status,
                   intelligence.status AS intelligence_status,
                   COALESCE(NULLIF(users.name, ''), users.email) AS agent
            FROM crm_call_sessions calls
            JOIN crm_contacts c ON c.id = calls.contact_id
            JOIN users ON users.id = calls.agent_user_id
            LEFT JOIN care_providers cp ON cp.id = c.provider_id
            LEFT JOIN crm_recordings recording ON recording.call_session_id = calls.id
            LEFT JOIN crm_call_intelligence intelligence ON intelligence.call_session_id = calls.id
            WHERE calls.organization_id = $1
              AND (calls.agent_user_id = $2 OR $3 IN ('owner', 'admin'))
            ORDER BY calls.created_at DESC
            LIMIT 50
            """,
            context.organization_id, context.user_id, context.role,
        )
        pending_disposition_call = await conn.fetchrow(
            """
            SELECT id, contact_id, status
            FROM crm_call_sessions
            WHERE organization_id = $1 AND agent_user_id = $2
              AND status IN ('completed', 'busy', 'no_answer', 'failed', 'canceled')
              AND disposition IS NULL
            ORDER BY ended_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            context.organization_id, context.user_id,
        )
        companies = await conn.fetch(
            """
            SELECT id, name, website, phone_e164, address, notes, owner_user_id, updated_at
            FROM crm_companies
            WHERE organization_id = $1
            ORDER BY name
            LIMIT 500
            """,
            context.organization_id,
        )
    return {
        "role": context.role,
        "counts": dict(counts or {}),
        "contacts": [dict(row) for row in contacts],
        "companies": [dict(row) for row in companies],
        "tasks": [dict(row) for row in tasks],
        "deals": [dict(row) for row in deals],
        "recent_calls": [dict(row) for row in recent_calls],
        "pending_disposition_call": dict(pending_disposition_call)
        if pending_disposition_call else None,
        "calling": {
            "enabled": bool(settings.crm_calling_enabled and settings.outbound_communications_enabled),
            "recording_enabled": settings.crm_recording_enabled,
            "recording_retention_days": settings.crm_recording_retention_days,
            "test_numbers_only": settings.crm_pilot_mode,
        },
        "features": {
            "email_campaigns_enabled": settings.crm_email_campaigns_enabled,
            "uk_sms_enabled": False,
            "ai_enabled": settings.crm_ai_enabled,
        },
}


def _require_manager(context: OrganizationContext) -> None:
    if context.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="A CRM owner or administrator must approve this action.")


@router.get("/team/members")
async def list_team_members(_auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    _require_manager(context)
    async with tenant_connection(context) as conn:
        rows = await conn.fetch(
            """
            SELECT users.id, users.email, users.name, member.role, member.created_at
            FROM organization_members member
            JOIN users ON users.id = member.user_id
            WHERE member.organization_id = $1
            ORDER BY member.created_at ASC
            """,
            context.organization_id,
        )
    return {"data": [dict(row) for row in rows], "role": context.role}


@router.post("/team/members", status_code=201)
async def invite_team_member(
    body: TeamInviteRequest, _auth: dict = Depends(validate_session_identity)
) -> dict[str, Any]:
    context = await _context(_auth)
    _require_manager(context)
    email = str(body.email).strip().lower()
    if body.role == "admin" and context.role != "owner":
        raise HTTPException(status_code=403, detail="Only the workspace owner can grant administrator access.")
    async with tenant_connection(context) as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name FROM users WHERE LOWER(email) = $1",
            email,
        )
        if not user:
            raise HTTPException(
                status_code=404,
                detail="No CareGist login exists for that email. They must sign up first, then you can add them.",
            )
        if user["id"] == context.user_id:
            raise HTTPException(status_code=409, detail="You are already in this workspace.")
        existing = await conn.fetchval(
            "SELECT role FROM organization_members WHERE organization_id = $1 AND user_id = $2",
            context.organization_id,
            user["id"],
        )
        if existing:
            return {"id": user["id"], "email": user["email"], "role": existing, "already_member": True}
        await conn.execute(
            """
            INSERT INTO organization_members (organization_id, user_id, role)
            VALUES ($1, $2, $3)
            """,
            context.organization_id,
            user["id"],
            body.role,
        )
        await _required_audit(
            conn,
            action="crm.team.invite",
            context=context,
            target_type="organization",
            target_id=context.organization_id,
            metadata={"invited_user_id": user["id"], "role": body.role},
        )
    return {"id": user["id"], "email": user["email"], "role": body.role, "already_member": False}


@router.post("/companies", status_code=201)
async def create_company(
    body: CompanyRequest, _auth: dict = Depends(validate_session_identity)
) -> dict[str, Any]:
    context = await _context(_auth)
    name = body.name.strip()
    phone = normalize_e164(body.phone_e164)
    async with tenant_connection(context) as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO crm_companies (
                  organization_id, name, website, phone_e164, address, notes,
                  owner_user_id, created_by_user_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
                RETURNING *
                """,
                context.organization_id, name,
                body.website.strip() if body.website else None,
                phone,
                body.address.strip() if body.address else None,
                body.notes.strip() if body.notes else None,
                context.user_id,
            )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(status_code=409, detail="This company already exists in the CRM.") from exc
        await _required_audit(
            conn, action="crm.company.create", context=context,
            target_type="crm_company", target_id=row["id"],
        )
    return dict(row)


@router.patch("/companies/{company_id}")
async def update_company(
    company_id: UUID,
    body: CompanyRequest,
    _auth: dict = Depends(validate_session_identity),
) -> dict[str, Any]:
    context = await _context(_auth)
    phone = normalize_e164(body.phone_e164)
    async with tenant_connection(context) as conn:
        try:
            row = await conn.fetchrow(
                """
                UPDATE crm_companies SET name = $3, website = $4, phone_e164 = $5,
                  address = $6, notes = $7, updated_at = NOW()
                WHERE id = $1 AND organization_id = $2
                RETURNING *
                """,
                company_id, context.organization_id, body.name.strip(),
                body.website.strip() if body.website else None, phone,
                body.address.strip() if body.address else None,
                body.notes.strip() if body.notes else None,
            )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(status_code=409, detail="This company already exists in the CRM.") from exc
        if not row:
            raise HTTPException(status_code=404, detail="CRM company not found.")
        await conn.execute(
            "UPDATE crm_contacts SET company_name = $2, updated_at = NOW() WHERE company_id = $1",
            company_id, row["name"],
        )
        await _required_audit(
            conn, action="crm.company.update", context=context,
            target_type="crm_company", target_id=company_id,
        )
    return dict(row)


@router.post("/contacts", status_code=201)
async def create_contact(body: ContactRequest, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    phone = normalize_e164(body.phone_e164)
    if not body.provider_id and not body.email and not phone:
        raise HTTPException(status_code=422, detail="A provider, email address, or phone number is required.")
    async with tenant_connection(context) as conn:
        if body.provider_id and not await conn.fetchval("SELECT 1 FROM care_providers WHERE id = $1", body.provider_id):
            raise HTTPException(status_code=404, detail="CareGist provider not found.")
        company_id = body.company_id
        company_name = body.company_name.strip() if body.company_name else None
        if company_id:
            company = await conn.fetchrow(
                "SELECT id, name FROM crm_companies WHERE id = $1 AND organization_id = $2",
                company_id, context.organization_id,
            )
            if not company:
                raise HTTPException(status_code=404, detail="CRM company not found.")
            company_name = company["name"]
        elif company_name:
            company_id = await conn.fetchval(
                """
                INSERT INTO crm_companies (
                  organization_id, name, owner_user_id, created_by_user_id
                ) VALUES ($1, $2, $3, $3)
                ON CONFLICT (organization_id, LOWER(name)) DO UPDATE
                  SET updated_at = crm_companies.updated_at
                RETURNING id
                """,
                context.organization_id, company_name, context.user_id,
            )
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO crm_contacts (
                  organization_id, provider_id, company_id, owner_user_id, created_by_user_id,
                  first_name, last_name, job_title, company_name, email, phone_e164,
                  lifecycle_stage
                ) VALUES ($1, $2, $3, $4, $4, $5, $6, $7, $8, $9, $10, 'assigned')
                RETURNING *
                """,
                context.organization_id,
                body.provider_id,
                company_id,
                context.user_id,
                body.first_name.strip(),
                body.last_name.strip(),
                body.job_title.strip() if body.job_title else None,
                company_name,
                str(body.email).lower() if body.email else None,
                phone,
            )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(status_code=409, detail="This contact phone number or email already exists in the CRM.") from exc
        if phone and settings.crm_screening_hash_key:
            cached = await conn.fetchrow(
                """
                SELECT status, source, source_reference, screened_at
                FROM crm_phone_screening_cache
                WHERE organization_id = $1 AND phone_hmac = $2
                """,
                context.organization_id,
                hash_screening_number(phone, settings.crm_screening_hash_key),
            )
            if cached:
                await conn.execute(
                    """
                    UPDATE crm_contacts SET phone_screening_status = $2,
                      phone_screening_evidence = jsonb_build_object(
                        'source', $3::text, 'reference', $4::text, 'automatic', true
                      ), phone_screened_at = $5, updated_at = NOW()
                    WHERE id = $1
                    """,
                    row["id"], cached["status"], cached["source"],
                    cached["source_reference"], cached["screened_at"],
                )
                if cached["status"] in {"tps", "ctps", "invalid"}:
                    await conn.execute(
                        """
                        INSERT INTO crm_suppressions (
                          organization_id, phone_e164, channel, reason, evidence, created_by_user_id
                        ) VALUES ($1, $2, 'call', $3,
                          jsonb_build_object('source', $4::text, 'automatic', true), $5)
                        ON CONFLICT DO NOTHING
                        """,
                        context.organization_id, phone, cached["status"],
                        cached["source"], context.user_id,
                    )
        await conn.execute(
            """
            INSERT INTO crm_activities (organization_id, contact_id, actor_user_id, activity_type, metadata)
            VALUES ($1, $2, $3, 'contact_created', jsonb_build_object('provider_id', $4::text))
            """,
            context.organization_id,
            row["id"],
            context.user_id,
            body.provider_id,
        )
        await _required_audit(
            conn, action="crm.contact.create", context=context,
            target_type="crm_contact", target_id=row["id"],
        )
    return dict(row)


@router.get("/contacts/{contact_id}/timeline")
async def contact_timeline(contact_id: UUID, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    async with tenant_connection(context) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM crm_contacts WHERE id = $1 AND organization_id = $2",
            contact_id, context.organization_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        rows = await conn.fetch(
            """
            SELECT id, activity_type, body, metadata, actor_user_id, created_at
            FROM crm_activities
            WHERE organization_id = $1 AND contact_id = $2
            ORDER BY created_at DESC LIMIT 200
            """,
            context.organization_id, contact_id,
        )
    return {"data": [dict(row) for row in rows]}


@router.post("/contacts/{contact_id}/notes", status_code=201)
async def add_note(contact_id: UUID, body: NoteRequest, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    async with tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO crm_activities (organization_id, contact_id, actor_user_id, activity_type, body)
            SELECT $1, id, $3, 'note', $4 FROM crm_contacts
            WHERE id = $2 AND organization_id = $1
            RETURNING id, activity_type, body, created_at
            """,
            context.organization_id, contact_id, context.user_id, body.body.strip(),
        )
        if not row:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
    return dict(row)


@router.post("/contacts/{contact_id}/tasks", status_code=201)
async def create_task(contact_id: UUID, body: TaskRequest, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    due_at = body.due_at if body.due_at.tzinfo else body.due_at.replace(tzinfo=UTC)
    async with tenant_connection(context) as conn:
        contact = await conn.fetchrow(
            """
            SELECT c.id, c.phone_e164,
                   c.phone_screening_status IN ('tps', 'ctps', 'invalid') OR EXISTS (
                     SELECT 1 FROM crm_suppressions suppression
                     WHERE suppression.organization_id = c.organization_id
                       AND suppression.phone_e164 = c.phone_e164
                       AND suppression.channel IN ('call', 'all')
                   ) AS call_suppressed
            FROM crm_contacts c
            WHERE c.id = $1 AND c.organization_id = $2
            """,
            contact_id, context.organization_id,
        )
        if not contact:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        if body.task_type == "call" and (not contact["phone_e164"] or contact["call_suppressed"]):
            raise HTTPException(status_code=409, detail="A call task cannot be scheduled for this contact.")
        row = await conn.fetchrow(
            """
            INSERT INTO crm_tasks (
              organization_id, contact_id, assigned_user_id, created_by_user_id,
              task_type, title, notes, due_at, priority
            )
            VALUES ($1, $2, $3, $3, $4, $5, $6, $7, $8)
            RETURNING id, contact_id, task_type, title, due_at, priority, status, created_at
            """,
            context.organization_id, contact_id, context.user_id,
            body.task_type, body.title.strip(), body.notes, due_at, body.priority,
        )
        await conn.execute(
            """
            INSERT INTO crm_activities (organization_id, contact_id, actor_user_id, activity_type, body, metadata)
            VALUES ($1, $2, $3, 'task_created', $4, jsonb_build_object('task_id', $5::uuid, 'due_at', $6::timestamptz))
            """,
            context.organization_id, contact_id, context.user_id,
            body.title.strip(), row["id"], due_at,
        )
    return dict(row)


@router.patch("/contacts/{contact_id}/stage")
async def update_stage(contact_id: UUID, body: StageRequest, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    async with tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            UPDATE crm_contacts SET lifecycle_stage = $3, updated_at = NOW()
            WHERE id = $1 AND organization_id = $2
            RETURNING id, lifecycle_stage, updated_at
            """,
            contact_id, context.organization_id, body.stage,
        )
        if not row:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        await conn.execute(
            """
            INSERT INTO crm_activities (organization_id, contact_id, actor_user_id, activity_type, metadata)
            VALUES ($1, $2, $3, 'deal_stage_changed', jsonb_build_object('stage', $4::text))
            """,
            context.organization_id, contact_id, context.user_id, body.stage,
        )
    return dict(row)


@router.post("/contacts/{contact_id}/suppress", status_code=201)
async def suppress_contact(contact_id: UUID, body: SuppressionRequest, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await _context(_auth)
    async with tenant_connection(context) as conn:
        contact = await conn.fetchrow(
            "SELECT id, phone_e164, email FROM crm_contacts WHERE id = $1 AND organization_id = $2 FOR UPDATE",
            contact_id, context.organization_id,
        )
        if not contact:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        if body.channel == "call" and not contact["phone_e164"]:
            raise HTTPException(status_code=422, detail="The contact has no phone number to suppress.")
        if body.channel == "email" and not contact["email"]:
            raise HTTPException(status_code=422, detail="The contact has no email address to suppress.")
        channels = ("call", "email") if body.channel == "all" else (body.channel,)
        rows = []
        for channel in channels:
            identifier = contact["phone_e164"] if channel == "call" else contact["email"]
            if not identifier:
                continue
            row = await conn.fetchrow(
                """
                INSERT INTO crm_suppressions (
                  organization_id, phone_e164, email, channel, reason,
                  evidence, created_by_user_id
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                ON CONFLICT DO NOTHING
                RETURNING id, channel, reason, created_at
                """,
                context.organization_id,
                identifier if channel == "call" else None,
                identifier if channel == "email" else None,
                channel, body.reason, json.dumps(body.evidence), context.user_id,
            )
            if row:
                rows.append(dict(row))
        await conn.execute(
            "UPDATE crm_contacts SET lifecycle_stage = 'suppressed', updated_at = NOW() WHERE id = $1",
            contact_id,
        )
        await conn.execute(
            """
            INSERT INTO crm_activities (organization_id, contact_id, actor_user_id, activity_type, metadata)
            VALUES ($1, $2, $3, 'suppressed', jsonb_build_object('channel', $4::text, 'reason', $5::text))
            """,
            context.organization_id, contact_id, context.user_id, body.channel, body.reason,
        )
        await _required_audit(
            conn, action="crm.contact.suppress", context=context,
            target_type="crm_contact", target_id=contact_id,
            metadata={"channel": body.channel, "reason": body.reason},
        )
    return {
        "channel": body.channel,
        "reason": body.reason,
        "created": rows,
        "already_suppressed": not rows,
    }


@router.get("/twilio/token")
async def twilio_token(_auth: dict = Depends(validate_session_identity)) -> dict[str, str | int]:
    _require_calling_enabled()
    context = await _context(_auth)
    try:
        from twilio.jwt.access_token import AccessToken
        from twilio.jwt.access_token.grants import VoiceGrant
    except ImportError as exc:  # pragma: no cover - deployment dependency guard
        raise HTTPException(status_code=503, detail="Twilio runtime dependency is unavailable.") from exc
    ttl = 300
    token = AccessToken(
        settings.twilio_account_sid,
        settings.twilio_api_key_sid,
        settings.twilio_api_key_secret,
        identity=f"caregist-user-{context.user_id}",
        ttl=ttl,
        region=settings.twilio_region,
    )
    token.add_grant(VoiceGrant(outgoing_application_sid=settings.twilio_twiml_app_sid, incoming_allow=False))
    encoded = token.to_jwt()
    if isinstance(encoded, bytes):
        encoded = encoded.decode("utf-8")
    return {"token": encoded, "ttl": ttl, "edge": settings.twilio_edge}


async def _enforce_call_permission(
    conn: asyncpg.Connection,
    *,
    organization_id: UUID,
    phone: str,
    screening_status: str,
    screened_at: datetime | None,
) -> None:
    """Apply the same fail-closed gate at authorisation and actual dial time."""
    if settings.crm_pilot_mode:
        if phone not in allowed_test_numbers(settings.crm_allowed_test_numbers):
            raise HTTPException(status_code=403, detail="This pilot can call approved test numbers only.")
    else:
        if not phone.startswith("+44"):
            raise HTTPException(status_code=403, detail="The UK CRM can call +44 numbers only.")
        if settings.crm_screening_hash_key and screening_status != "consent_override":
            cached = await conn.fetchrow(
                """
                SELECT status, screened_at FROM crm_phone_screening_cache
                WHERE organization_id = $1 AND phone_hmac = $2
                """,
                organization_id,
                hash_screening_number(phone, settings.crm_screening_hash_key),
            )
            if cached and (not screened_at or cached["screened_at"] >= screened_at):
                screening_status = cached["status"]
                screened_at = cached["screened_at"]
        if (
            screening_status not in {"clear", "consent_override"}
            or not screened_at
            or screened_at < datetime.now(UTC) - timedelta(days=28)
        ):
            raise HTTPException(
                status_code=409,
                detail="TPS/CTPS screening evidence must be current before calling.",
            )
    suppressed = await conn.fetchval(
        """
        SELECT 1 FROM crm_suppressions
        WHERE organization_id = $1 AND phone_e164 = $2 AND channel IN ('call', 'all')
        LIMIT 1
        """,
        organization_id, phone,
    )
    if suppressed:
        raise HTTPException(status_code=409, detail="This contact is suppressed from calling.")


@router.post("/contacts/{contact_id}/calls/authorize", status_code=201)
async def authorize_call(contact_id: UUID, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    _require_calling_enabled()
    context = await _context(_auth)
    token = secrets.token_urlsafe(32)
    token_hash = hash_call_authorization(token)
    expires_at = datetime.now(UTC) + timedelta(minutes=2)
    async with tenant_connection(context) as conn:
        # Serialize per-agent authorization attempts. The unresolved-call query
        # alone is vulnerable to two concurrent transactions both observing no
        # row before either inserts one.
        await conn.execute(
            "SELECT pg_advisory_xact_lock($1, $2)",
            context.user_id, 0x43524D,
        )
        unresolved = await conn.fetchval(
            """
            SELECT 1 FROM crm_call_sessions
            WHERE organization_id = $1 AND agent_user_id = $2
              AND (
                (status = 'authorized' AND authorization_expires_at > NOW())
                OR status IN ('initiated', 'ringing', 'in_progress')
                OR (
                  status IN ('completed', 'busy', 'no_answer', 'failed', 'canceled')
                  AND disposition IS NULL
                )
              )
            LIMIT 1
            """,
            context.organization_id, context.user_id,
        )
        if unresolved:
            raise HTTPException(
                status_code=409,
                detail="Finish the active call and save its disposition before starting another call.",
            )
        contact = await conn.fetchrow(
            """
            SELECT id, phone_e164, phone_screening_status, phone_screened_at FROM crm_contacts
            WHERE id = $1 AND organization_id = $2 FOR UPDATE
            """,
            contact_id, context.organization_id,
        )
        if not contact:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        phone = contact["phone_e164"]
        if not phone:
            raise HTTPException(status_code=422, detail="The contact has no callable phone number.")
        await _enforce_call_permission(
            conn,
            organization_id=context.organization_id,
            phone=phone,
            screening_status=contact["phone_screening_status"],
            screened_at=contact["phone_screened_at"],
        )
        row = await conn.fetchrow(
            """
            INSERT INTO crm_call_sessions (
              organization_id, contact_id, agent_user_id,
              authorization_token_hash, authorization_expires_at, recording_notice_version
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, status, authorization_expires_at
            """,
            context.organization_id, contact_id, context.user_id, token_hash, expires_at,
            settings.crm_recording_notice_version if settings.crm_recording_enabled else None,
        )
        await _required_audit(
            conn, action="crm.call.authorize", context=context,
            target_type="crm_call", target_id=row["id"],
            metadata={
                "contact_id": str(contact_id),
                "test_number_only": settings.crm_pilot_mode,
                "recording": settings.crm_recording_enabled,
            },
        )
    return {**dict(row), "authorization": token}


async def _twilio_form(request: Request) -> dict[str, str]:
    raw_content_length = request.headers.get("content-length")
    try:
        content_length = int(raw_content_length or "")
    except ValueError as exc:
        raise HTTPException(status_code=413, detail="Twilio webhook body size is invalid.") from exc
    if content_length <= 0 or content_length > MAX_TWILIO_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Twilio webhook body exceeds the approved size limit.")
    raw_body = await request.body()
    if not raw_body or len(raw_body) > MAX_TWILIO_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Twilio webhook body exceeds the approved size limit.")
    form = await request.form()
    return {str(key): str(value) for key, value in form.multi_items()}


def _validate_twilio(request: Request, form: dict[str, str]) -> None:
    public_url = twilio_webhook_url(settings.twilio_webhook_base_url, request.url.path)
    if request.url.query:
        public_url += "?" + request.url.query
    validate_twilio_request(
        auth_token=settings.twilio_auth_token,
        signature=request.headers.get("X-Twilio-Signature"),
        url=public_url,
        form=form,
    )
    if form.get("AccountSid") != settings.twilio_account_sid:
        raise HTTPException(status_code=401, detail="Twilio account does not match this CareGist environment.")


@router.post("/twilio/voice")
async def twilio_voice(request: Request) -> Response:
    _require_calling_enabled()
    form = await _twilio_form(request)
    _validate_twilio(request, form)
    authorization = form.get("authorization", "")
    token_hash = hash_call_authorization(authorization)
    parent_call_sid = validate_twilio_call_sid(form.get("CallSid", ""))
    async with _twilio_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT calls.id, calls.organization_id, calls.contact_id, contacts.phone_e164,
                   contacts.phone_screening_status, contacts.phone_screened_at
            FROM crm_call_sessions calls
            JOIN crm_contacts contacts ON contacts.id = calls.contact_id
            WHERE calls.authorization_token_hash = $1
              AND calls.authorization_consumed_at IS NULL
              AND calls.authorization_expires_at > NOW()
              AND calls.status = 'authorized'
            FOR UPDATE OF calls
            """,
            token_hash,
        )
        if not row:
            raise HTTPException(status_code=409, detail="Call authorization is invalid, expired, or already used.")
        await conn.fetchrow(
            "SELECT id FROM crm_contacts WHERE id = $1 FOR UPDATE",
            row["contact_id"],
        )
        await _enforce_call_permission(
            conn,
            organization_id=row["organization_id"],
            phone=row["phone_e164"],
            screening_status=row["phone_screening_status"],
            screened_at=row["phone_screened_at"],
        )
        await conn.execute(
            """
            UPDATE crm_call_sessions
            SET authorization_consumed_at = NOW(), status = 'initiated',
                twilio_parent_call_sid = $2, started_at = NOW(), updated_at = NOW()
            WHERE id = $1
            """,
            row["id"], parent_call_sid,
        )
    callback = twilio_webhook_url(
        settings.twilio_webhook_base_url,
        f"/api/v1/crm/twilio/calls/{row['id']}/status",
    )
    recording_attributes = ' record="do-not-record"'
    number_attributes = ""
    if settings.crm_recording_enabled:
        recording_callback = twilio_webhook_url(
            settings.twilio_webhook_base_url,
            f"/api/v1/crm/twilio/calls/{row['id']}/recording",
        )
        notice_callback = twilio_webhook_url(
            settings.twilio_webhook_base_url,
            "/api/v1/crm/twilio/recording-notice",
        )
        recording_attributes = (
            ' record="record-from-answer-dual" recordingStatusCallbackEvent="completed"'
            f' recordingStatusCallback="{escape(recording_callback, quote=True)}"'
            ' recordingStatusCallbackMethod="POST"'
        )
        number_attributes = f' url="{escape(notice_callback, quote=True)}" method="POST"'
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Dial callerId="{escape(settings.twilio_phone_number, quote=True)}"{recording_attributes}>'
        '<Number statusCallbackEvent="initiated ringing answered completed" '
        f'statusCallback="{escape(callback, quote=True)}" statusCallbackMethod="POST"{number_attributes}>'
        f'{escape(row["phone_e164"])}</Number></Dial></Response>'
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/twilio/calls/{call_session_id}/status")
async def twilio_call_status(call_session_id: UUID, request: Request) -> dict[str, bool]:
    _require_calling_enabled()
    form = await _twilio_form(request)
    _validate_twilio(request, form)
    call_sid = validate_twilio_call_sid(form.get("CallSid", ""))
    try:
        sequence = int(form.get("SequenceNumber", "-1"))
        duration = int(form["CallDuration"]) if form.get("CallDuration") else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Twilio callback sequence or duration is invalid.") from exc
    if sequence < 0 or (duration is not None and duration < 0):
        raise HTTPException(status_code=422, detail="Twilio callback sequence or duration is invalid.")
    status = map_twilio_status(form.get("CallStatus"))
    async with _twilio_connection() as conn:
        call = await conn.fetchrow(
            """
            SELECT id, organization_id, contact_id, twilio_child_call_sid, last_sequence_number
            FROM crm_call_sessions WHERE id = $1 FOR UPDATE
            """,
            call_session_id,
        )
        if not call:
            raise HTTPException(status_code=404, detail="CRM call session not found.")
        if call["twilio_child_call_sid"] and call["twilio_child_call_sid"] != call_sid:
            raise HTTPException(status_code=409, detail="Twilio callback does not match this call session.")
        inserted = await conn.fetchval(
            """
            INSERT INTO crm_call_events (
              call_session_id, twilio_call_sid, sequence_number, event_status, duration_seconds
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (twilio_call_sid, sequence_number) DO NOTHING
            RETURNING id
            """,
            call_session_id, call_sid, sequence, status, duration,
        )
        advanced = bool(inserted) and sequence > call["last_sequence_number"]
        if inserted:
            await conn.execute(
                """
                UPDATE crm_call_sessions SET
                  twilio_child_call_sid = COALESCE(twilio_child_call_sid, $2),
                  status = CASE WHEN $3 > last_sequence_number THEN $4 ELSE status END,
                  last_sequence_number = GREATEST(last_sequence_number, $3),
                  answered_at = CASE WHEN $3 > last_sequence_number AND $4 = 'in_progress'
                                     THEN COALESCE(answered_at, NOW()) ELSE answered_at END,
                  ended_at = CASE WHEN $3 > last_sequence_number AND $4 IN ('completed','busy','no_answer','failed','canceled')
                                  THEN NOW() ELSE ended_at END,
                  duration_seconds = CASE WHEN $3 > last_sequence_number THEN COALESCE($5, duration_seconds)
                                          ELSE duration_seconds END,
                  updated_at = NOW()
                WHERE id = $1
                """,
                call_session_id, call_sid, sequence, status, duration,
            )
            if advanced and status in {"completed", "busy", "no_answer", "failed", "canceled"}:
                await conn.execute(
                    """
                    INSERT INTO crm_activities (
                      organization_id, contact_id, activity_type, metadata
                    ) VALUES ($1, $2, 'call', jsonb_build_object(
                      'call_session_id', $3::uuid, 'status', $4::text, 'duration_seconds', $5::int
                    ))
                    """,
                    call["organization_id"], call["contact_id"], call_session_id, status, duration,
                )
    return {"accepted": True, "duplicate": not bool(inserted)}


@router.post("/calls/{call_session_id}/disposition")
async def record_disposition(
    call_session_id: UUID,
    body: DispositionRequest,
    _auth: dict = Depends(validate_session_identity),
) -> dict[str, Any]:
    context = await _context(_auth)
    async with tenant_connection(context) as conn:
        call = await conn.fetchrow(
            """
            SELECT calls.id, calls.contact_id, calls.agent_user_id, calls.status,
                   calls.disposition,
                   contacts.phone_e164
            FROM crm_call_sessions calls
            JOIN crm_contacts contacts ON contacts.id = calls.contact_id
            WHERE calls.id = $1 AND calls.organization_id = $2 FOR UPDATE OF calls
            """,
            call_session_id, context.organization_id,
        )
        if not call:
            raise HTTPException(status_code=404, detail="CRM call session not found.")
        if call["agent_user_id"] != context.user_id and context.role not in {"owner", "admin"}:
            raise HTTPException(status_code=403, detail="Only the calling agent or a manager can disposition this call.")
        if call["status"] not in TERMINAL_CALL_STATUSES:
            closed = close_status_for_disposition(call["status"])
            if closed:
                await conn.execute(
                    """
                    UPDATE crm_call_sessions
                    SET status = $2, ended_at = COALESCE(ended_at, NOW()), updated_at = NOW()
                    WHERE id = $1 AND status NOT IN ('completed', 'busy', 'no_answer', 'failed', 'canceled')
                    """,
                    call_session_id,
                    closed,
                )
        if call["disposition"] is not None:
            raise HTTPException(status_code=409, detail="This call already has an operator disposition.")
        await conn.execute(
            """
            UPDATE crm_call_sessions SET disposition_group = $2, disposition = $3,
              callback_due_at = $4, notes = $5, dispositioned_at = NOW(), updated_at = NOW()
            WHERE id = $1
            """,
            call_session_id, body.disposition_group, body.disposition,
            body.callback_at.astimezone(UTC) if body.callback_at else None, body.notes,
        )
        if body.disposition in {"do_not_call", "wrong_number"}:
            suppression_reason = "contact_objection" if body.disposition == "do_not_call" else "invalid"
            await conn.execute(
                """
                INSERT INTO crm_suppressions (
                  organization_id, phone_e164, channel, reason, evidence, created_by_user_id
                ) VALUES ($1, $2, 'call', $3,
                          jsonb_build_object('call_session_id', $4::uuid), $5)
                ON CONFLICT DO NOTHING
                """,
                context.organization_id, call["phone_e164"], suppression_reason,
                call_session_id, context.user_id,
            )
            await conn.execute(
                "UPDATE crm_contacts SET lifecycle_stage = 'suppressed', updated_at = NOW() WHERE id = $1",
                call["contact_id"],
            )
        stage_by_disposition = {
            "connected": "connected",
            "no_answer": "attempting_contact",
            "busy": "attempting_contact",
            "voicemail": "attempting_contact",
            "gatekeeper": "attempting_contact",
            "qualified": "qualified",
            "meeting_booked": "demo_booked",
            "sale_completed": "won",
            "not_interested": "lost",
        }
        if body.disposition in stage_by_disposition:
            await conn.execute(
                "UPDATE crm_contacts SET lifecycle_stage = $2, updated_at = NOW() WHERE id = $1",
                call["contact_id"], stage_by_disposition[body.disposition],
            )
        if body.disposition == "callback_requested":
            await conn.execute(
                """
                INSERT INTO crm_tasks (
                  organization_id, contact_id, assigned_user_id, created_by_user_id,
                  task_type, title, due_at, priority
                ) VALUES ($1, $2, $3, $4, 'call', 'Requested callback', $5, 'high')
                """,
                context.organization_id, call["contact_id"], call["agent_user_id"],
                context.user_id, body.callback_at.astimezone(UTC),
            )
        await _required_audit(
            conn, action="crm.call.disposition", context=context,
            target_type="crm_call", target_id=call_session_id,
            metadata={
                "disposition_group": body.disposition_group,
                "disposition": body.disposition,
                "callback_at": body.callback_at.astimezone(UTC).isoformat()
                if body.callback_at else None,
            },
        )
    return {"id": call_session_id, "disposition": body.disposition}
