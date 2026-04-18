"""New registration feed endpoints built on the trusted event ledger."""

from __future__ import annotations

import csv
import io
import json
import logging
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from api.config import get_next_tier
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.middleware.rate_limit import add_rate_limit_headers, check_export_limit
from api.services.new_registration_feed import (
    FeedFilters,
    coerce_json_object,
    deliver_new_registration_event,
    list_new_registration_events,
    queue_weekly_new_registration_digests,
    require_digest_access,
    require_feed_access,
    require_saved_filter_access,
    sync_new_registration_event_payloads,
)
from api.utils.analytics import log_event

router = APIRouter(prefix="/api/v1/feed", tags=["feed"])
logger = logging.getLogger("caregist.feed")


class SavedFilterCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    filters: dict[str, str] = Field(default_factory=dict)


class DigestSubscriptionRequest(BaseModel):
    active: bool = True
    filters: dict[str, str] = Field(default_factory=dict)


def _filters_from_query(
    q: str | None = None,
    region: str | None = None,
    local_authority: str | None = None,
    service_type: str | None = None,
    provider_type: str | None = None,
    postcode_prefix: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> FeedFilters:
    return FeedFilters(
        q=q.strip() if q else None,
        region=region,
        local_authority=local_authority,
        service_type=service_type,
        provider_type=provider_type,
        postcode_prefix=postcode_prefix,
        from_date=from_date,
        to_date=to_date,
    )


def _feed_response(data: list[dict[str, Any]], total: int, page: int, per_page: int, tier: str) -> dict[str, Any]:
    pages = max(1, (total + per_page - 1) // per_page) if per_page else 1
    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "tier": tier,
        },
    }


def _export_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "registered_on": str(row["effective_date"]),
            "provider_name": row["name"],
            "service_types": row["service_types"],
            "type": row["type"],
            "region": row["region"],
            "local_authority": row["local_authority"],
            "town": row["town"],
            "postcode": row["postcode"],
            "rating": row["overall_rating"],
            "website": row["website"],
            "phone": row["phone"],
            "provider_slug": row["slug"],
            "confidence_score": float(row["confidence_score"] or 0),
        }
        for row in rows
    ]


