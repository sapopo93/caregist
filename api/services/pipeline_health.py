"""Pipeline health snapshot helpers for readiness and freshness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg


FRESHNESS_SLA = timedelta(days=7)
RUN_WINDOW = timedelta(days=1)


def _as_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


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

    latest_run = None
    if pipeline_runs_exists:
        latest_run = await conn.fetchrow(
            """
            SELECT run_type, status, started_at, completed_at, error_message
            FROM pipeline_runs
            WHERE run_type IN ('incremental', 'feed_cycle')
            ORDER BY COALESCE(completed_at, started_at) DESC NULLS LAST
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

    latest_completed_at = latest_run["completed_at"] if latest_run else None
    latest_started_at = latest_run["started_at"] if latest_run else None
    latest_status = latest_run["status"] if latest_run else None
    latest_observed_at = latest_event["latest_observed_at"] if latest_event else None
    latest_effective_date = latest_event["latest_effective_date"] if latest_event else None

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
    status = "healthy" if readiness_ok and feed_fresh else "degraded"

    return {
        "status": status,
        "generated_at": now.isoformat(),
        "readiness_ok": readiness_ok,
        "feed_fresh": feed_fresh,
        "checks": checks,
    }
