"""Provider search, detail, nearby, compare, and export endpoints."""

from __future__ import annotations

import csv
import io
import logging
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from api.config import BASIC_CSV_FIELDS, filter_fields, get_next_tier, get_tier_config, settings
from api.database import get_connection
from api.middleware.auth import validate_api_key, validate_optional_api_key
from api.middleware.rate_limit import add_rate_limit_headers
from api.queries.providers import (
    CQC_ID_LOOKUP,
    CHECK_MONITOR,
    COMPARE_QUERY,
    COUNT_USER_MONITORS,
    DEFAULT_SORT,
    DELETE_MONITOR,
    DETAIL_BY_SLUG,
    FACET_RATINGS,
    FACET_REGIONS,
    FACET_TYPES,
    INSERT_MONITOR,
    NEARBY_COUNT,
    NEARBY_QUERY,
    PROVIDER_ID_FROM_SLUG,
    RATING_HISTORY_QUERY,
    SEARCH_EXPORT,
    SORT_OPTIONS,
    build_count_query,
    build_search_query,
    classify_query,
)

logger = logging.getLogger("caregist.api")
router = APIRouter(prefix="/api/v1/providers", tags=["providers"])

# Human-readable labels for raw CQC type values
TYPE_LABELS = {
    "Social Care Org": "Care Home",
    "Primary Medical Services": "GP Surgery",
    "Primary Dental Care": "Dental Practice",
    "Independent Ambulance": "Ambulance Service",
    "Independent Healthcare Org": "Private Healthcare",
    "NHS Healthcare Organisation": "NHS Service",
}


def _row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "as_tuple"):
            d[k] = float(v)
    # Map raw CQC type to human-readable label
    if "type" in d and d["type"] in TYPE_LABELS:
        d["type"] = TYPE_LABELS[d["type"]]
    return d


