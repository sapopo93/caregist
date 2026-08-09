"""Radar and Intelligence Feed APIs backed by the trusted event ledger."""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.services.radar import (
    OGL_ATTRIBUTION,
    RadarFilters,
    enforce_plan_scope,
    get_radar_event,
    list_radar_events,
    parse_event_types,
    require_radar_access,
)
from api.services.tenant_context import OrganizationContext, resolve_organization_context, tenant_connection


router = APIRouter(prefix="/api/v1/radar", tags=["radar"])


class SavedViewRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    filters: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class ActionRequest(BaseModel):
    action_type: Literal["opened", "saved", "exported", "dismissed", "requested_detail"]
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class OutcomeRequest(BaseModel):
    event_id: UUID
    outcome_type: Literal["contacted", "meeting_booked", "engagement_won", "not_relevant"]
    notes: str | None = Field(None, max_length=1000)

    model_config = {"extra": "forbid"}


class ScopeRequest(BaseModel):
    region: str = Field(min_length=2, max_length=100)

    model_config = {"extra": "forbid"}


def _parse_date(value: str | None, name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{name} must use YYYY-MM-DD.") from exc


def _filters(
    event_type: list[str] | None,
    q: str | None,
    region: str | None,
    local_authority: str | None,
    service_type: str | None,
    from_date: str | None,
    to_date: str | None,
) -> RadarFilters:
    return RadarFilters(
        event_types=parse_event_types(event_type),
        q=q.strip() if q else None,
        region=region.strip() if region else None,
        local_authority=local_authority.strip() if local_authority else None,
        service_type=service_type.strip() if service_type else None,
        from_date=_parse_date(from_date, "from_date"),
        to_date=_parse_date(to_date, "to_date"),
    )


def _saved_view_filters(filters: dict[str, Any]) -> RadarFilters:
    """Validate an untyped saved-view document through the public filter contract."""
    event_types = filters.get("event_types")
    if event_types is not None and (
        not isinstance(event_types, list)
        or any(not isinstance(value, str) for value in event_types)
    ):
        raise HTTPException(status_code=422, detail="event_types must be a list of signal names.")

    strings: dict[str, str | None] = {}
    for name, max_length in {
        "q": 120,
        "region": 100,
        "local_authority": 120,
        "service_type": 120,
        "from_date": 10,
        "to_date": 10,
    }.items():
        value = filters.get(name)
        if value is not None and not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"{name} must be a string.")
        if value is not None and len(value) > max_length:
            raise HTTPException(status_code=422, detail=f"{name} is too long.")
        strings[name] = value

    return _filters(
        event_types,
        strings["q"],
        strings["region"],
        strings["local_authority"],
        strings["service_type"],
        strings["from_date"],
        strings["to_date"],
    )


async def _context(auth: dict) -> tuple[OrganizationContext, dict[str, Any]]:
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="An organization user account is required.")
    context = await resolve_organization_context(int(user_id), auth.get("tier", "free"))
    config = require_radar_access(context.plan_tier, auth.get("auth_method"))
    return context, config


@router.get("/events")
async def get_events(
    event_type: list[str] | None = Query(None),
    q: str | None = Query(None, max_length=120),
    region: str | None = Query(None, max_length=100),
    local_authority: str | None = Query(None, max_length=120),
    service_type: str | None = Query(None, max_length=120),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    cursor: str | None = Query(None, max_length=500),
    limit: int = Query(50, ge=1, le=500),
    _auth: dict = Depends(validate_api_key),
) -> dict[str, Any]:
    context, config = await _context(_auth)
    scoped = enforce_plan_scope(
        context.plan_tier,
        _filters(event_type, q, region, local_authority, service_type, from_date, to_date),
        context.scope_config,
    )
    page_limit = min(limit, int(config.get("feed_rows") or config.get("page_size") or 50))
    async with get_connection() as conn:
        return await list_radar_events(conn, scoped, cursor=cursor, limit=page_limit)