@router.get("/new-registrations")
async def get_new_registration_feed(
    response: Response,
    q: str | None = Query(None),
    region: str | None = Query(None),
    local_authority: str | None = Query(None),
    service_type: str | None = Query(None),
    provider_type: str | None = Query(None, alias="type"),
    postcode_prefix: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int | None = Query(None, ge=1, le=250),
    _auth: dict = Depends(validate_api_key),
) -> dict[str, Any]:
    tier = _auth["tier"]
    config = require_feed_access(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    page_size = min(per_page or config["page_size"], config["page_size"], config["feed_rows"])
    offset = (page - 1) * page_size
    filters = _filters_from_query(q, region, local_authority, service_type, provider_type, postcode_prefix, from_date, to_date)

    # Feed sync is NOT triggered here. It runs exclusively via the hourly cron
    # (tools/run_new_registration_feed_cycle.py) or the internal admin endpoint
    # below. GET requests are read-only and never write to the ledger.
    async with get_connection() as conn:
        rows, total = await list_new_registration_events(
            conn, filters, limit=page_size, offset=offset,
            sort_by=sort_by, sort_order=sort_order,
        )

    if tier == "free":
        total = min(total, page_size)

    return _feed_response(rows, total, page, page_size, tier)


@router.get("/new-registrations/export.csv")
async def export_new_registration_csv(
    response: Response,
    q: str | None = Query(None),
    region: str | None = Query(None),
    local_authority: str | None = Query(None),
    service_type: str | None = Query(None),
    provider_type: str | None = Query(None, alias="type"),
    postcode_prefix: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    _auth: dict = Depends(validate_api_key),
) -> StreamingResponse:
    tier = _auth["tier"]
    config = require_feed_access(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    if tier == "free":
        raise HTTPException(status_code=403, detail="Exporting the new registration feed starts on the Starter plan.")

    check_export_limit(_auth.get("key_id") or _auth.get("name", "guest"), tier)
    limit = int(config["export"])
    filters = _filters_from_query(q, region, local_authority, service_type, provider_type, postcode_prefix, from_date, to_date)
    async with get_connection() as conn:
        rows, total = await list_new_registration_events(conn, filters, limit=limit, offset=0)

    export_rows = _export_rows(rows)
    if not export_rows:
        raise HTTPException(status_code=404, detail="No feed events matched this filter.")

    await log_event("new_registration_feed_export_csv", "new_registration_feed", user_id=_auth.get("user_id"), meta={"tier": tier, "rows": len(export_rows)})

    fieldnames = list(export_rows[0].keys())
    headers = dict(response.headers)
    headers["Content-Disposition"] = "attachment; filename=new-registrations.csv"
    headers["X-Total-Count"] = str(total)

    def _csv_stream():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        yield buf.getvalue()
        for row in export_rows:
            buf.seek(0)
            buf.truncate()
            writer.writerow(row)
            yield buf.getvalue()

    return StreamingResponse(_csv_stream(), media_type="text/csv", headers=headers)


@router.get("/new-registrations/export.xlsx")
async def export_new_registration_xlsx(
    response: Response,
    q: str | None = Query(None),
    region: str | None = Query(None),
    local_authority: str | None = Query(None),
    service_type: str | None = Query(None),
    provider_type: str | None = Query(None, alias="type"),
    postcode_prefix: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    _auth: dict = Depends(validate_api_key),
) -> StreamingResponse:
    import openpyxl
    from openpyxl.styles import Font

    tier = _auth["tier"]
    config = require_feed_access(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    if tier == "free":
        raise HTTPException(status_code=403, detail="Exporting the new registration feed starts on the Starter plan.")

    check_export_limit(_auth.get("key_id") or _auth.get("name", "guest"), tier)
    limit = int(config["export"])
    filters = _filters_from_query(q, region, local_authority, service_type, provider_type, postcode_prefix, from_date, to_date)
    async with get_connection() as conn:
        rows, total = await list_new_registration_events(conn, filters, limit=limit, offset=0)

    export_rows = _export_rows(rows)
    if not export_rows:
        raise HTTPException(status_code=404, detail="No feed events matched this filter.")

    await log_event("new_registration_feed_export_xlsx", "new_registration_feed", user_id=_auth.get("user_id"), meta={"tier": tier, "rows": len(export_rows)})

    import tempfile

    from openpyxl.cell import WriteOnlyCell

    headers_list = list(export_rows[0].keys())
    workbook = openpyxl.Workbook(write_only=True)
    sheet = workbook.create_sheet("New Registrations")
    header_cells = []
    for h in headers_list:
        cell = WriteOnlyCell(sheet, value=h)
        cell.font = Font(bold=True)
        header_cells.append(cell)
    sheet.append(header_cells)
    for row in export_rows:
        sheet.append([row.get(column) for column in headers_list])

    # SpooledTemporaryFile keeps the first 10 MB in RAM; larger files spill to
    # disk automatically. This prevents a single large export from pinning the
    # process heap when multiple exports run concurrently.
    tmp = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
    workbook.save(tmp)
    tmp.seek(0)

    def _xlsx_stream(f):
        try:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            f.close()

    resp_headers = dict(response.headers)
    resp_headers["Content-Disposition"] = "attachment; filename=new-registrations.xlsx"
    resp_headers["X-Total-Count"] = str(total)
    return StreamingResponse(
        _xlsx_stream(tmp),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=resp_headers,
    )


@router.get("/new-registrations/saved-filters")
async def list_saved_filters(_auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    require_saved_filter_access(_auth["tier"])
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, filters, created_at, updated_at
            FROM saved_feed_filters
            WHERE user_id = $1 AND feed_type = 'new_registration'
            ORDER BY updated_at DESC, id DESC
            """,
            _auth["user_id"],
        )
    return {
        "filters": [
            {
                "id": row["id"],
                "name": row["name"],
                "filters": coerce_json_object(row["filters"]),
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in rows
        ]
    }


@router.post("/new-registrations/saved-filters", status_code=201)
async def create_saved_filter(body: SavedFilterCreateRequest, _auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    limit = require_saved_filter_access(_auth["tier"])
    async with get_connection() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM saved_feed_filters WHERE user_id = $1 AND feed_type = 'new_registration'",
            _auth["user_id"],
        )
        if int(count or 0) >= limit:
            raise HTTPException(
                status_code=403,
                detail=f"You have reached the saved filter limit for the {_auth['tier'].title()} plan. Upgrade to {get_next_tier(_auth['tier']) or 'a higher plan'} for more.",
            )
        row = await conn.fetchrow(
            """
            INSERT INTO saved_feed_filters (user_id, feed_type, name, filters)
            VALUES ($1, 'new_registration', $2, $3::jsonb)
            ON CONFLICT (user_id, feed_type, name)
            DO UPDATE SET filters = EXCLUDED.filters, updated_at = NOW()
            RETURNING id, name, filters, created_at, updated_at
            """,
            _auth["user_id"],
            body.name,
            json.dumps(body.filters),
        )
    return {
        "id": row["id"],
        "name": row["name"],
        "filters": coerce_json_object(row["filters"]),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


@router.delete("/new-registrations/saved-filters/{filter_id}")
async def delete_saved_filter(filter_id: int, _auth: dict = Depends(validate_api_key)) -> dict[str, bool]:
    require_saved_filter_access(_auth["tier"])
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM saved_feed_filters WHERE id = $1 AND user_id = $2",
            filter_id,
            _auth["user_id"],
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Saved filter not found.")
    return {"deleted": True}


@router.get("/new-registrations/digest")
async def get_digest_subscription(_auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    require_digest_access(_auth["tier"])
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, email, filters, active, frequency, unsubscribe_token, created_at, updated_at
            FROM feed_digest_subscriptions
            WHERE user_id = $1 AND feed_type = 'new_registration'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            _auth["user_id"],
        )
    if not row:
        return {"subscription": None}
    return {
        "subscription": {
            "id": row["id"],
            "email": row["email"],
            "filters": coerce_json_object(row["filters"]),
            "active": row["active"],
            "frequency": row["frequency"],
            "unsubscribe_url": f"/api/v1/feed/new-registrations/digest/unsubscribe/{row['unsubscribe_token']}",
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }
    }


@router.put("/new-registrations/digest")
async def upsert_digest_subscription(body: DigestSubscriptionRequest, _auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    require_digest_access(_auth["tier"])
    unsubscribe_token = secrets.token_urlsafe(24)
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO feed_digest_subscriptions (user_id, email, feed_type, filters, frequency, active, unsubscribe_token)
            VALUES ($1, $2, 'new_registration', $3::jsonb, 'weekly', $4, $5)
            ON CONFLICT (user_id, feed_type, frequency)
            DO UPDATE SET
              email = EXCLUDED.email,
              filters = EXCLUDED.filters,
              active = EXCLUDED.active,
              updated_at = NOW()
            RETURNING id, email, filters, active, frequency, unsubscribe_token, created_at, updated_at
            """,
            _auth["user_id"],
            _auth["email"],
            json.dumps(body.filters),
            body.active,
            unsubscribe_token,
        )
    return {
        "subscription": {
            "id": row["id"],
            "email": row["email"],
            "filters": coerce_json_object(row["filters"]),
            "active": row["active"],
            "frequency": row["frequency"],
            "unsubscribe_url": f"/api/v1/feed/new-registrations/digest/unsubscribe/{row['unsubscribe_token']}",
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }
    }


@router.get("/new-registrations/digest/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_digest(token: str) -> HTMLResponse:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE feed_digest_subscriptions SET active = FALSE, updated_at = NOW() WHERE unsubscribe_token = $1",
            token,
        )
    return HTMLResponse(
        '<html><body style="font-family:system-ui;max-width:440px;margin:80px auto;text-align:center">'
        '<h1 style="color:#6B4C35">Weekly digest paused</h1>'
        '<p style="color:#8a6a4a">You will no longer receive the new registration feed digest.</p>'
        '<p><a href="https://caregist.co.uk/dashboard" style="color:#C1784F">Return to CareGist</a></p>'
        '</body></html>'
    )


@router.post("/internal/new-registrations/sync")
async def sync_feed_for_internal_delivery(_auth: dict = Depends(validate_api_key)) -> dict[str, Any]:
    if _auth["tier"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    async with get_connection() as conn:
        rows = await sync_new_registration_event_payloads(conn, force=True)
        delivered = 0
        for row in rows:
            delivered += await deliver_new_registration_event(conn, row)
        digest_result = await queue_weekly_new_registration_digests(conn)
    return {
        "inserted_events": len(rows),
        "webhook_deliveries": delivered,
        "digests": digest_result,
    }