def _paginated_response(data: list, total: int, page: int, per_page: int, tier: str | None = None) -> dict:
    pages = max(1, (total + per_page - 1) // per_page)
    resp: dict[str, Any] = {
        "data": data,
        "meta": {"total": total, "page": page, "per_page": per_page, "pages": pages},
    }
    if tier:
        resp["meta"]["tier"] = tier
    return resp


def _stream_headers(response: Response, disposition: str, total: int) -> dict[str, str]:
    headers = dict(response.headers)
    headers["Content-Disposition"] = disposition
    headers["X-Total-Count"] = str(total)
    return headers


@router.get("/search")
async def search_providers(
    response: Response,
    q: str | None = Query(None, max_length=500),
    region: str | None = Query(None),
    rating: str | None = Query(None),
    type: str | None = Query(None),
    service_type: str | None = Query(None),
    postcode: str | None = Query(None, max_length=10),
    sort: str = Query(DEFAULT_SORT),
    page: int = Query(1, ge=1),
    per_page: int | None = Query(None, ge=1, le=500),
    facets: bool = Query(False),
    _auth: dict = Depends(validate_optional_api_key),
) -> dict:
    """Search care providers. Handles postcodes, CQC IDs, and free text.

    Smart query classification:
    - UK postcodes (e.g. BH1 1AA) → postcode prefix search
    - CQC IDs (e.g. 1-2881562896) → direct ID lookup
    - Everything else → full-text search with ts_rank relevance
    """
    # Normalize empty string to None so SQL treats it as "no query"
    if q is not None and not q.strip():
        q = None

    # Sanitize null bytes that crash the database
    if q and "\x00" in q:
        q = q.replace("\x00", "")
        if not q.strip():
            q = None

    # Validate sort parameter
    if sort not in SORT_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid sort. Choose from: {', '.join(SORT_OPTIONS.keys())}")

    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    max_page = config["page_size"]
    per_page = min(per_page or max_page, max_page)
    offset = (page - 1) * per_page

    query_type = classify_query(q)

    try:
        async with get_connection() as conn:
            # CQC ID direct lookup
            if query_type == "cqc_id":
                rows = await conn.fetch(CQC_ID_LOOKUP, q.strip())
                total = len(rows)
                data = [filter_fields(_row_to_dict(r), tier) for r in rows]
                resp = _paginated_response(data, total, 1, per_page, tier)
                resp["meta"]["query_type"] = "cqc_id"
                return resp

            # Postcode search — route to ILIKE prefix match
            if query_type == "postcode":
                # Strip spaces and use as postcode filter, clear q for FTS
                pc = q.strip().upper().replace(" ", "")
                # Insert a space before the last 3 chars for standard format matching
                if len(pc) > 3:
                    pc_prefix = pc[:-3]
                else:
                    pc_prefix = pc

                query_sql = build_search_query(sort, has_text_query=False, is_postcode=True)
                count_sql = build_count_query(is_postcode=True)
                rows = await conn.fetch(query_sql, pc_prefix, region, rating, type, service_type, postcode, per_page, offset)
                count_row = await conn.fetchrow(count_sql, pc_prefix, region, rating, type, service_type, postcode)
                total = count_row["total"] if count_row else 0
                data = [filter_fields(_row_to_dict(r), tier) for r in rows]
                resp = _paginated_response(data, total, page, per_page, tier)
                resp["meta"]["query_type"] = "postcode"
                resp["meta"]["postcode_prefix"] = pc_prefix
                return resp

            # Standard FTS search
            has_text = query_type == "text"
            query_sql = build_search_query(sort, has_text_query=has_text)
            count_sql = build_count_query()
            rows = await conn.fetch(query_sql, q, region, rating, type, service_type, postcode, per_page, offset)
            count_row = await conn.fetchrow(count_sql, q, region, rating, type, service_type, postcode)

    except Exception as exc:
        logger.error("Search query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    total = count_row["total"] if count_row else 0
    data = [filter_fields(_row_to_dict(r), tier) for r in rows]
    resp = _paginated_response(data, total, page, per_page, tier)
    resp["meta"]["query_type"] = query_type

    # Faceted counts (optional — requested via ?facets=true)
    if facets:
        try:
            async with get_connection() as conn:
                rating_rows = await conn.fetch(FACET_RATINGS, q, region, rating, type, service_type, postcode)
                region_rows = await conn.fetch(FACET_REGIONS, q, region, rating, type, service_type, postcode)
                type_rows = await conn.fetch(FACET_TYPES, q, region, rating, type, service_type, postcode)
            resp["facets"] = {
                "ratings": {r["overall_rating"]: r["count"] for r in rating_rows},
                "regions": {r["region"]: r["count"] for r in region_rows},
                "service_types": {r["service_type"]: r["count"] for r in type_rows},
            }
        except Exception as exc:
            logger.warning("Facet query failed: %s", exc)

    return resp


@router.get("/export.csv")
async def export_providers_csv(
    response: Response,
    q: str | None = Query(None, max_length=500),
    region: str | None = Query(None),
    rating: str | None = Query(None),
    type: str | None = Query(None),
    service_type: str | None = Query(None),
    postcode: str | None = Query(None, max_length=10),
    _auth: dict = Depends(validate_api_key),
) -> StreamingResponse:
    """Export search results as CSV. Row limit depends on tier."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    row_limit = config["export"]
    if row_limit == 0:
        raise HTTPException(status_code=403, detail="CSV export requires an account. Sign up free at /signup")

    # Require at least one filter for free/starter to prevent bulk scraping
    # Pro and above can download unfiltered (within their row limit)
    if tier in ("free", "starter") and not any([q, region, rating, type, service_type, postcode]):
        raise HTTPException(status_code=400, detail="Provide at least one filter (q, region, rating, type, service_type, or postcode). Upgrade to Pro for unfiltered export.")

    # Sanitize null bytes
    if q and "\x00" in q:
        q = q.replace("\x00", "")
        if not q.strip():
            q = None

    is_basic = tier == "free"

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(SEARCH_EXPORT + " LIMIT $7", q, region, rating, type, service_type, postcode, row_limit)
            count_row = await conn.fetchrow(build_count_query(), q, region, rating, type, service_type, postcode)
    except Exception as exc:
        logger.error("Export query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Export failed.")

    if not rows:
        raise HTTPException(status_code=404, detail="No results to export.")

    total = count_row["total"] if count_row else len(rows)

    buf = io.StringIO()
    if is_basic:
        fieldnames = BASIC_CSV_FIELDS
        data = [{k: _row_to_dict(r).get(k) for k in fieldnames} for r in rows]
    else:
        data = [filter_fields(_row_to_dict(r), tier) for r in rows]
        fieldnames = [k for k in data[0].keys() if data[0][k] is not None]

    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in data:
        writer.writerow({k: v for k, v in row.items() if v is not None})

    # Log analytics + schedule follow-up email
    try:
        from api.utils.analytics import log_event
        from api.utils.email_queue import queue_email
        from datetime import datetime, timedelta, timezone
        await log_event("csv_download", "search", meta={"tier": tier, "rows": len(data), "total": total, "crm_state": "data_intent_user"})
        user_email = _auth.get("email")
        if user_email:
            await queue_email(
                user_email,
                "Your CareGist export is ready — want alerts?",
                "<p>You recently exported a provider list from CareGist.</p>"
                "<p>Want to be notified when any of these providers change their CQC rating?</p>"
                "<p><a href='https://caregist.co.uk/pricing'>Set up monitoring alerts →</a></p>",
                send_after=datetime.now(timezone.utc) + timedelta(hours=24),
            )
    except Exception:
        pass

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers=_stream_headers(response, "attachment; filename=caregist_export.csv", total),
    )


@router.get("/export.xlsx")
async def export_providers_xlsx(
    response: Response,
    q: str | None = Query(None, max_length=500),
    region: str | None = Query(None),
    rating: str | None = Query(None),
    type: str | None = Query(None),
    service_type: str | None = Query(None),
    postcode: str | None = Query(None, max_length=10),
    _auth: dict = Depends(validate_api_key),
) -> StreamingResponse:
    """Export search results as Excel (.xlsx). Row limit depends on tier."""
    import openpyxl
    from openpyxl.styles import Font

    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    row_limit = config["export"]
    if row_limit == 0:
        raise HTTPException(status_code=403, detail="Export requires an account. Sign up free at /signup")

    if tier in ("free", "starter") and not any([q, region, rating, type, service_type, postcode]):
        raise HTTPException(status_code=400, detail="Provide at least one filter. Upgrade to Pro for unfiltered export.")

    if q and "\x00" in q:
        q = q.replace("\x00", "")
        if not q.strip():
            q = None

    is_basic = tier == "free"

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(SEARCH_EXPORT + " LIMIT $7", q, region, rating, type, service_type, postcode, row_limit)
            count_row = await conn.fetchrow(build_count_query(), q, region, rating, type, service_type, postcode)
    except Exception as exc:
        logger.error("Export (xlsx) query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Export failed.")

    if not rows:
        raise HTTPException(status_code=404, detail="No results to export.")

    total = count_row["total"] if count_row else len(rows)

    if is_basic:
        fieldnames = BASIC_CSV_FIELDS
        data = [{k: _row_to_dict(r).get(k) for k in fieldnames} for r in rows]
    else:
        data = [filter_fields(_row_to_dict(r), tier) for r in rows]
        fieldnames = [k for k in data[0].keys() if data[0][k] is not None]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CareGist Export"
    ws.append(fieldnames)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in data:
        ws.append([row.get(k) for k in fieldnames])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    try:
        from api.utils.analytics import log_event
        await log_event("xlsx_download", "search", meta={"tier": tier, "rows": len(data)})
    except Exception:
        pass

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_stream_headers(response, "attachment; filename=caregist_export.xlsx", total),
    )


@router.get("/compare")
async def compare_providers(
    response: Response,
    slugs: str = Query(..., max_length=1000),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Compare providers side-by-side. Max count depends on tier."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    if config["compare"] == 0:
        raise HTTPException(status_code=403, detail="Compare requires Starter tier or above. Upgrade at /pricing")

    slug_list = [s.strip() for s in slugs.split(",") if s.strip()][:config["compare"]]
    if not slug_list:
        raise HTTPException(status_code=400, detail="Provide at least one provider slug.")

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(COMPARE_QUERY, slug_list)
    except Exception as exc:
        logger.error("Compare query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    if not rows:
        raise HTTPException(status_code=404, detail="No matching providers found.")

    return {"data": [filter_fields(_row_to_dict(r), tier) for r in rows]}


@router.get("/nearby/search")
async def nearby_providers(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, ge=0.1, le=100),
    type: str | None = Query(None),
    rating: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int | None = Query(None, ge=1, le=500),
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Find providers near a point. Requires Starter tier or above."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    add_rate_limit_headers(response, tier, _auth["remaining"])

    if not config["nearby"]:
        raise HTTPException(status_code=403, detail="Nearby search requires Starter tier or above. Upgrade at /pricing")

    max_page = config["page_size"]
    per_page = min(per_page or max_page, max_page)
    offset = (page - 1) * per_page

    try:
        async with get_connection() as conn:
            rows = await conn.fetch(NEARBY_QUERY, lon, lat, radius_km, type, rating, per_page, offset)
            count_row = await conn.fetchrow(NEARBY_COUNT, lon, lat, radius_km, type, rating)
    except Exception as exc:
        logger.error("Nearby query failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    total = count_row["total"] if count_row else 0
    data = [filter_fields(_row_to_dict(r), tier) for r in rows]
    return _paginated_response(data, total, page, per_page, tier)


# --- Monitor endpoints ---


async def _resolve_provider_id(slug: str) -> str:
    """Resolve a slug to a provider ID, raising 404 if not found."""
    async with get_connection() as conn:
        row = await conn.fetchrow(PROVIDER_ID_FROM_SLUG, slug)
    if not row:
        raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")
    return row["id"]


@router.post("/{slug}/monitor", status_code=201)
async def create_monitor(
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Monitor a provider for rating changes."""
    tier = _auth["tier"]
    config = get_tier_config(tier)
    max_monitors = config.get("monitors", 2)

    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")

    provider_id = await _resolve_provider_id(slug)

    async with get_connection() as conn:
        count_row = await conn.fetchrow(COUNT_USER_MONITORS, user_id)
        if count_row and count_row["total"] >= max_monitors:
            next_tier = get_next_tier(tier)
            raise HTTPException(
                status_code=403,
                detail=f"Monitor limit reached ({max_monitors}). Upgrade to {next_tier.title() if next_tier else 'a higher plan'} for more monitors.",
            )
        row = await conn.fetchrow(INSERT_MONITOR, user_id, provider_id)

    try:
        from api.utils.analytics import log_event
        await log_event("monitor_created", "provider", user_id=user_id, provider_id=provider_id, meta={"crm_state": "watchlist_user"})
    except Exception:
        pass

    return {"monitoring": True, "new": row is not None}


@router.delete("/{slug}/monitor")
async def remove_monitor(
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Stop monitoring a provider."""
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")

    provider_id = await _resolve_provider_id(slug)

    async with get_connection() as conn:
        await conn.execute(DELETE_MONITOR, user_id, provider_id)

    return {"monitoring": False}


@router.get("/{slug}/monitor-status")
async def monitor_status(
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Check if the current user is monitoring a provider."""
    user_id = _auth.get("user_id")
    if not user_id:
        return {"monitoring": False}

    provider_id = await _resolve_provider_id(slug)

    async with get_connection() as conn:
        row = await conn.fetchrow(CHECK_MONITOR, user_id, provider_id)

    return {"monitoring": row is not None}


@router.get("/{slug}/rating-history")
async def rating_history(
    slug: str,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Get the rating history for a provider."""
    provider_id = await _resolve_provider_id(slug)

    async with get_connection() as conn:
        rows = await conn.fetch(RATING_HISTORY_QUERY, provider_id)

    return {"data": [dict(r) for r in rows]}


# /{slug} must be last — it catches any path segment as a slug
@router.get("/{slug}")
async def get_provider(response: Response, slug: str, _auth: dict = Depends(validate_api_key)) -> dict:
    """Get a single provider by slug. Field visibility depends on tier."""
    tier = _auth["tier"]
    add_rate_limit_headers(response, tier, _auth["remaining"])

    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(DETAIL_BY_SLUG, slug)
    except Exception as exc:
        logger.error("Detail query failed for %s: %s", slug, exc)
        raise HTTPException(status_code=503, detail="Database query failed.")

    if not row:
        raise HTTPException(status_code=404, detail=f"Provider not found: {slug}")
    return {"data": filter_fields(_row_to_dict(row), tier)}