@router.get("/events/export.csv")
async def export_events(
    event_type: list[str] | None = Query(None),
    q: str | None = Query(None, max_length=120),
    region: str | None = Query(None, max_length=100),
    local_authority: str | None = Query(None, max_length=120),
    service_type: str | None = Query(None, max_length=120),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    _auth: dict = Depends(validate_api_key),
) -> StreamingResponse:
    if not settings.radar_delivery_enabled:
        raise HTTPException(status_code=503, detail="Radar export is awaiting its delivery-readiness gate.")
    context, config = await _context(_auth)
    scoped = enforce_plan_scope(
        context.plan_tier,
        _filters(event_type, q, region, local_authority, service_type, from_date, to_date),
        context.scope_config,
    )
    limit = min(int(config.get("export") or 0), 50000)
    if limit <= 0:
        raise HTTPException(status_code=403, detail="Event export is not included in this plan.")
    async with get_connection() as conn:
        result = await list_radar_events(conn, scoped, cursor=None, limit=limit)
    if not result["data"]:
        raise HTTPException(status_code=404, detail="No Radar events matched this view.")

    output = io.StringIO()
    fields = [
        "event_id", "event_type", "effective_at", "observed_at", "source_published_at",
        "cqc_location_id", "cqc_provider_id", "provider_name", "region",
        "local_authority", "old_value", "new_value", "source_url", "data_attribution",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for event in result["data"]:
        writer.writerow(
            {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "effective_at": event["effective_at"],
                "observed_at": event["observed_at"],
                "source_published_at": event["source_published_at"],
                "cqc_location_id": event["entity"]["cqc_location_id"],
                "cqc_provider_id": event["entity"]["cqc_provider_id"],
                "provider_name": event["entity"]["name"],
                "region": event["provider"]["region"],
                "local_authority": event["provider"]["local_authority"],
                "old_value": json.dumps(event["change"]["old"], sort_keys=True, default=str),
                "new_value": json.dumps(event["change"]["new"], sort_keys=True, default=str),
                "source_url": event["source"]["url"],
                "data_attribution": OGL_ATTRIBUTION,
            }
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=caregist-radar-events.csv"},
    )


@router.get("/events/{event_id}")
async def get_event(event_id: UUID, _auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    context, _ = await _context(_auth)
    scoped = enforce_plan_scope(context.plan_tier, RadarFilters(), context.scope_config)
    async with get_connection() as conn:
        event = await get_radar_event(conn, scoped, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Radar event not found or outside this subscription scope.")
    return event


@router.get("/views")
async def list_views(_auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    context, _ = await _context(_auth)
    async with tenant_connection(context) as conn:
        rows = await conn.fetch(
            "SELECT id, name, filters, created_at, updated_at FROM saved_signal_views "
            "WHERE organization_id = $1 ORDER BY updated_at DESC",
            context.organization_id,
        )
    return {"data": [dict(row) for row in rows]}


@router.post("/views", status_code=201)
async def create_view(body: SavedViewRequest, _auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    context, config = await _context(_auth)
    allowed_keys = {"event_types", "q", "region", "local_authority", "service_type", "from_date", "to_date"}
    unknown = sorted(set(body.filters) - allowed_keys)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unsupported view filters: {', '.join(unknown)}")
    requested_filters = _saved_view_filters(body.filters)
    # Validate the stored filter against the current entitlement. The enforced
    # rolling history boundary is reapplied when the view is used, so it is not
    # frozen into the saved document here.
    enforce_plan_scope(context.plan_tier, requested_filters, context.scope_config)
    stored_filters = requested_filters.to_json()
    limit = int(config.get("saved_filters") or 0)
    async with tenant_connection(context) as conn:
        count = int(
            await conn.fetchval(
                "SELECT COUNT(*) FROM saved_signal_views WHERE organization_id = $1",
                context.organization_id,
            )
            or 0
        )
        if count >= limit:
            raise HTTPException(status_code=403, detail="This organization has reached its saved-view limit.")
        row = await conn.fetchrow(
            """
            INSERT INTO saved_signal_views (organization_id, created_by_user_id, name, filters)
            VALUES ($1, $2, $3, $4::jsonb)
            ON CONFLICT (organization_id, name)
            DO UPDATE SET filters = EXCLUDED.filters, updated_at = NOW()
            RETURNING id, name, filters, created_at, updated_at
            """,
            context.organization_id,
            context.user_id,
            body.name,
            json.dumps(stored_filters),
        )
    return dict(row)


@router.delete("/views/{view_id}")
async def delete_view(view_id: UUID, _auth: dict = Depends(validate_api_key)) -> dict[str, bool]:
    context, _ = await _context(_auth)
    async with tenant_connection(context) as conn:
        result = await conn.execute(
            "DELETE FROM saved_signal_views WHERE id = $1 AND organization_id = $2",
            view_id,
            context.organization_id,
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Saved view not found.")
    return {"deleted": True}


@router.post("/events/{event_id}/actions", status_code=201)
async def record_action(
    event_id: UUID,
    body: ActionRequest,
    _auth: dict = Depends(validate_api_key),
) -> dict[str, Any]:
    context, _ = await _context(_auth)
    scoped = enforce_plan_scope(context.plan_tier, RadarFilters(), context.scope_config)
    async with tenant_connection(context) as conn:
        visible_event = await get_radar_event(conn, scoped, event_id)
        if not visible_event:
            raise HTTPException(status_code=404, detail="Radar event not found or outside this subscription scope.")
        ledger_id = await conn.fetchval("SELECT id FROM trusted_event_ledger WHERE public_event_id = $1", event_id)
        if not ledger_id:
            raise HTTPException(status_code=404, detail="Radar event not found.")
        row = await conn.fetchrow(
            """
            INSERT INTO event_actions (organization_id, user_id, event_id, action_type, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (organization_id, user_id, event_id, action_type)
            DO UPDATE SET metadata = EXCLUDED.metadata
            RETURNING id, action_type, created_at
            """,
            context.organization_id,
            context.user_id,
            ledger_id,
            body.action_type,
            json.dumps(body.metadata),
        )
    return dict(row)


@router.post("/outcomes", status_code=201)
async def record_outcome(body: OutcomeRequest, _auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    context, _ = await _context(_auth)
    scoped = enforce_plan_scope(context.plan_tier, RadarFilters(), context.scope_config)
    async with tenant_connection(context) as conn:
        visible_event = await get_radar_event(conn, scoped, body.event_id)
        if not visible_event:
            raise HTTPException(status_code=404, detail="Radar event not found or outside this subscription scope.")
        ledger_id = await conn.fetchval("SELECT id FROM trusted_event_ledger WHERE public_event_id = $1", body.event_id)
        if not ledger_id:
            raise HTTPException(status_code=404, detail="Radar event not found.")
        row = await conn.fetchrow(
            """
            INSERT INTO event_outcomes (organization_id, user_id, event_id, outcome_type, notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, outcome_type, created_at
            """,
            context.organization_id,
            context.user_id,
            ledger_id,
            body.outcome_type,
            body.notes,
        )
    return dict(row)


@router.get("/scope")
async def get_scope(_auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    context, _ = await _context(_auth)
    return {"plan_tier": context.plan_tier, "scope": context.scope_config}


@router.put("/scope")
async def set_scope(body: ScopeRequest, _auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    context, _ = await _context(_auth)
    if context.plan_tier != "radar-regional":
        raise HTTPException(status_code=422, detail="Territory selection applies only to Radar Regional.")
    if context.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Only an organization owner or admin can change territory.")
    async with tenant_connection(context) as conn:
        row = await conn.fetchrow(
            """
            UPDATE organization_subscriptions
            SET scope_config = jsonb_build_object('region', $2::text), updated_at = NOW()
            WHERE organization_id = $1
            RETURNING plan_tier, scope_config
            """,
            context.organization_id,
            body.region.strip(),
        )
    if not row:
        raise HTTPException(status_code=409, detail="The organization subscription is not provisioned.")
    return {"plan_tier": row["plan_tier"], "scope": dict(row["scope_config"] or {})}
