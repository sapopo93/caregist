"""Full UK CRM modules layered on the isolated CRM foundation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import PurePath
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_session_identity
from api.routers import crm
from api.services.crm_campaigns import (
    MAX_CAMPAIGN_RECIPIENTS,
    create_unsubscribe_token,
    hash_unsubscribe_token,
    is_email_marketing_eligible,
    render_campaign_html,
)
from api.services.crm_email_events import (
    HANDLED_EMAIL_EVENTS,
    resend_event_occurred_at,
    verify_resend_webhook,
)
from api.services.crm_recordings import (
    presign_recording,
    recording_object_key,
    validate_twilio_recording_sid,
)


router = APIRouter(prefix="/api/v1/crm", tags=["crm"])

MAX_SCREENING_IMPORT_BYTES = 5 * 1024 * 1024
MAX_SCREENING_IMPORT_ROWS = 20_000


class MarketingPreferenceRequest(BaseModel):
    subscriber_type: Literal["corporate", "sole_trader", "partnership", "individual", "unknown"]
    email_marketing_basis: Literal["corporate_subscriber", "consent", "soft_opt_in", "none"]
    evidence: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class PhoneScreeningRequest(BaseModel):
    status: Literal["clear", "tps", "ctps", "consent_override"]
    source: Literal["tps_ctps_licence", "approved_provider", "specific_consent"]
    source_reference: str = Field(min_length=1, max_length=500)
    screened_at: datetime

    model_config = {"extra": "forbid"}


class DealRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    value_pence: int = Field(default=0, ge=0, le=100_000_000)

    model_config = {"extra": "forbid"}


class DealStageRequest(BaseModel):
    stage: Literal[
        "new", "assigned", "attempting_contact", "connected", "qualified",
        "demo_booked", "proposal_sent", "negotiation", "won", "lost", "suppressed",
    ]
    loss_reason: str | None = Field(default=None, max_length=255)

    model_config = {"extra": "forbid"}


class CampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    subject: str = Field(min_length=1, max_length=500)
    body_text: str = Field(min_length=1, max_length=20_000)

    model_config = {"extra": "forbid"}


class CampaignLaunchRequest(BaseModel):
    contact_ids: list[UUID] = Field(min_length=1, max_length=MAX_CAMPAIGN_RECIPIENTS)
    confirm_send: bool

    model_config = {"extra": "forbid"}


def _require_manager(context) -> None:
    if context.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="A CRM owner or administrator must approve this action.")


def _require_campaigns_enabled() -> None:
    crm._require_crm_enabled()
    if not settings.crm_email_campaigns_enabled or not settings.outbound_communications_enabled:
        raise HTTPException(status_code=503, detail="CRM email campaigns are awaiting their activation gate.")
    if not settings.resend_api_key:
        raise HTTPException(status_code=503, detail="The email delivery provider is not configured.")


def _bounded_evidence(evidence: dict[str, str]) -> dict[str, str]:
    if len(evidence) > 10:
        raise HTTPException(status_code=422, detail="Marketing evidence must contain at most 10 fields.")
    cleaned: dict[str, str] = {}
    for raw_key, raw_value in evidence.items():
        key = raw_key.strip()
        value = raw_value.strip()
        if not key or len(key) > 80 or not value or len(value) > 500:
            raise HTTPException(status_code=422, detail="Marketing evidence contains an invalid field.")
        cleaned[key] = value
    return cleaned


@router.patch("/contacts/{contact_id}/marketing")
async def update_marketing_preference(
    contact_id: UUID,
    body: MarketingPreferenceRequest,
    _auth: dict = Depends(validate_session_identity),
) -> dict[str, Any]:
    context = await crm._context(_auth)
    evidence = _bounded_evidence(body.evidence)
    if body.email_marketing_basis == "corporate_subscriber" and body.subscriber_type != "corporate":
        raise HTTPException(status_code=422, detail="Corporate-subscriber basis requires a corporate subscriber.")
    if body.email_marketing_basis != "none" and not evidence:
        raise HTTPException(status_code=422, detail="Record concise evidence for the selected marketing basis.")
    async with crm.tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            UPDATE crm_contacts SET
              subscriber_type = $3, email_marketing_basis = $4,
              email_marketing_evidence = $5::jsonb,
              email_marketing_recorded_at = CASE WHEN $4 = 'none' THEN NULL ELSE NOW() END,
              updated_at = NOW()
            WHERE id = $1 AND organization_id = $2
            RETURNING id, subscriber_type, email_marketing_basis, email_marketing_recorded_at
            """,
            contact_id, context.organization_id, body.subscriber_type,
            body.email_marketing_basis, json.dumps(evidence),
        )
        if not row:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        await crm._required_audit(
            conn, action="crm.contact.marketing_basis", context=context,
            target_type="crm_contact", target_id=contact_id,
            metadata={"subscriber_type": body.subscriber_type, "basis": body.email_marketing_basis},
        )
    return dict(row)


