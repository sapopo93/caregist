"""Pipeline health snapshot helpers for readiness and commerce gates.

Event activity is deliberately informational. A quiet CQC market must not make
an otherwise healthy collector appear stale; source, polling, reconciliation,
latency, and delivery are measured independently.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg

from api.config import settings
from api.services.cqc_freshness import get_cqc_freshness


SOURCE_FRESHNESS_SLA = timedelta(days=8)
SIGNAL_POLL_FRESHNESS_SLA = timedelta(minutes=75)
SHADOW_WINDOW = timedelta(days=7)
SHADOW_MIN_POLLS = 7 * 48
SHADOW_SUCCESS_RATIO = 0.99
LEDGER_LATENCY_SLA_SECONDS = 45 * 60
DELIVERY_STUCK_AFTER = timedelta(minutes=15)


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


async def _columns_exist(
    conn: asyncpg.Connection,
    table_name: str,
    column_names: tuple[str, ...],
) -> bool:
    """Return whether every required column exists without querying it directly."""
    return bool(
        await conn.fetchval(
            """
            SELECT COUNT(*) = $3
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = $1
              AND column_name = ANY($2::text[])
            """,
            table_name,
            list(column_names),
            len(column_names),
        )
    )


async def unique_index_exists(
    conn: asyncpg.Connection,
    table_name: str,
    column_names: tuple[str, ...],
) -> bool:
    """Return whether an unconditional unique index covers exactly these columns."""
    return bool(
        await conn.fetchval(
            """
            SELECT EXISTS (
              SELECT 1
              FROM pg_index AS index_record
              JOIN pg_class AS table_record ON table_record.oid = index_record.indrelid
              JOIN pg_namespace AS namespace_record ON namespace_record.oid = table_record.relnamespace
              WHERE namespace_record.nspname = 'public'
                AND table_record.relname = $1
                AND index_record.indisunique
                AND index_record.indpred IS NULL
                AND index_record.indexprs IS NULL
                AND (
                  SELECT ARRAY_AGG(attribute_record.attname::TEXT ORDER BY key_record.ordinality)
                  FROM UNNEST(index_record.indkey::SMALLINT[]) WITH ORDINALITY
                    AS key_record(attnum, ordinality)
                  JOIN pg_attribute AS attribute_record
                    ON attribute_record.attrelid = table_record.oid
                   AND attribute_record.attnum = key_record.attnum
                ) = $2::TEXT[]
            )
            """,
            table_name,
            list(column_names),
        )
    )


async def get_pipeline_health(conn: asyncpg.Connection) -> dict[str, Any]:
    """Build the operational snapshot used by readiness and checkout gating."""
    now = datetime.now(UTC)
    checks: list[dict[str, Any]] = []

    pipeline_runs_exists = await _table_exists(conn, "pipeline_runs")
    trusted_event_ledger_exists = await _table_exists(conn, "trusted_event_ledger")
    source_snapshots_exists = await _table_exists(conn, "source_snapshots")
    delivery_outbox_exists = await _table_exists(conn, "delivery_outbox")
    source_snapshot_identity_ready = bool(
        source_snapshots_exists
        and await unique_index_exists(
            conn,
            "source_snapshots",
            ("source_type", "checksum_sha256"),
        )
    )
    pipeline_source_schema_ready = bool(
        pipeline_runs_exists
        and await _columns_exist(
            conn,
            "pipeline_runs",
            (
                "source_uri",
                "source_published_at",
                "source_retrieved_at",
                "source_checksum_sha256",
                "source_record_count",
                "active_records_before",
                "active_records_after",
                "source_total_count",
                "checked_count",
                "success_count",
                "failure_count",
                "reconciled_at",
                "counts_reconciled",
            ),
        )
    )
    canonical_ledger_schema_ready = bool(
        trusted_event_ledger_exists
        and await _columns_exist(
            conn,
            "trusted_event_ledger",
            (
                "public_event_id",
                "schema_version",
                "entity_level",
                "source_published_at",
                "source_checked_at",
                "source_url",
                "source_snapshot_sha256",
                "explanation_status",
            ),
        )
    )

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

    latest_signal_run = None
    poll_window = None
    if pipeline_runs_exists:
        latest_signal_run = await conn.fetchrow(
            """
            SELECT run_type, status, started_at, completed_at, error_message
            FROM pipeline_runs
            WHERE run_type = 'signal_poll'
            ORDER BY COALESCE(completed_at, started_at) DESC NULLS LAST
            LIMIT 1
            """
        )
        poll_window = await conn.fetchrow(
            """
            SELECT COUNT(*)::int AS total_polls,
                   COUNT(*) FILTER (WHERE status = 'completed')::int AS completed_polls
            FROM pipeline_runs
            WHERE run_type = 'signal_poll'
              AND started_at >= NOW() - INTERVAL '7 days'
            """
        )
    authoritative_freshness = await get_cqc_freshness(conn, now=now)

    latest_event = None
    latency = None
    if trusted_event_ledger_exists:
        latest_event = await conn.fetchrow(
            """
            SELECT MAX(observed_at) AS latest_observed_at,
                   MAX(effective_date) AS latest_effective_date
            FROM trusted_event_ledger
            WHERE event_type IN ('new_registration', 'rating_changed')
            """
        )
        if canonical_ledger_schema_ready:
            latency = await conn.fetchrow(
                """
                SELECT COUNT(*)::int AS measured_events,
                       percentile_cont(0.95) WITHIN GROUP (
                         ORDER BY EXTRACT(EPOCH FROM (observed_at - source_published_at))
                       ) AS p95_seconds
                FROM trusted_event_ledger
                WHERE event_type IN ('new_registration', 'rating_changed')
                  AND source_published_at IS NOT NULL
                  AND observed_at >= source_published_at
                  AND observed_at >= NOW() - INTERVAL '7 days'
                """
            )

    delivery = None
    if delivery_outbox_exists:
        delivery = await conn.fetchrow(
            """
            SELECT COUNT(*) FILTER (WHERE status = 'pending')::int AS pending,
                   COUNT(*) FILTER (
                     WHERE (status = 'pending'
                            AND available_at < NOW() - INTERVAL '15 minutes')
                        OR (status = 'processing'
                            AND locked_at < NOW() - INTERVAL '15 minutes')
                   )::int AS stuck,
                   COUNT(*) FILTER (WHERE status = 'dead_letter')::int AS dead_letter
            FROM delivery_outbox
            """
        )

    signal_completed_at = _as_utc(
        latest_signal_run["completed_at"] if latest_signal_run else None
    )
    signal_started_at = _as_utc(
        latest_signal_run["started_at"] if latest_signal_run else None
    )
    signal_status = latest_signal_run["status"] if latest_signal_run else None
    signal_poll_fresh = bool(
        signal_status == "completed"
        and signal_completed_at is not None
        and signal_completed_at >= now - SIGNAL_POLL_FRESHNESS_SLA
    )

    total_polls = int(poll_window["total_polls"] or 0) if poll_window else 0
    completed_polls = int(poll_window["completed_polls"] or 0) if poll_window else 0
    poll_success_ratio = completed_polls / total_polls if total_polls else 0.0
    poll_coverage_ok = bool(
        total_polls >= SHADOW_MIN_POLLS and poll_success_ratio >= SHADOW_SUCCESS_RATIO
    )

    latest_observed_at = _as_utc(latest_event["latest_observed_at"] if latest_event else None)
    latest_effective_date = latest_event["latest_effective_date"] if latest_event else None
    source_published_value = authoritative_freshness["sourcePublishedAt"]
    source_retrieved_value = authoritative_freshness["sourceRetrievedAt"]
    source_retrieved_at = (
        datetime.fromisoformat(source_retrieved_value) if source_retrieved_value else None
    )
    source_age = now - source_retrieved_at if source_retrieved_at else None
    source_fresh = authoritative_freshness["status"] == "fresh"
    source_location_count = authoritative_freshness["totalSourceLocations"]
    active_location_count = int(units["active_location_rows"] or 0)
    counts_reconciled = bool(authoritative_freshness["countsReconciled"])

    measured_events = int(latency["measured_events"] or 0) if latency else 0
    p95_seconds = float(latency["p95_seconds"]) if latency and latency["p95_seconds"] is not None else None
    latency_ok = bool(
        measured_events > 0
        and p95_seconds is not None
        and p95_seconds <= LEDGER_LATENCY_SLA_SECONDS
    )

    pending_deliveries = int(delivery["pending"] or 0) if delivery else 0
    stuck_deliveries = int(delivery["stuck"] or 0) if delivery else 0
    dead_letter_deliveries = int(delivery["dead_letter"] or 0) if delivery else 0
    delivery_healthy = bool(
        delivery_outbox_exists and stuck_deliveries == 0 and dead_letter_deliveries == 0
    )

    source_details = {
        "source": "Care Quality Commission public directory",
        "sourceUri": authoritative_freshness["source"],
        "sourcePublishedAt": source_published_value,
        "sourceRetrievedAt": source_retrieved_value,
        "reconciledAt": authoritative_freshness["reconciledAt"],
        "checksumSha256": authoritative_freshness["checksumSha256"],
        "sourceLocationCount": source_location_count,
        "checkedLocationCount": authoritative_freshness["checkedLocations"],
        "successCount": authoritative_freshness["successCount"],
        "failureCount": authoritative_freshness["failureCount"],
        "coveragePercentage": authoritative_freshness["coveragePercentage"],
        "activeLocationCount": active_location_count,
        "countsReconciled": counts_reconciled,
        "freshnessStatus": authoritative_freshness["status"],
        "reason": authoritative_freshness["reason"],
        "ageHours": round(source_age.total_seconds() / 3600, 1) if source_age else None,
        "slaHours": int(SOURCE_FRESHNESS_SLA.total_seconds() // 3600),
    }
    checks.extend(
        [
            {
                "name": "canonical_signal_schema",
                "ok": (
                    pipeline_source_schema_ready
                    and canonical_ledger_schema_ready
                    and source_snapshot_identity_ready
                ),
                "details": {
                    "pipelineSourceColumnsReady": pipeline_source_schema_ready,
                    "trustedLedgerColumnsReady": canonical_ledger_schema_ready,
                    "sourceSnapshotsReady": source_snapshots_exists,
                    "sourceSnapshotIdentityReady": source_snapshot_identity_ready,
                    "deliveryOutboxReady": delivery_outbox_exists,
                },
            },
            {"name": "cqc_source_watermark", "ok": source_fresh, "details": source_details},
            {
                "name": "source_count_reconciliation",
                "ok": counts_reconciled,
                "details": {
                    "sourceLocationCount": source_location_count,
                    "activeLocationCount": active_location_count,
                },
            },
            {
                "name": "signal_poll_execution",
                "ok": signal_poll_fresh,
                "details": {
                    "latestStatus": signal_status,
                    "latestStartedAt": _as_iso(signal_started_at),
                    "latestCompletedAt": _as_iso(signal_completed_at),
                    "error": latest_signal_run["error_message"] if latest_signal_run else None,
                    "slaMinutes": int(SIGNAL_POLL_FRESHNESS_SLA.total_seconds() // 60),
                },
            },
            {
                "name": "signal_poll_shadow_coverage",
                "ok": poll_coverage_ok,
                "details": {
                    "windowDays": int(SHADOW_WINDOW.total_seconds() // 86400),
                    "totalPolls": total_polls,
                    "completedPolls": completed_polls,
                    "successRatio": round(poll_success_ratio, 5),
                    "minimumPolls": SHADOW_MIN_POLLS,
                    "minimumSuccessRatio": SHADOW_SUCCESS_RATIO,
                },
            },
            {
                "name": "approved_source_to_ledger_latency",
                "ok": latency_ok,
                "details": {
                    "measuredEvents": measured_events,
                    "p95Minutes": round(p95_seconds / 60, 2) if p95_seconds is not None else None,
                    "targetMinutes": LEDGER_LATENCY_SLA_SECONDS // 60,
                },
            },
            {
                "name": "delivery_outbox_health",
                "ok": delivery_healthy,
                "details": {
                    "pending": pending_deliveries,
                    "stuck": stuck_deliveries,
                    "deadLetter": dead_letter_deliveries,
                    "stuckAfterMinutes": int(DELIVERY_STUCK_AFTER.total_seconds() // 60),
                },
            },
            {
                "name": "latest_signal_activity",
                "ok": True,
                "informational": True,
                "details": {
                    "latestObservedAt": _as_iso(latest_observed_at),
                    "latestEffectiveDate": (
                        latest_effective_date.isoformat() if latest_effective_date else None
                    ),
                },
            },
            {
                # Compatibility check name retained for existing monitors. It now
                # reflects collector freshness, not the age of the newest event.
                "name": "new_registration_feed_freshness",
                "ok": signal_poll_fresh,
                "details": {
                    "latestObservedAt": _as_iso(latest_observed_at),
                    "latestEffectiveDate": (
                        latest_effective_date.isoformat() if latest_effective_date else None
                    ),
                    "collectorFresh": signal_poll_fresh,
                    "eventAgeIsInformational": True,
                },
            },
        ]
    )

    readiness_ok = bool(
        pipeline_runs_exists
        and trusted_event_ledger_exists
        and pipeline_source_schema_ready
        and canonical_ledger_schema_ready
        and source_snapshot_identity_ready
    )
    freshness_ok = source_fresh and counts_reconciled and signal_poll_fresh
    checkout_ready = bool(
        readiness_ok
        and source_snapshots_exists
        and delivery_outbox_exists
        and freshness_ok
        and poll_coverage_ok
        and latency_ok
        and delivery_healthy
        and settings.radar_delivery_enabled
    )
    status = "healthy" if readiness_ok and freshness_ok else "degraded"

    return {
        "status": status,
        "generated_at": now.isoformat(),
        "readiness_ok": readiness_ok,
        "freshness_ok": freshness_ok,
        "source_fresh": source_fresh,
        "feed_fresh": signal_poll_fresh,
        "source": source_details,
        "eventActivity": {
            "latestObservedAt": _as_iso(latest_observed_at),
            "latestEffectiveDate": latest_effective_date.isoformat() if latest_effective_date else None,
            "informational": True,
        },
        "delivery": {
            "enabled": settings.radar_delivery_enabled,
            "healthy": delivery_healthy,
            "pending": pending_deliveries,
            "stuck": stuck_deliveries,
            "deadLetter": dead_letter_deliveries,
        },
        "commercialReadiness": {
            "checkoutReady": checkout_ready,
            "shadowCoveragePassed": poll_coverage_ok,
            "ledgerLatencyPassed": latency_ok,
            "deliveryEnabled": settings.radar_delivery_enabled,
            "deliveryHealthy": delivery_healthy,
            "explanationsRequired": False,
        },
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
