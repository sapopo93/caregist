"""Trusted event ledger sync and feed helpers for the launch wedge."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from api.config import get_next_tier, get_tier_config, settings
from api.utils.email_queue import queue_email
from api.utils.webhook_delivery import deliver_webhook

logger = logging.getLogger("caregist.new_registration_feed")

EVENT_TYPE = "new_registration"
WEBHOOK_EVENT = "feed.new_registration"
_SYNC_COOLDOWN_SECONDS = 300
_last_sync_completed_at = 0.0


@dataclass
class FeedFilters:
    q: str | None = None
    region: str | None = None
    local_authority: str | None = None
    service_type: str | None = None
    provider_type: str | None = None
    postcode_prefix: str | None = None
    from_date: str | None = None
    to_date: str | None = None

    def to_dict(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "q": self.q,
                "region": self.region,
                "local_authority": self.local_authority,
                "service_type": self.service_type,
                "provider_type": self.provider_type,
                "postcode_prefix": self.postcode_prefix,
                "from_date": self.from_date,
                "to_date": self.to_date,
            }.items()
            if value
        }


def require_feed_access(tier: str) -> dict[str, Any]:
    config = get_tier_config(tier)
    if config.get("feed_rows", 0) <= 0:
        raise HTTPException(
            status_code=403,
            detail="The new registration feed is part of CareGist's recurring intelligence workflow. Upgrade to Starter to unlock it.",
        )
    return config


def require_saved_filter_access(tier: str) -> int:
    config = require_feed_access(tier)
    limit = int(config.get("saved_filters", 0))
    if limit <= 0:
        raise HTTPException(
            status_code=403,
            detail=f"Saved feed filters start on the Starter plan. Upgrade to {get_next_tier(tier) or 'a paid plan'} to save recurring views.",
        )
    return limit


def require_digest_access(tier: str) -> int:
    config = require_feed_access(tier)
    limit = int(config.get("feed_digests", 0))
    if limit <= 0:
        raise HTTPException(
            status_code=403,
            detail=f"Weekly feed digests start on the Starter plan. Upgrade to {get_next_tier(tier) or 'a paid plan'} to schedule them.",
        )
    return limit


def _build_filter_clause(filters: FeedFilters, start_index: int = 1) -> tuple[str, list[Any]]:
    clauses = ["tel.event_type = $1"]
    args: list[Any] = [EVENT_TYPE]
    index = start_index + 1

    if filters.q:
        clauses.append(f"(cp.name ILIKE ${index} OR cp.town ILIKE ${index} OR cp.local_authority ILIKE ${index})")
        args.append(f"%{filters.q}%")
        index += 1
    if filters.region:
        clauses.append(f"cp.region = ${index}")
        args.append(filters.region)
        index += 1
    if filters.local_authority:
        clauses.append(f"cp.local_authority = ${index}")
        args.append(filters.local_authority)
        index += 1
    if filters.service_type:
        clauses.append(f"cp.service_types ILIKE ${index}")
        args.append(f"%{filters.service_type}%")
        index += 1
    if filters.provider_type:
        clauses.append(f"cp.type = ${index}")
        args.append(filters.provider_type)
        index += 1
    if filters.postcode_prefix:
        clauses.append(f"replace(cp.postcode, ' ', '') ILIKE ${index}")
        args.append(f"{filters.postcode_prefix.replace(' ', '').upper()}%")
        index += 1
    if filters.from_date:
        clauses.append(f"tel.effective_date >= ${index}")
        args.append(filters.from_date)
        index += 1
    if filters.to_date:
        clauses.append(f"tel.effective_date <= ${index}")
        args.append(filters.to_date)
        index += 1

    return " AND ".join(clauses), args


def _build_feed_query(filters: FeedFilters, limit: int, offset: int) -> tuple[str, str, list[Any]]:
    where_sql, args = _build_filter_clause(filters)
    limit_index = len(args) + 1
    offset_index = len(args) + 2

    base = f"""
    FROM trusted_event_ledger tel
    JOIN care_providers cp
      ON cp.id = COALESCE(tel.location_id, tel.entity_id)
    WHERE {where_sql}
    """

    query = f"""
    SELECT
      tel.id,
      tel.event_type,
      tel.effective_date,
      tel.observed_at,
      tel.confidence_score,
      tel.dedupe_key,
      tel.metadata,
      cp.id AS provider_location_id,
      cp.provider_id,
      cp.slug,
      cp.name,
      cp.type,
      cp.status,
      cp.region,
      cp.local_authority,
      cp.town,
      cp.county,
      cp.postcode,
      cp.registration_date,
      cp.service_types,
      cp.website,
      cp.phone,
      cp.overall_rating
    {base}
    ORDER BY tel.effective_date DESC, tel.observed_at DESC, tel.id DESC
    LIMIT ${limit_index} OFFSET ${offset_index}
    """
    count_query = f"SELECT COUNT(*) AS total {base}"
    return query, count_query, [*args, limit, offset]


def _raw_jsonb(value: Any) -> dict[str, Any]:
    """Decode a JSONB column that may arrive as a string (raw asyncpg) or dict (app pool)."""
    if value is None:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _event_payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": EVENT_TYPE,
        "dedupe_key": row["dedupe_key"],
        "effective_date": row["effective_date"],
        "confidence_score": float(row["confidence_score"] or 0),
        "provider_id": row.get("provider_id"),
        **(_raw_jsonb(row.get("metadata"))),
    }


async def sync_new_registration_event_payloads(conn, *, force: bool = False) -> list[dict[str, Any]]:
    """Backfill / refresh canonical new-registration events from care_providers."""
    global _last_sync_completed_at
    now = time.monotonic()
    if not force and now - _last_sync_completed_at < _SYNC_COOLDOWN_SECONDS:
        return []

    inserted = await conn.fetch(
        """
        INSERT INTO trusted_event_ledger (
          entity_type,
          entity_id,
          provider_id,
          location_id,
          event_type,
          effective_date,
          observed_at,
          old_value,
          new_value,
          source,
          confidence_score,
          dedupe_key,
          metadata
        )
        SELECT
          'care_provider',
          cp.id,
          cp.provider_id,
          cp.id,
          'new_registration',
          cp.registration_date,
          COALESCE(cp.last_updated, cp.updated_at, cp.created_at, NOW()),
          NULL,
          jsonb_build_object(
            'name', cp.name,
            'slug', cp.slug,
            'status', cp.status,
            'type', cp.type,
            'registration_date', cp.registration_date,
            'region', cp.region,
            'local_authority', cp.local_authority,
            'postcode', cp.postcode,
            'service_types', cp.service_types
          ),
          'care_providers_snapshot',
          0.9900,
          CONCAT('new_registration:', cp.id, ':', cp.registration_date::text),
          jsonb_build_object(
            'name', cp.name,
            'slug', cp.slug,
            'status', cp.status,
            'type', cp.type,
            'town', cp.town,
            'county', cp.county,
            'region', cp.region,
            'local_authority', cp.local_authority,
            'postcode', cp.postcode,
            'service_types', cp.service_types
          )
        FROM care_providers cp
        WHERE cp.registration_date IS NOT NULL
          AND UPPER(COALESCE(cp.status, 'ACTIVE')) = 'ACTIVE'
        ON CONFLICT (dedupe_key) DO NOTHING
        RETURNING id, dedupe_key, entity_id, provider_id, effective_date, confidence_score, metadata
        """
    )
    _last_sync_completed_at = time.monotonic()
    return [_event_payload_from_row(dict(row)) for row in inserted]


async def sync_new_registration_events(conn, *, force: bool = False) -> int:
    return len(await sync_new_registration_event_payloads(conn, force=force))


async def list_new_registration_events(conn, filters: FeedFilters, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    query, count_query, args = _build_feed_query(filters, limit, offset)
    rows = await conn.fetch(query, *args)
    count_row = await conn.fetchrow(count_query, *args[:-2])
    total = int(count_row["total"] or 0) if count_row else 0
    return [dict(row) for row in rows], total


def event_matches_filter(payload: dict[str, Any], filter_config: dict[str, Any]) -> bool:
    if not filter_config:
        return True
    filters = FeedFilters(
        q=filter_config.get("q"),
        region=filter_config.get("region"),
        local_authority=filter_config.get("local_authority"),
        service_type=filter_config.get("service_type"),
        provider_type=filter_config.get("provider_type"),
        postcode_prefix=filter_config.get("postcode_prefix"),
        from_date=filter_config.get("from_date"),
        to_date=filter_config.get("to_date"),
    )
    effective_date = payload.get("effective_date")
    region = payload.get("region")
    local_authority = payload.get("local_authority")
    service_types = payload.get("service_types") or ""
    provider_type = payload.get("type")
    postcode = (payload.get("postcode") or "").replace(" ", "").upper()
    haystack = " ".join(
        str(value or "")
        for value in [payload.get("name"), payload.get("town"), payload.get("local_authority")]
    ).lower()

    if filters.q and filters.q.lower() not in haystack:
        return False
    if filters.region and filters.region != region:
        return False
    if filters.local_authority and filters.local_authority != local_authority:
        return False
    if filters.service_type and filters.service_type.lower() not in str(service_types).lower():
        return False
    if filters.provider_type and filters.provider_type != provider_type:
        return False
    if filters.postcode_prefix and not postcode.startswith(filters.postcode_prefix.replace(" ", "").upper()):
        return False
    if filters.from_date and effective_date and str(effective_date) < str(filters.from_date):
        return False
    if filters.to_date and effective_date and str(effective_date) > str(filters.to_date):
        return False
    return True


async def deliver_new_registration_event(conn, event_payload: dict[str, Any]) -> int:
    """Deliver one new-registration event to matching webhook subscriptions."""
    rows = await conn.fetch(
        """
        SELECT id, url, secret, filter_config
        FROM webhook_subscriptions
        WHERE active = TRUE
          AND $1 = ANY(events)
        """,
        WEBHOOK_EVENT,
    )
    delivered = 0

    for row in rows:
        raw_fc = row["filter_config"]
        filter_config = json.loads(raw_fc) if isinstance(raw_fc, str) else (raw_fc or {})
        if not event_matches_filter(event_payload, filter_config):
            continue

        existing = await conn.fetchrow(
            """
            SELECT id, delivered_at, attempt_count
            FROM webhook_delivery_log
            WHERE subscription_id = $1 AND event_type = $2 AND event_dedupe_key = $3
            """,
            row["id"],
            WEBHOOK_EVENT,
            event_payload["dedupe_key"],
        )
        if existing and existing["delivered_at"]:
            continue
        if existing is None:
            existing = await conn.fetchrow(
                """
                INSERT INTO webhook_delivery_log (
                  subscription_id, event_type, event_dedupe_key, payload, attempt_count
                )
                VALUES ($1, $2, $3, $4::jsonb, 0)
                RETURNING id, delivered_at, attempt_count
                """,
                row["id"],
                WEBHOOK_EVENT,
                event_payload["dedupe_key"],
                json.dumps(event_payload, default=str),
            )

        success, attempts, status_code, error_message = await deliver_webhook(
            row["url"],
            row["secret"],
            {
                "event": WEBHOOK_EVENT,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **event_payload,
            },
            return_metadata=True,
        )
        await conn.execute(
            """
            UPDATE webhook_delivery_log
            SET attempt_count = attempt_count + $2,
                response_status = $3,
                last_error = $4,
                last_attempt_at = NOW(),
                delivered_at = CASE WHEN $1 THEN NOW() ELSE delivered_at END
            WHERE id = $5
            """,
            success,
            attempts,
            status_code,
            error_message,
            existing["id"],
        )
        if success:
            await conn.execute(
                """
                UPDATE webhook_subscriptions
                SET last_delivery_at = NOW(), delivery_failures = 0
                WHERE id = $1
                """,
                row["id"],
            )
            delivered += 1
        else:
            await conn.execute(
                """
                UPDATE webhook_subscriptions
                SET delivery_failures = delivery_failures + 1
                WHERE id = $1
                """,
                row["id"],
            )

    return delivered


def digest_key_for_week(reference_date: date) -> str:
    iso_year, iso_week, _ = reference_date.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def build_weekly_digest_html(filters: dict[str, Any], rows: list[dict[str, Any]], digest_key: str) -> str:
    filter_lines = []
    for key, value in filters.items():
        if value:
            filter_lines.append(f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>")

    items = "".join(
        f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #E8E0D0">
            <a href="https://caregist.co.uk/provider/{row['slug']}" style="color:#6B4C35;text-decoration:none;font-weight:600">{row['name']}</a>
            <div style="font-size:12px;color:#8a6a4a;margin-top:2px">{row['town'] or ''} · {row['region'] or ''}</div>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #E8E0D0">{row['service_types'] or '—'}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #E8E0D0">{row['local_authority'] or '—'}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #E8E0D0">{row['effective_date']}</td>
        </tr>
        """
        for row in rows
    )
    filter_summary = (
        "<ul style='margin:8px 0 0 18px;padding:0;color:#6B4C35'>" + "".join(filter_lines) + "</ul>"
        if filter_lines
        else "<p style='color:#6B4C35;margin:8px 0 0'>No filters applied. This digest includes all newly registered providers in the feed.</p>"
    )
    return f"""
    <div style="font-family:system-ui, sans-serif;max-width:720px;margin:0 auto;padding:24px;background:#FDFAF5">
      <p style="color:#C1784F;font-size:12px;letter-spacing:0.18em;text-transform:uppercase;margin:0 0 8px">CareGist new registration feed</p>
      <h1 style="color:#2B2520;margin:0 0 8px;font-size:28px">Weekly newly registered providers digest</h1>
      <p style="color:#6B4C35;margin:0 0 16px">Digest window: {digest_key}. CareGist turns the raw CQC register into a recurring commercial workflow.</p>
      <div style="background:#F5EFE4;border:1px solid #D6CFC4;border-radius:12px;padding:16px;margin-bottom:20px">
        <p style="margin:0;font-weight:700;color:#2B2520">Applied filters</p>
        {filter_summary}
      </div>
      <table style="width:100%;border-collapse:collapse;background:#ffffff;border:1px solid #E8E0D0;border-radius:12px;overflow:hidden">
        <tr style="background:#F5EFE4;text-align:left">
          <th style="padding:10px 12px">Provider</th>
          <th style="padding:10px 12px">Service type</th>
          <th style="padding:10px 12px">Local authority</th>
          <th style="padding:10px 12px">Registered on</th>
        </tr>
        {items}
      </table>
      <p style="margin:20px 0 0">
        <a href="https://caregist.co.uk/dashboard" style="background:#C1784F;color:white;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:700">Open the feed in CareGist</a>
      </p>
    </div>
    """