@router.patch("/contacts/{contact_id}/phone-screening")
async def update_phone_screening(
    contact_id: UUID,
    body: PhoneScreeningRequest,
    _auth: dict = Depends(validate_session_identity),
) -> dict[str, Any]:
    context = await crm._context(_auth)
    _require_manager(context)
    if len(settings.crm_screening_hash_key) < 32:
        raise HTTPException(status_code=503, detail="Private screening-cache hashing is not configured.")
    screened_at = body.screened_at if body.screened_at.tzinfo else body.screened_at.replace(tzinfo=UTC)
    screened_at = screened_at.astimezone(UTC)
    if screened_at > datetime.now(UTC) + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Screening time cannot be in the future.")
    if body.status == "consent_override" and body.source != "specific_consent":
        raise HTTPException(status_code=422, detail="A consent override requires specific-consent evidence.")
    if body.status != "consent_override" and body.source == "specific_consent":
        raise HTTPException(status_code=422, detail="Specific consent is valid only for a consent override.")
    reference = body.source_reference.strip()
    evidence = {"source": body.source, "reference": reference}
    async with crm.tenant_connection(context) as conn:
        contact = await conn.fetchrow(
            """
            SELECT id, phone_e164, phone_screening_status, phone_screened_at FROM crm_contacts
            WHERE id = $1 AND organization_id = $2 FOR UPDATE
            """,
            contact_id, context.organization_id,
        )
        if not contact:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        if not contact["phone_e164"] or not contact["phone_e164"].startswith("+44"):
            raise HTTPException(status_code=422, detail="TPS/CTPS screening applies to a callable UK number.")
        if contact["phone_screened_at"] and screened_at < contact["phone_screened_at"]:
            raise HTTPException(status_code=409, detail="Newer phone-screening evidence already exists.")
        event_id = await conn.fetchval(
            """
            INSERT INTO crm_phone_screening_events (
              organization_id, contact_id, screened_by_user_id, phone_e164,
              status, source, source_reference, screened_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            context.organization_id, contact_id, context.user_id, contact["phone_e164"],
            body.status, body.source, reference, screened_at,
        )
        await conn.execute(
            """
            UPDATE crm_contacts SET phone_screening_status = $3,
              phone_screening_evidence = $4::jsonb, phone_screened_at = $5, updated_at = NOW()
            WHERE id = $1 AND organization_id = $2
            """,
            contact_id, context.organization_id, body.status, json.dumps(evidence), screened_at,
        )
        if body.status in {"tps", "ctps"}:
            await conn.execute(
                """
                INSERT INTO crm_suppressions (
                  organization_id, phone_e164, channel, reason, evidence, created_by_user_id
                ) VALUES ($1, $2, 'call', $3, $4::jsonb, $5)
                ON CONFLICT (organization_id, phone_e164, channel)
                  WHERE phone_e164 IS NOT NULL
                DO UPDATE SET reason = EXCLUDED.reason, evidence = EXCLUDED.evidence
                """,
                context.organization_id, contact["phone_e164"], body.status,
                json.dumps({**evidence, "screening_event_id": str(event_id)}), context.user_id,
            )
        else:
            await conn.execute(
                """
                DELETE FROM crm_suppressions
                WHERE organization_id = $1 AND phone_e164 = $2 AND channel = 'call'
                  AND reason IN ('tps', 'ctps')
                """,
                context.organization_id, contact["phone_e164"],
            )
        await conn.execute(
            """
            INSERT INTO crm_activities (
              organization_id, contact_id, actor_user_id, activity_type, metadata
            ) VALUES ($1, $2, $3, 'phone_screened',
              jsonb_build_object('status', $4::text, 'source', $5::text, 'screening_event_id', $6::uuid))
            """,
            context.organization_id, contact_id, context.user_id, body.status, body.source, event_id,
        )
        await crm._required_audit(
            conn, action="crm.contact.phone_screening", context=context,
            target_type="crm_contact", target_id=contact_id,
            metadata={"status": body.status, "source": body.source, "event_id": str(event_id)},
        )
    return {
        "id": contact_id,
        "phone_screening_status": body.status,
        "phone_screened_at": screened_at,
        "screening_event_id": event_id,
    }


@router.post("/phone-screenings/import", status_code=201)
async def import_phone_screenings(
    source: Literal["tps_ctps_licence", "approved_provider"] = Form(...),
    source_reference: str = Form(..., min_length=1, max_length=500),
    upload: UploadFile = File(...),
    _auth: dict = Depends(validate_session_identity),
) -> dict[str, Any]:
    """Ingest a bounded TPS/CTPS screening-result CSV without retaining the source file."""
    context = await crm._context(_auth)
    _require_manager(context)
    if len(settings.crm_screening_hash_key) < 32:
        raise HTTPException(status_code=503, detail="Private screening-cache hashing is not configured.")
    file_name = PurePath(upload.filename or "screening.csv").name[:255]
    raw = await upload.read(MAX_SCREENING_IMPORT_BYTES + 1)
    await upload.close()
    if not raw or len(raw) > MAX_SCREENING_IMPORT_BYTES:
        raise HTTPException(status_code=422, detail="Screening CSV must be between 1 byte and 5 MB.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Screening CSV must use UTF-8 encoding.") from exc
    reader = csv.DictReader(io.StringIO(text))
    required_columns = {"phone_e164", "status", "screened_at"}
    if not reader.fieldnames or not required_columns.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=422,
            detail="Screening CSV requires phone_e164,status,screened_at columns.",
        )
    records: dict[str, tuple[str, datetime, int]] = {}
    for row_number, row in enumerate(reader, start=2):
        if row_number > MAX_SCREENING_IMPORT_ROWS + 1:
            raise HTTPException(status_code=422, detail="Screening CSV exceeds 20,000 data rows.")
        phone = crm.normalize_e164(row.get("phone_e164"))
        if not phone or not phone.startswith("+44"):
            raise HTTPException(status_code=422, detail=f"Row {row_number} has no valid UK E.164 number.")
        status = (row.get("status") or "").strip().lower()
        if status not in {"clear", "tps", "ctps"}:
            raise HTTPException(status_code=422, detail=f"Row {row_number} has an invalid screening status.")
        try:
            screened_at = datetime.fromisoformat((row.get("screened_at") or "").strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Row {row_number} has an invalid screened_at value.") from exc
        if not screened_at.tzinfo:
            screened_at = screened_at.replace(tzinfo=UTC)
        screened_at = screened_at.astimezone(UTC)
        if screened_at > datetime.now(UTC) + timedelta(minutes=5):
            raise HTTPException(status_code=422, detail=f"Row {row_number} has a future screened_at value.")
        if phone in records:
            raise HTTPException(status_code=422, detail=f"Row {row_number} duplicates phone_e164 {phone}.")
        records[phone] = (status, screened_at, row_number)
    if not records:
        raise HTTPException(status_code=422, detail="Screening CSV has no data rows.")
    reference = source_reference.strip()
    file_hash = hashlib.sha256(raw).hexdigest()
    matched = clear_count = suppressed_count = 0
    async with crm.tenant_connection(context) as conn:
        contacts = await conn.fetch(
            """
            SELECT id, phone_e164, phone_screening_status, phone_screened_at FROM crm_contacts
            WHERE organization_id = $1 AND phone_e164 = ANY($2::text[])
            FOR UPDATE
            """,
            context.organization_id, list(records),
        )
        matched = len(contacts)
        import_id = await conn.fetchval(
            """
            INSERT INTO crm_phone_screening_imports (
              organization_id, imported_by_user_id, source, source_reference,
              file_name, file_sha256, row_count, matched_count, clear_count, suppressed_count
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 0, 0)
            RETURNING id
            """,
            context.organization_id, context.user_id, source, reference,
            file_name, file_hash, len(records), matched,
        )
        await conn.executemany(
            """
            INSERT INTO crm_phone_screening_cache (
              organization_id, import_id, phone_hmac, status,
              source, source_reference, screened_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (organization_id, phone_hmac) DO UPDATE SET
              import_id = EXCLUDED.import_id,
              status = EXCLUDED.status,
              source = EXCLUDED.source,
              source_reference = EXCLUDED.source_reference,
              screened_at = EXCLUDED.screened_at,
              updated_at = NOW()
            WHERE EXCLUDED.screened_at >= crm_phone_screening_cache.screened_at
            """,
            [
                (
                    context.organization_id,
                    import_id,
                    crm.hash_screening_number(phone, settings.crm_screening_hash_key),
                    status,
                    source,
                    reference,
                    screened_at,
                )
                for phone, (status, screened_at, _row_number) in records.items()
            ],
        )
        for contact in contacts:
            status, screened_at, row_number = records[contact["phone_e164"]]
            if contact["phone_screening_status"] == "consent_override":
                continue
            if contact["phone_screened_at"] and screened_at < contact["phone_screened_at"]:
                continue
            evidence = {
                "source": source,
                "reference": reference,
                "file_sha256": file_hash,
                "row": str(row_number),
            }
            event_id = await conn.fetchval(
                """
                INSERT INTO crm_phone_screening_events (
                  organization_id, contact_id, screened_by_user_id, import_id,
                  phone_e164, status, source, source_reference, screened_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                context.organization_id, contact["id"], context.user_id, import_id,
                contact["phone_e164"], status, source, reference, screened_at,
            )
            await conn.execute(
                """
                UPDATE crm_contacts SET phone_screening_status = $2,
                  phone_screening_evidence = $3::jsonb, phone_screened_at = $4, updated_at = NOW()
                WHERE id = $1
                """,
                contact["id"], status, json.dumps(evidence), screened_at,
            )
            if status in {"tps", "ctps"}:
                suppressed_count += 1
                await conn.execute(
                    """
                    INSERT INTO crm_suppressions (
                      organization_id, phone_e164, channel, reason, evidence, created_by_user_id
                    ) VALUES ($1, $2, 'call', $3, $4::jsonb, $5)
                    ON CONFLICT (organization_id, phone_e164, channel)
                      WHERE phone_e164 IS NOT NULL
                    DO UPDATE SET reason = EXCLUDED.reason, evidence = EXCLUDED.evidence
                    """,
                    context.organization_id, contact["phone_e164"], status,
                    json.dumps({**evidence, "screening_event_id": str(event_id)}), context.user_id,
                )
            else:
                clear_count += 1
                await conn.execute(
                    """
                    DELETE FROM crm_suppressions
                    WHERE organization_id = $1 AND phone_e164 = $2 AND channel = 'call'
                      AND reason IN ('tps', 'ctps')
                    """,
                    context.organization_id, contact["phone_e164"],
                )
        await conn.execute(
            """
            UPDATE crm_phone_screening_imports
            SET clear_count = $2, suppressed_count = $3 WHERE id = $1
            """,
            import_id, clear_count, suppressed_count,
        )
        await crm._required_audit(
            conn, action="crm.phone_screening.import", context=context,
            target_type="crm_screening_import", target_id=import_id,
            metadata={
                "source": source,
                "file_sha256": file_hash,
                "rows": len(records),
                "matched": matched,
                "suppressed": suppressed_count,
            },
        )
    return {
        "id": import_id,
        "file_sha256": file_hash,
        "rows": len(records),
        "matched": matched,
        "clear": clear_count,
        "suppressed": suppressed_count,
        "unmatched": len(records) - matched,
    }


@router.post("/contacts/{contact_id}/deals", status_code=201)
async def create_deal(
    contact_id: UUID, body: DealRequest, _auth: dict = Depends(validate_session_identity)
) -> dict[str, Any]:
    context = await crm._context(_auth)
    async with crm.tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO crm_deals (organization_id, contact_id, owner_user_id, title, stage, value_pence)
            SELECT $1, id, $3, $4, lifecycle_stage, $5
            FROM crm_contacts WHERE id = $2 AND organization_id = $1
            RETURNING id, contact_id, title, stage, value_pence, created_at
            """,
            context.organization_id, contact_id, context.user_id, body.title.strip(), body.value_pence,
        )
        if not row:
            raise HTTPException(status_code=404, detail="CRM contact not found.")
        await conn.execute(
            """
            INSERT INTO crm_activities (organization_id, contact_id, actor_user_id, activity_type, body, metadata)
            VALUES ($1, $2, $3, 'deal_created', $4, jsonb_build_object('deal_id', $5::uuid, 'value_pence', $6::bigint))
            """,
            context.organization_id, contact_id, context.user_id,
            body.title.strip(), row["id"], body.value_pence,
        )
    result = dict(row)
    evaluation = result.get("evaluation")
    if isinstance(evaluation, dict) and "overall_qa_score" in evaluation:
        # Backwards-compatible alias for older clients. New clients use the
        # authoritative overall_qa_score persisted in the evaluation object.
        result["evaluation"] = {
            **evaluation,
            "overall_score": evaluation["overall_qa_score"],
        }
    return result


@router.patch("/deals/{deal_id}/stage")
async def update_deal_stage(
    deal_id: UUID, body: DealStageRequest, _auth: dict = Depends(validate_session_identity)
) -> dict[str, Any]:
    context = await crm._context(_auth)
    if body.stage == "lost" and not (body.loss_reason or "").strip():
        raise HTTPException(status_code=422, detail="A loss reason is required when a deal is lost.")
    async with crm.tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            UPDATE crm_deals SET stage = $3,
              loss_reason = CASE WHEN $3 = 'lost' THEN $4 ELSE NULL END,
              closed_at = CASE WHEN $3 IN ('won', 'lost') THEN NOW() ELSE NULL END,
              updated_at = NOW()
            WHERE id = $1 AND organization_id = $2
            RETURNING id, contact_id, stage, value_pence, loss_reason, closed_at, updated_at
            """,
            deal_id, context.organization_id, body.stage,
            body.loss_reason.strip() if body.loss_reason else None,
        )
        if not row:
            raise HTTPException(status_code=404, detail="CRM deal not found.")
        await conn.execute(
            "UPDATE crm_contacts SET lifecycle_stage = $2, updated_at = NOW() WHERE id = $1",
            row["contact_id"], body.stage,
        )
        await conn.execute(
            """
            INSERT INTO crm_activities (
              organization_id, contact_id, actor_user_id, activity_type, metadata
            ) VALUES ($1, $2, $3, 'deal_stage_changed',
              jsonb_build_object('deal_id', $4::uuid, 'stage', $5::text))
            """,
            context.organization_id, row["contact_id"], context.user_id, deal_id, body.stage,
        )
        await crm._required_audit(
            conn, action="crm.deal.stage", context=context,
            target_type="crm_deal", target_id=deal_id,
            metadata={"stage": body.stage},
        )
    return dict(row)


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: UUID, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await crm._context(_auth)
    async with crm.tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            UPDATE crm_tasks SET status = 'completed', completed_at = NOW(), updated_at = NOW()
            WHERE id = $1 AND organization_id = $2 AND status = 'open'
              AND (assigned_user_id = $3 OR assigned_user_id IS NULL OR $4 IN ('owner', 'admin'))
            RETURNING id, contact_id, status, completed_at
            """,
            task_id, context.organization_id, context.user_id, context.role,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Open CRM task not found.")
        await conn.execute(
            """
            INSERT INTO crm_activities (organization_id, contact_id, actor_user_id, activity_type, metadata)
            VALUES ($1, $2, $3, 'task_completed', jsonb_build_object('task_id', $4::uuid))
            """,
            context.organization_id, row["contact_id"], context.user_id, task_id,
        )
    return dict(row)


@router.post("/campaigns", status_code=201)
async def create_campaign(body: CampaignRequest, _auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    _require_campaigns_enabled()
    context = await crm._context(_auth)
    _require_manager(context)
    async with crm.tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO crm_email_campaigns (
              organization_id, created_by_user_id, name, subject, html_body
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, subject, status, recipient_count, created_at
            """,
            context.organization_id, context.user_id, body.name.strip(),
            body.subject.strip(), body.body_text.strip(),
        )
        await crm._required_audit(
            conn, action="crm.campaign.create", context=context,
            target_type="crm_campaign", target_id=row["id"],
        )
    return dict(row)


