"""Canonical, evidence-first query model for Radar and Intelligence Feed."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from api.config import get_tier_config


LAUNCH_EVENT_TYPES = frozenset({"new_registration", "rating_changed"})
RADAR_BROWSER_TIERS = frozenset({"radar-regional", "radar-national"})
FEED_API_TIERS = frozenset({"intelligence-feed", "embedded-enterprise", "enterprise", "admin"})
LEGACY_COMPATIBILITY_TIERS = frozenset({"alerts-pro", "starter", "pro", "business"})
OGL_ATTRIBUTION = "Contains public sector information licensed under the Open Government Licence v3.0"


@dataclass(frozen=True)
class RadarFilters:
    event_types: tuple[str, ...] = ("new_registration", "rating_changed")
    q: str | None = None
    region: str | None = None
    local_authority: str | None = None
    service_type: str | None = None
    from_date: date | None = None
    to_date: date | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "event_types": list(self.event_types),
                "q": self.q,
                "region": self.region,
                "local_authority": self.local_authority,
                "service_type": self.service_type,
                "from_date": self.from_date.isoformat() if self.from_date else None,
                "to_date": self.to_date.isoformat() if self.to_date else None,
            }.items()
            if value not in (None, [], ())
        }


def require_radar_access(tier: str, auth_method: str | None) -> dict[str, Any]:
    config = get_tier_config(tier)
    if tier in RADAR_BROWSER_TIERS and auth_method == "api_key":
        raise HTTPException(status_code=403, detail="Radar plans provide browser and email access, not machine API access.")
    if tier not in RADAR_BROWSER_TIERS | FEED_API_TIERS | LEGACY_COMPATIBILITY_TIERS:
        raise HTTPException(status_code=403, detail="A Radar or Intelligence Feed entitlement is required.")
    return config


def parse_event_types(values: list[str] | None) -> tuple[str, ...]:
    requested = tuple(dict.fromkeys(values or sorted(LAUNCH_EVENT_TYPES)))
    unsupported = sorted(set(requested) - LAUNCH_EVENT_TYPES)
    if unsupported:
        raise HTTPException(status_code=422, detail=f"Unsupported launch event types: {', '.join(unsupported)}")
    if not requested:
        raise HTTPException(status_code=422, detail="At least one event type is required.")
    return requested


def enforce_plan_scope(tier: str, filters: RadarFilters, scope_config: dict[str, Any]) -> RadarFilters:
    history_days = int(get_tier_config(tier).get("history_days") or 365)
    earliest = datetime.now(UTC).date() - timedelta(days=history_days)
    from_date = max(filters.from_date or earliest, earliest)
    if filters.to_date and filters.to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must not be earlier than from_date.")

    region = filters.region
    if tier == "radar-regional":
        configured_region = str(scope_config.get("region") or "").strip()
        if not configured_region:
            raise HTTPException(status_code=409, detail="Choose the Radar Regional territory before viewing signals.")
        if region and region.casefold() != configured_region.casefold():
            raise HTTPException(status_code=403, detail="That region is outside this Radar Regional subscription.")
        region = configured_region

    return RadarFilters(
        event_types=filters.event_types,
        q=filters.q,
        region=region,
        local_authority=filters.local_authority,
        service_type=filters.service_type,
        from_date=from_date,
        to_date=filters.to_date,
    )


def encode_cursor(observed_at: datetime, public_event_id: str) -> str:
    payload = json.dumps(
        {"observed_at": observed_at.astimezone(UTC).isoformat(), "event_id": public_event_id},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        observed_at = datetime.fromisoformat(str(payload["observed_at"]).replace("Z", "+00:00"))
        event_id = UUID(str(payload["event_id"]))
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        return observed_at, event_id
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid Radar cursor.") from exc


def _append_clause(clauses: list[str], args: list[Any], expression: str, value: Any) -> None:
    args.append(value)
    clauses.append(expression.replace("?", f"${len(args)}"))


def build_radar_query(
    filters: RadarFilters,
    *,
    cursor: tuple[datetime, UUID] | None,
    limit: int,
    public_event_id: UUID | None = None,
) -> tuple[str, list[Any]]:
    clauses = ["tel.event_type = ANY($1::text[])"]
    args: list[Any] = [list(filters.event_types)]
    if filters.q:
        _append_clause(
            clauses,
            args,
            "(cp.name ILIKE ? OR cp.town ILIKE ? OR cp.local_authority ILIKE ?)",
            f"%{filters.q}%",
        )
    if filters.region:
        _append_clause(clauses, args, "cp.region = ?", filters.region)
    if filters.local_authority:
        _append_clause(clauses, args, "cp.local_authority = ?", filters.local_authority)
    if filters.service_type:
        _append_clause(clauses, args, "cp.service_types ILIKE ?", f"%{filters.service_type}%")
    if filters.from_date:
        _append_clause(clauses, args, "tel.effective_date >= ?", filters.from_date)
    if filters.to_date:
        _append_clause(clauses, args, "tel.effective_date <= ?", filters.to_date)
    if public_event_id:
        _append_clause(clauses, args, "tel.public_event_id = ?", public_event_id)
    if cursor:
        args.extend(cursor)
        clauses.append(f"(tel.observed_at, tel.public_event_id) < (${len(args)-1}, ${len(args)})")
    args.append(limit + 1)
    query = f"""
        SELECT tel.id, tel.public_event_id, tel.schema_version, tel.entity_level,
               tel.event_type, tel.effective_date, tel.effective_at,
               tel.effective_date_source, tel.observed_at,
               tel.old_value, tel.new_value, tel.metadata,
               tel.source_published_at, tel.source_checked_at,
               tel.source_url, tel.source_snapshot_sha256,
               tel.explanation_status,
               cp.id AS cqc_location_id, cp.provider_id AS cqc_provider_id,
               cp.name, cp.slug, cp.type, cp.status, cp.region,
               cp.local_authority, cp.town, cp.postcode, cp.service_types,
               cp.overall_rating, cp.inspection_report_url,
               explanation.facts, explanation.interpretation,
               explanation.model_version, explanation.prompt_version
        FROM trusted_event_ledger tel
        JOIN care_providers cp ON cp.id = COALESCE(tel.location_id, tel.entity_id)
        LEFT JOIN LATERAL (
          SELECT facts, interpretation, model_version, prompt_version
          FROM event_explanations ee
          WHERE ee.event_id = tel.id AND ee.status = 'published'
          ORDER BY ee.reviewed_at DESC NULLS LAST, ee.created_at DESC
          LIMIT 1
        ) explanation ON TRUE
        WHERE {' AND '.join(clauses)}
        ORDER BY tel.observed_at DESC, tel.public_event_id DESC
        LIMIT ${len(args)}
    """
    return query, args


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


def effective_timing_statement(row: Any) -> str:
    """Describe CQC effective timing without substituting CareGist observation time."""
    if row["effective_at"]:
        return f"CQC published the effective timestamp as {row['effective_at'].isoformat()}."
    if row["effective_date"]:
        return f"CQC published the effective date as {row['effective_date'].isoformat()}."
    observed_at = row["observed_at"]
    return (
        "CQC did not publish an effective timestamp; CareGist first observed "
        f"this change at {observed_at.isoformat()}."
    )


def canonical_event(row: Any, *, matched_region: str | None = None) -> dict[str, Any]:
    source_url = (
        row["source_url"]
        or row["inspection_report_url"]
        or f"https://www.cqc.org.uk/location/{row['cqc_location_id']}"
    )
    facts = _json_value(row["facts"], [])
    interpretation = _json_value(row["interpretation"], [])
    explanation_status = row["explanation_status"]
    ranking_reasons = ["recent verified CQC change"]
    if matched_region:
        ranking_reasons.append(f"matches {matched_region} territory")
    if row["event_type"] == "rating_changed":
        ranking_reasons.append("rating movement selected for launch")
    return {
        "schema_version": int(row["schema_version"] or 1),
        "event_id": str(row["public_event_id"]),
        "event_type": row["event_type"],
        "entity": {
            "level": row["entity_level"] or "location",
            "cqc_location_id": row["cqc_location_id"],
            "cqc_provider_id": row["cqc_provider_id"],
            "name": row["name"],
        },
        "change": {
            "old": _json_value(row["old_value"], row["old_value"]),
            "new": _json_value(row["new_value"], row["new_value"]),
        },
        "effective_date": row["effective_date"].isoformat() if row["effective_date"] else None,
        "effective_at": row["effective_at"].isoformat() if row["effective_at"] else None,
        "effective_date_source": row["effective_date_source"],
        "effective_timing_statement": effective_timing_statement(row),
        "source_published_at": row["source_published_at"].isoformat() if row["source_published_at"] else None,
        "observed_at": row["observed_at"].isoformat(),
        "first_observed_at": row["observed_at"].isoformat(),
        "source_checked_at": row["source_checked_at"].isoformat() if row["source_checked_at"] else None,
        "source": {
            "url": source_url,
            "licence": OGL_ATTRIBUTION,
            "snapshot_sha256": row["source_snapshot_sha256"],
        },
        "evidence": [{"source_url": source_url, "type": "cqc_source"}],
        "explanation": {
            "status": explanation_status,
            "facts": facts if explanation_status == "published" else [],
            "interpretation": interpretation if explanation_status == "published" else [],
            "model_version": row["model_version"] if explanation_status == "published" else None,
            "prompt_version": row["prompt_version"] if explanation_status == "published" else None,
        },
        "ranking": {"reasons": ranking_reasons},
        "provider": {
            "slug": row["slug"],
            "type": row["type"],
            "status": row["status"],
            "region": row["region"],
            "local_authority": row["local_authority"],
            "town": row["town"],
            "postcode": row["postcode"],
            "service_types": row["service_types"],
            "overall_rating": row["overall_rating"],
        },
    }


async def list_radar_events(
    conn,
    filters: RadarFilters,
    *,
    cursor: str | None,
    limit: int,
) -> dict[str, Any]:
    decoded = decode_cursor(cursor)
    query, args = build_radar_query(filters, cursor=decoded, limit=limit)
    rows = list(await conn.fetch(query, *args))
    has_more = len(rows) > limit
    visible = rows[:limit]
    events = [canonical_event(row, matched_region=filters.region) for row in visible]
    next_cursor = None
    if has_more and visible:
        last = visible[-1]
        next_cursor = encode_cursor(last["observed_at"], str(last["public_event_id"]))
    return {"data": events, "meta": {"next_cursor": next_cursor, "has_more": has_more, "limit": limit}}


async def get_radar_event(conn, filters: RadarFilters, public_event_id: UUID) -> dict[str, Any] | None:
    query, args = build_radar_query(
        filters,
        cursor=None,
        limit=1,
        public_event_id=public_event_id,
    )
    row = await conn.fetchrow(query, *args)
    return canonical_event(row, matched_region=filters.region) if row else None
