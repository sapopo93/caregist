"""Pipeline health snapshot helpers for readiness and freshness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg


FRESHNESS_SLA = timedelta(days=7)
SOURCE_FRESHNESS_SLA = timedelta(days=8)
RUN_WINDOW = timedelta(days=1)


def _as_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _table_exists(conn: asyncpg.Connection, table_name: str) -> bool:
    return bool(
        await conn.fetchval(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = $1
            )
            """,
            table_name,
        )
    )


async def get_pipeline_health(conn: asyncpg.Connection) -> dict[str, Any]:
    """Build a lightweight operational snapshot from pipeline and ledger tables."""
    now = datetime.now(UTC)
    checks: list[dict[str, Any]] = []

    pipeline_runs_exists = await _table_exists(conn, "pipeline_runs")
    trusted_event_ledger_exists = await _table_exists(conn, "trusted_event_ledger")

    units = await conn.fetchrow(
        """
        SELECT COUNT(*) AS location_rows,
               COUNT(*) FILTER (WHERE UPPER(status) = 'ACTIVE') AS active_location_rows,
               COUNT(DISTINCT provider_id) FILTER (
                 WHERE UPPER(status) = 'ACTIVE'
                   AND provider_id IS NOT NULL
                   AND provider_id != ''
               ) AS active_provider_organisations,
               COUNT(DISTINCT provider_id) FILTER (
                 WHERE UPPER(status) = 'ACTIVE'
                   AND provider_id IS NOT NULL
                   AND provider_id != ''
                   AND group_name IS NOT NULL
                   AND BTRIM(group_name) != ''
               ) AS grouped_provider_organisations,
               COUNT(DISTINCT BTRIM(group_name)) FILTER (
                 WHERE UPPER(status) = 'ACTIVE'
                   AND group_name IS NOT NULL
                   AND BTRIM(group_name) != ''
               ) AS named_group_labels
        FROM care_providers
        """
    )

    latest_run = None
    if pipeline_runs_exists:
        latest_run = await conn.fetchrow(
            """
            SELECT run_type, status, started_at, completed_at, error_message
            FROM pipeline_runs
            WHERE run_type = 'incremental'
            ORDER BY COALESCE(completed_at, started_at) DESC NULLS LAST
            LIMIT 1
            """
        )

    latest_source_run = None
    if pipeline_runs_exists:
        latest_source_run = await conn.fetchrow(
            """
            SELECT source_uri, source_published_at, source_retrieved_at,
                   source_checksum_sha256, source_record_count,
                   active_records_before, active_records_after, completed_at
            FROM pipeline_runs
            WHERE run_type = 'incremental'
              AND status = 'completed'
              AND source_published_at IS NOT NULL
            ORDER BY source_published_at DESC, completed_at DESC
            LIMIT 1
            """
        )

    latest_event = None
    if trusted_event_ledger_exists:
        latest_event = await conn.fetchrow(
            """
            SELECT MAX(observed_at) AS latest_observed_at,
                   MAX(effective_date) AS latest_effective_date
            FROM trusted_event_ledger
            WHERE event_type = 'new_registration'
            """
        )

    latest_completed_at = _as_utc(latest_run["completed_at"] if latest_run else None)
    latest_started_at = _as_utc(latest_run["started_at"] if latest_run else None)
    latest_status = latest_run["status"] if latest_run else None
    latest_observed_at = _as_utc(latest_event["latest_observed_at"] if latest_event else None)
    latest_effective_date = latest_event["latest_effective_date"] if latest_event else None
    source_published_date = latest_source_run["source_published_at"] if latest_source_run else None
    source_published_at = (
        datetime.combine(source_published_date, datetime.min.time(), tzinfo=UTC)
        if source_published_date
        else None
    )
    source_age = now - source_published_at if source_published_at else None
    source_fresh = bool(source_age is not None and source_age <= SOURCE_FRESHNESS_SLA)
    source_location_count = latest_source_run["source_record_count"] if latest_source_run else None
    active_location_count = int(units["active_location_rows"] or 0)
    counts_reconciled = bool(
        source_location_count is not None and active_location_count == int(source_location_count)
    )

    recent_run_ok = bool(
        latest_status == "completed"
        and latest_completed_at is not None
        and latest_completed_at >= now - RUN_WINDOW
    )
    feed_fresh = bool(
        latest_observed_at is not None
        and latest_observed_at >= now - FRESHNESS_SLA
    )

    checks.append(
        {
            "name": "cqc_source_watermark",
            "ok": source_fresh,
            "details": {
                "source": "Care Quality Commission public directory",
                "sourceUri": latest_source_run["source_uri"] if latest_source_run else None,
                "sourcePublishedAt": source_published_date.isoformat() if source_published_date else None,
                "sourceRetrievedAt": _as_iso(
                    _as_utc(latest_source_run["source_retrieved_at"] if latest_source_run else None)
                ),
                "checksumSha256": latest_source_run["source_checksum_sha256"] if latest_source_run else None,
                "sourceLocationCount": source_location_count,
                "activeLocationCount": active_location_count,
                "previousActiveLocationCount": latest_source_run["active_records_before"] if latest_source_run else None,
                "countsReconciled": counts_reconciled,
                "ageHours": round(source_age.total_seconds() / 3600, 1) if source_age else None,
                "slaHours": int(SOURCE_FRESHNESS_SLA.total_seconds() // 3600),
            },
        }
    )
    checks.append(
        {
            "name": "pipeline_runs_table",
            "ok": pipeline_runs_exists,
            "details": {
                "present": pipeline_runs_exists,
            },
        }
    )
    checks.append(
        {
            "name": "trusted_event_ledger_table",
            "ok": trusted_event_ledger_exists,
            "details": {
                "present": trusted_event_ledger_exists,
            },
        }
    )
    checks.append(
        {
            "name": "recent_pipeline_run",
            "ok": recent_run_ok,
            "details": {
                "latestRunType": latest_run["run_type"] if latest_run else None,
                "latestStatus": latest_status,
                "latestStartedAt": _as_iso(latest_started_at),
                "latestCompletedAt": _as_iso(latest_completed_at),
                "error": latest_run["error_message"] if latest_run else None,
            },
        }
    )
    checks.append(
        {
            "name": "new_registration_feed_freshness",
            "ok": feed_fresh,
            "details": {
                "latestObservedAt": _as_iso(latest_observed_at),
                "latestEffectiveDate": latest_effective_date.isoformat() if latest_effective_date else None,
                "slaHours": int(FRESHNESS_SLA.total_seconds() // 3600),
            },
        }
    )

    readiness_ok = pipeline_runs_exists and trusted_event_ledger_exists
    freshness_ok = source_fresh and feed_fresh and recent_run_ok and counts_reconciled
    status = "healthy" if readiness_ok and freshness_ok else "degraded"

    return {
        "status": status,
        "generated_at": now.isoformat(),
        "readiness_ok": readiness_ok,
        "freshness_ok": freshness_ok,
        "source_fresh": source_fresh,
        "feed_fresh": feed_fresh,
        "source": next(check["details"] for check in checks if check["name"] == "cqc_source_watermark"),
        "units": {
            "locationRows": int(units["location_rows"] or 0),
            "activeLocationRows": active_location_count,
            "activeProviderOrganisations": int(units["active_provider_organisations"] or 0),
            "groupedProviderOrganisations": int(units["grouped_provider_organisations"] or 0),
            "namedGroupLabels": int(units["named_group_labels"] or 0),
            "sourceActiveLocationRows": source_location_count,
            "countsReconciled": counts_reconciled,
        },
        "checks": checks,
    }