@router.post("/campaigns/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: UUID,
    body: CampaignLaunchRequest,
    _auth: dict = Depends(validate_session_identity),
) -> dict[str, Any]:
    _require_campaigns_enabled()
    context = await crm._context(_auth)
    _require_manager(context)
    if not body.confirm_send:
        raise HTTPException(status_code=422, detail="Explicit campaign send confirmation is required.")
    contact_ids = list(dict.fromkeys(body.contact_ids))
    async with crm.tenant_connection(context) as conn:
        campaign = await conn.fetchrow(
            """
            SELECT id, subject, html_body, status
            FROM crm_email_campaigns
            WHERE id = $1 AND organization_id = $2
            FOR UPDATE
            """,
            campaign_id, context.organization_id,
        )
        if not campaign:
            raise HTTPException(status_code=404, detail="CRM campaign not found.")
        if campaign["status"] != "draft":
            raise HTTPException(status_code=409, detail="Only a draft campaign can be launched.")
        contacts = await conn.fetch(
            """
            SELECT c.id, c.email, c.market_code, c.subscriber_type, c.email_marketing_basis,
                   EXISTS (
                     SELECT 1 FROM crm_suppressions s
                     WHERE s.organization_id = c.organization_id
                       AND LOWER(s.email) = LOWER(c.email)
                       AND s.channel IN ('email', 'all')
                   ) AS suppressed
            FROM crm_contacts c
            WHERE c.organization_id = $1 AND c.id = ANY($2::uuid[])
            FOR UPDATE
            """,
            context.organization_id, contact_ids,
        )
        if len(contacts) != len(contact_ids):
            raise HTTPException(status_code=422, detail="One or more selected contacts do not exist.")
        ineligible = [
            row["id"] for row in contacts
            if row["suppressed"] or not is_email_marketing_eligible(
                market_code=row["market_code"], subscriber_type=row["subscriber_type"],
                marketing_basis=row["email_marketing_basis"], email=row["email"],
            )
        ]
        if ineligible:
            raise HTTPException(
                status_code=422,
                detail=f"{len(ineligible)} selected contact(s) lack an eligible UK email basis or are suppressed.",
            )
        scheduled_at = datetime.now(UTC)
        for contact in contacts:
            raw_token, token_hash = create_unsubscribe_token()
            html_body = render_campaign_html(campaign["html_body"], raw_token)
            queued = await conn.fetchrow(
                """
                INSERT INTO pending_emails (
                  to_email, subject, html_body, status, send_after, idempotency_key
                ) VALUES ($1, $2, $3, 'pending', $4, $5)
                RETURNING id
                """,
                contact["email"], campaign["subject"], html_body, scheduled_at,
                f"crm-campaign:{campaign_id}:{contact['id']}",
            )
            await conn.execute(
                """
                INSERT INTO crm_email_deliveries (
                  organization_id, campaign_id, contact_id, queued_email_id,
                  recipient_email, unsubscribe_token_hash
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                context.organization_id, campaign_id, contact["id"], queued["id"],
                contact["email"], token_hash,
            )
            await conn.execute(
                """
                INSERT INTO crm_activities (
                  organization_id, contact_id, actor_user_id, activity_type, metadata
                ) VALUES ($1, $2, $3, 'email_campaign_queued', jsonb_build_object('campaign_id', $4::uuid))
                """,
                context.organization_id, contact["id"], context.user_id, campaign_id,
            )
        await conn.execute(
            """
            UPDATE crm_email_campaigns SET
              status = 'queued', recipient_count = $2, approved_by_user_id = $3,
              scheduled_at = $4, launched_at = NOW(), updated_at = NOW()
            WHERE id = $1
            """,
            campaign_id, len(contacts), context.user_id, scheduled_at,
        )
        await crm._required_audit(
            conn, action="crm.campaign.launch", context=context,
            target_type="crm_campaign", target_id=campaign_id,
            metadata={"recipient_count": len(contacts), "channel": "email", "market": "GB"},
        )
    return {"id": campaign_id, "status": "queued", "recipient_count": len(contacts)}


@router.get("/campaigns")
async def list_campaigns(_auth: dict = Depends(validate_session_identity)) -> dict[str, Any]:
    context = await crm._context(_auth)
    async with crm.tenant_connection(context) as conn:
        rows = await conn.fetch(
            """
            SELECT campaign.id, campaign.name, campaign.subject, campaign.status,
                   campaign.recipient_count, campaign.created_at, campaign.launched_at,
                   COUNT(*) FILTER (WHERE email.status = 'sent')::int AS sent_count,
                   COUNT(*) FILTER (WHERE email.status = 'failed')::int AS failed_count,
                   COUNT(*) FILTER (WHERE delivery.delivered_at IS NOT NULL)::int AS delivered_count,
                   COUNT(*) FILTER (WHERE delivery.bounced_at IS NOT NULL)::int AS bounced_count,
                   COUNT(*) FILTER (WHERE delivery.complained_at IS NOT NULL)::int AS complained_count,
                   COUNT(*) FILTER (WHERE delivery.unsubscribed_at IS NOT NULL)::int AS unsubscribed_count
            FROM crm_email_campaigns campaign
            LEFT JOIN crm_email_deliveries delivery ON delivery.campaign_id = campaign.id
            LEFT JOIN pending_emails email ON email.id = delivery.queued_email_id
            WHERE campaign.organization_id = $1
            GROUP BY campaign.id
            ORDER BY campaign.created_at DESC
            LIMIT 100
            """,
            context.organization_id,
        )
    return {"data": [dict(row) for row in rows]}


@router.get("/email/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_email(token: str) -> HTMLResponse:
    if len(token) < 32 or len(token) > 200:
        raise HTTPException(status_code=404, detail="Unsubscribe link is invalid.")
    token_hash = hash_unsubscribe_token(token)
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_unsubscribe', true)")
            delivery = await conn.fetchrow(
                """
                SELECT id, organization_id, contact_id, recipient_email, unsubscribed_at
                FROM crm_email_deliveries
                WHERE unsubscribe_token_hash = $1
                FOR UPDATE
                """,
                token_hash,
            )
            if not delivery:
                raise HTTPException(status_code=404, detail="Unsubscribe link is invalid.")
            if not delivery["unsubscribed_at"]:
                await conn.execute(
                    "UPDATE crm_email_deliveries SET unsubscribed_at = NOW() WHERE id = $1",
                    delivery["id"],
                )
                await conn.execute(
                    """
                    INSERT INTO crm_suppressions (
                      organization_id, email, channel, reason, evidence, created_by_user_id
                    )
                    SELECT $1, $2, 'email', 'unsubscribe',
                           jsonb_build_object('delivery_id', $3::uuid), created_by_user_id
                    FROM crm_contacts WHERE id = $4
                    ON CONFLICT DO NOTHING
                    """,
                    delivery["organization_id"], delivery["recipient_email"],
                    delivery["id"], delivery["contact_id"],
                )
                await conn.execute(
                    """
                    INSERT INTO crm_activities (organization_id, contact_id, activity_type, metadata)
                    VALUES ($1, $2, 'email_unsubscribed', jsonb_build_object('delivery_id', $3::uuid))
                    """,
                    delivery["organization_id"], delivery["contact_id"], delivery["id"],
                )
    return HTMLResponse(
        "<!doctype html><html><body style='font-family:Arial;padding:40px'>"
        "<h1>You are unsubscribed</h1><p>CareGist will not send further marketing emails to this address.</p>"
        "</body></html>",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/webhooks/resend")
async def resend_webhook(request: Request) -> dict[str, Any]:
    try:
        event_id, event = verify_resend_webhook(await request.body(), request.headers)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Email webhook verification is unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid email webhook.") from exc
    event_type = str(event.get("type") or "")
    if event_type not in HANDLED_EMAIL_EVENTS:
        return {"accepted": True, "ignored": True}
    try:
        occurred_at = resend_event_occurred_at(event)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Email webhook event time is invalid.") from exc
    provider_message_id = str(event["data"].get("email_id") or "").strip()
    if not provider_message_id or len(provider_message_id) > 255:
        raise HTTPException(status_code=422, detail="Email webhook has no valid message identifier.")
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_email_webhook', true)")
            delivery = await conn.fetchrow(
                """
                SELECT delivery.id, delivery.organization_id, delivery.contact_id,
                       delivery.recipient_email, contact.created_by_user_id
                FROM crm_email_deliveries delivery
                JOIN pending_emails email ON email.id = delivery.queued_email_id
                JOIN crm_contacts contact ON contact.id = delivery.contact_id
                WHERE email.provider_message_id = $1
                FOR UPDATE OF delivery
                """,
                provider_message_id,
            )
            if not delivery:
                return {"accepted": True, "unmatched": True}
            inserted = await conn.fetchval(
                """
                INSERT INTO crm_email_events (
                  organization_id, delivery_id, provider_event_id, event_type, occurred_at
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (provider_event_id) DO NOTHING
                RETURNING id
                """,
                delivery["organization_id"], delivery["id"], event_id, event_type, occurred_at,
            )
            if not inserted:
                return {"accepted": True, "duplicate": True}
            await conn.execute(
                """
                UPDATE crm_email_deliveries SET
                  delivered_at = CASE WHEN $2 = 'email.delivered' THEN NOW() ELSE delivered_at END,
                  failed_at = CASE WHEN $2 IN ('email.failed', 'email.suppressed') THEN NOW() ELSE failed_at END,
                  bounced_at = CASE WHEN $2 = 'email.bounced' THEN NOW() ELSE bounced_at END,
                  complained_at = CASE WHEN $2 = 'email.complained' THEN NOW() ELSE complained_at END,
                  last_event_type = $2, last_event_at = NOW()
                WHERE id = $1
                """,
                delivery["id"], event_type,
            )
            suppression_reason = {
                "email.bounced": "bounce",
                "email.complained": "complaint",
                "email.suppressed": "provider_suppressed",
            }.get(event_type)
            if suppression_reason:
                await conn.execute(
                    """
                    INSERT INTO crm_suppressions (
                      organization_id, email, channel, reason, evidence, created_by_user_id
                    ) VALUES ($1, $2, 'email', $3,
                      jsonb_build_object('provider_event_id', $4::text), $5)
                    ON CONFLICT DO NOTHING
                    """,
                    delivery["organization_id"], delivery["recipient_email"], suppression_reason,
                    event_id, delivery["created_by_user_id"],
                )
            activity_type = {
                "email.bounced": "email_bounced",
                "email.complained": "email_complained",
            }.get(event_type)
            if activity_type:
                await conn.execute(
                    """
                    INSERT INTO crm_activities (
                      organization_id, contact_id, activity_type, metadata
                    ) VALUES ($1, $2, $3, jsonb_build_object('delivery_id', $4::uuid))
                    """,
                    delivery["organization_id"], delivery["contact_id"], activity_type, delivery["id"],
                )
    return {"accepted": True, "event": event_type}


@router.post("/twilio/recording-notice")
async def recording_notice(request: Request) -> Response:
    crm._require_calling_enabled()
    if not settings.crm_recording_enabled:
        raise HTTPException(status_code=404, detail="Recording is not enabled.")
    form = await crm._twilio_form(request)
    crm._validate_twilio(request, form)
    message = "This call is being recorded for training and quality purposes."
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{message}</Say></Response>',
        media_type="application/xml",
    )


@router.post("/twilio/calls/{call_session_id}/recording")
async def recording_complete(call_session_id: UUID, request: Request) -> dict[str, Any]:
    crm._require_calling_enabled()
    if not settings.crm_recording_enabled:
        raise HTTPException(status_code=404, detail="Recording is not enabled.")
    form = await crm._twilio_form(request)
    crm._validate_twilio(request, form)
    if form.get("RecordingStatus") != "completed":
        return {"accepted": True, "ready": False}
    recording_sid = form.get("RecordingSid", "")
    try:
        validate_twilio_recording_sid(recording_sid)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Twilio RecordingSid is invalid.") from exc
    callback_call_sid = crm.validate_twilio_call_sid(form.get("CallSid", ""))
    try:
        duration = int(form.get("RecordingDuration", "0"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Recording duration is invalid.") from exc
    if duration < 0:
        raise HTTPException(status_code=422, detail="Recording duration is invalid.")
    now = datetime.now(UTC)
    async with crm._twilio_connection() as conn:
        call = await conn.fetchrow(
            """
            SELECT id, organization_id, contact_id, twilio_parent_call_sid
            FROM crm_call_sessions WHERE id = $1 FOR UPDATE
            """,
            call_session_id,
        )
        if not call:
            raise HTTPException(status_code=404, detail="CRM call session not found.")
        if call["twilio_parent_call_sid"] != callback_call_sid:
            raise HTTPException(status_code=409, detail="Recording callback does not match this call session.")
        existing = await conn.fetchrow(
            """
            SELECT id, call_session_id, status
            FROM crm_recordings WHERE twilio_recording_sid = $1
            """,
            recording_sid,
        )
        if existing and existing["call_session_id"] != call_session_id:
            raise HTTPException(status_code=409, detail="Recording SID belongs to a different call session.")
        if existing and existing["status"] in {"queued", "uploading", "ready", "deleted"}:
            return {
                "accepted": True,
                "queued": existing["status"] in {"queued", "uploading"},
                "ready": existing["status"] == "ready",
                "duplicate": True,
            }
        object_key = recording_object_key(call["organization_id"], call_session_id, now)
        if existing:
            recording_id = existing["id"]
            await conn.execute(
                """
                UPDATE crm_recordings
                SET status = 'queued', error_code = NULL,
                    processing_started_at = NULL, updated_at = NOW()
                WHERE id = $1 AND attempts < 5 AND expires_at > NOW()
                """,
                recording_id,
            )
        else:
            recording_id = await conn.fetchval(
                """
                INSERT INTO crm_recordings (
                  organization_id, call_session_id, twilio_recording_sid,
                  object_key, duration_seconds, expires_at
                ) VALUES ($1, $2, $3, $4, $5, NOW() + INTERVAL '30 days')
                RETURNING id
                """,
                call["organization_id"], call_session_id, recording_sid, object_key, duration,
            )
    return {"accepted": True, "queued": True, "ready": False}


@router.get("/recordings/{recording_id}/playback")
async def recording_playback(
    recording_id: UUID, _auth: dict = Depends(validate_session_identity)
) -> RedirectResponse:
    context = await crm._context(_auth)
    async with crm.tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            SELECT recording.object_key, recording.status, recording.expires_at,
                   call.agent_user_id
            FROM crm_recordings recording
            JOIN crm_call_sessions call ON call.id = recording.call_session_id
            WHERE recording.id = $1 AND recording.organization_id = $2
            """,
            recording_id, context.organization_id,
        )
        if not row or row["status"] != "ready" or row["expires_at"] <= datetime.now(UTC):
            raise HTTPException(status_code=404, detail="Recording is unavailable.")
        if row["agent_user_id"] != context.user_id and context.role not in {"owner", "admin"}:
            raise HTTPException(status_code=403, detail="You cannot access this recording.")
        await crm._required_audit(
            conn, action="crm.recording.playback", context=context,
            target_type="crm_recording", target_id=recording_id,
        )
    url = await presign_recording(row["object_key"], expires_seconds=60)
    return RedirectResponse(url, status_code=307, headers={"Cache-Control": "no-store"})


@router.get("/calls/{call_session_id}")
async def call_detail(
    call_session_id: UUID, _auth: dict = Depends(validate_session_identity)
) -> dict[str, Any]:
    context = await crm._context(_auth)
    async with crm.tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            SELECT call.id, call.contact_id, call.agent_user_id, call.status,
                   call.duration_seconds, call.disposition, call.started_at, call.ended_at,
                   recording.id AS recording_id, recording.status AS recording_status,
                   recording.expires_at AS recording_expires_at,
                   intelligence.status AS intelligence_status,
                   intelligence.transcript, intelligence.summary, intelligence.evaluation
            FROM crm_call_sessions call
            LEFT JOIN crm_recordings recording ON recording.call_session_id = call.id
            LEFT JOIN crm_call_intelligence intelligence ON intelligence.call_session_id = call.id
            WHERE call.id = $1 AND call.organization_id = $2
            """,
            call_session_id, context.organization_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="CRM call session not found.")
        if row["agent_user_id"] != context.user_id and context.role not in {"owner", "admin"}:
            raise HTTPException(status_code=403, detail="You cannot access this call evaluation.")
    result = dict(row)
    evaluation = result.get("evaluation")
    if isinstance(evaluation, dict) and "overall_qa_score" in evaluation:
        # Backwards-compatible alias for older clients. New clients use the
        # authoritative overall_qa_score persisted in the evaluation object.
        result["evaluation"] = {
            **evaluation,
            "overall_score": evaluation["overall_qa_score"],
        }
    return result


@router.get("/reports/performance")
async def performance_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    _auth: dict = Depends(validate_session_identity),
) -> dict[str, Any]:
    context = await crm._context(_auth)
    _require_manager(context)
    end_date = end or datetime.now(UTC).date()
    start_date = start or (end_date - timedelta(days=29))
    if end_date < start_date or (end_date - start_date).days > 366:
        raise HTTPException(status_code=422, detail="Report range must be between 1 and 367 days.")
    start_at = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    end_at = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    async with crm.tenant_connection(context) as conn:
        agents = await conn.fetch(
            """
            SELECT call.agent_user_id, COALESCE(NULLIF(users.name, ''), users.email) AS agent,
                   COUNT(*)::int AS calls,
                   COUNT(*) FILTER (WHERE call.answered_at IS NOT NULL)::int AS connected_calls,
                   COALESCE(SUM(call.duration_seconds), 0)::bigint AS talk_seconds,
                   COUNT(*) FILTER (WHERE call.disposition IS NOT NULL)::int AS dispositioned_calls,
                   COUNT(*) FILTER (WHERE call.disposition IN ('qualified','meeting_booked','sale_completed'))::int AS positive_outcomes,
                   ROUND(AVG((intelligence.evaluation->>'overall_qa_score')::numeric), 1) AS average_qa_score
            FROM crm_call_sessions call
            JOIN users ON users.id = call.agent_user_id
            LEFT JOIN crm_call_intelligence intelligence
              ON intelligence.call_session_id = call.id AND intelligence.status = 'completed'
            WHERE call.organization_id = $1 AND call.created_at >= $2 AND call.created_at < $3
            GROUP BY call.agent_user_id, users.name, users.email
            ORDER BY calls DESC, agent
            """,
            context.organization_id, start_at, end_at,
        )
        dispositions = await conn.fetch(
            """
            SELECT COALESCE(disposition, status) AS outcome, COUNT(*)::int AS count
            FROM crm_call_sessions
            WHERE organization_id = $1 AND created_at >= $2 AND created_at < $3
            GROUP BY COALESCE(disposition, status)
            ORDER BY count DESC, outcome
            """,
            context.organization_id, start_at, end_at,
        )
        campaigns = await conn.fetchrow(
            """
            SELECT COUNT(DISTINCT campaign.id)::int AS campaigns,
                   COUNT(delivery.id)::int AS recipients,
                   COUNT(*) FILTER (WHERE email.status = 'sent')::int AS sent,
                   COUNT(*) FILTER (WHERE email.status = 'failed')::int AS failed,
                   COUNT(*) FILTER (WHERE delivery.delivered_at IS NOT NULL)::int AS delivered,
                   COUNT(*) FILTER (WHERE delivery.bounced_at IS NOT NULL)::int AS bounced,
                   COUNT(*) FILTER (WHERE delivery.complained_at IS NOT NULL)::int AS complained,
                   COUNT(*) FILTER (WHERE delivery.unsubscribed_at IS NOT NULL)::int AS unsubscribed
            FROM crm_email_campaigns campaign
            LEFT JOIN crm_email_deliveries delivery ON delivery.campaign_id = campaign.id
            LEFT JOIN pending_emails email ON email.id = delivery.queued_email_id
            WHERE campaign.organization_id = $1
              AND campaign.created_at >= $2 AND campaign.created_at < $3
            """,
            context.organization_id, start_at, end_at,
        )
    return {
        "start": start_date.isoformat(), "end": end_date.isoformat(),
        "agents": [dict(row) for row in agents],
        "dispositions": [dict(row) for row in dispositions],
        "campaigns": dict(campaigns or {}),
        "ai_advisory_only": True,
    }