async def queue_weekly_new_registration_digests(conn, *, reference_date: date | None = None) -> dict[str, int]:
    reference_date = reference_date or datetime.now(timezone.utc).date()
    digest_key = digest_key_for_week(reference_date)
    week_start = reference_date - timedelta(days=7)
    rows = await conn.fetch(
        """
        SELECT id, user_id, email, filters, unsubscribe_token
        FROM feed_digest_subscriptions
        WHERE feed_type = 'new_registration' AND active = TRUE
        ORDER BY id ASC
        """
    )

    queued = 0
    skipped = 0
    for row in rows:
        existing = await conn.fetchval(
            "SELECT id FROM feed_digest_delivery_log WHERE subscription_id = $1 AND digest_key = $2",
            row["id"],
            digest_key,
        )
        if existing:
            skipped += 1
            continue

        raw_f = row["filters"]
        filters = json.loads(raw_f) if isinstance(raw_f, str) else (raw_f or {})
        filter_model = FeedFilters(
            q=filters.get("q"),
            region=filters.get("region"),
            local_authority=filters.get("local_authority"),
            service_type=filters.get("service_type"),
            provider_type=filters.get("provider_type"),
            postcode_prefix=filters.get("postcode_prefix"),
            from_date=str(week_start),
            to_date=str(reference_date),
        )
        feed_rows, _ = await list_new_registration_events(conn, filter_model, limit=50, offset=0)
        if not feed_rows:
            skipped += 1
            continue

        html = build_weekly_digest_html(filters, feed_rows, digest_key)
        unsubscribe_url = f"{settings.app_url.rstrip('/')}/api/v1/feed/new-registrations/digest/unsubscribe/{row['unsubscribe_token']}"
        html += f"<p style='color:#8a6a4a;font-size:12px;margin-top:20px'>Pause this digest any time: <a href='{unsubscribe_url}' style='color:#8a6a4a'>unsubscribe</a>.</p>"
        pending_email_id = await queue_email(
            row["email"],
            f"Newly registered care providers digest — {digest_key}",
            html,
        )
        await conn.execute(
            """
            INSERT INTO feed_digest_delivery_log (subscription_id, digest_key, event_count, pending_email_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (subscription_id, digest_key) DO NOTHING
            """,
            row["id"],
            digest_key,
            len(feed_rows),
            pending_email_id,
        )
        queued += 1

    return {"queued": queued, "skipped": skipped}
