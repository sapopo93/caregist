"""Internal support-platform routes."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from api.database import get_connection
from api.middleware.internal_auth import validate_internal_token
from api.services.pipeline_health import get_pipeline_health
from api.utils.email_queue import process_email_queue

logger = logging.getLogger("caregist.internal")
router = APIRouter(prefix="/internal", tags=["internal"])


class InternalRemediationRequest(BaseModel):
    action: str = Field(min_length=3)
    tenantId: str
    payload: dict[str, Any] = Field(default_factory=dict)


async def _complete_task(task_id: str, result: dict[str, Any]) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE internal_tasks
            SET status = 'completed',
                result = $2::jsonb,
                completed_at = NOW()
            WHERE id = $1
            """,
            task_id,
            json.dumps(result),
        )


async def _fail_task(task_id: str, error: str) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE internal_tasks
            SET status = 'failed',
                error = $2,
                completed_at = NOW()
            WHERE id = $1
            """,
            task_id,
            error,
        )


def _provider_identifier(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    provider_id = str(payload.get("providerId", "")).strip() or None
    provider_slug = str(payload.get("providerSlug", "")).strip() or None
    return provider_id, provider_slug


async def _refresh_profile_projection(payload: dict[str, Any]) -> dict[str, Any]:
    provider_id, provider_slug = _provider_identifier(payload)
    async with get_connection() as conn:
        if provider_id:
            updated = await conn.execute(
                """
                UPDATE care_providers
                SET profile_updated_at = NOW()
                WHERE id = $1
                """,
                provider_id,
            )
        elif provider_slug:
            updated = await conn.execute(
                """
                UPDATE care_providers
                SET profile_updated_at = NOW()
                WHERE slug = $1
                """,
                provider_slug,
            )
        else:
            updated = await conn.execute(
                """
                UPDATE care_providers
                SET profile_updated_at = NOW()
                WHERE is_claimed = true OR profile_tier IS NOT NULL
                """,
            )
    return {
        "action": "caregist:refresh_profile_projection",
        "updated": updated,
        "providerId": provider_id,
        "providerSlug": provider_slug,
    }


async def _retry_profile_update_ingestion(payload: dict[str, Any]) -> dict[str, Any]:
    provider_id, provider_slug = _provider_identifier(payload)
    async with get_connection() as conn:
        if provider_id:
            updated = await conn.execute(
                """
                UPDATE care_providers
                SET profile_updated_at = NOW()
                WHERE id = $1
                  AND (profile_updated_at IS NULL OR profile_updated_at < NOW() - INTERVAL '1 day')
                """,
                provider_id,
            )
        elif provider_slug:
            updated = await conn.execute(
                """
                UPDATE care_providers
                SET profile_updated_at = NOW()
                WHERE slug = $1
                  AND (profile_updated_at IS NULL OR profile_updated_at < NOW() - INTERVAL '1 day')
                """,
                provider_slug,
            )
        else:
            updated = await conn.execute(
                """
                UPDATE care_providers
                SET profile_updated_at = NOW()
                WHERE profile_tier IS NOT NULL
                  AND (profile_updated_at IS NULL OR profile_updated_at < NOW() - INTERVAL '1 day')
                """,
            )
    return {
        "action": "caregist:retry_profile_update_ingestion",
        "updated": updated,
        "providerId": provider_id,
        "providerSlug": provider_slug,
    }


async def _rebuild_listing_index(_: dict[str, Any]) -> dict[str, Any]:
    async with get_connection() as conn:
        await conn.execute("REINDEX INDEX idx_search")
    return {
        "action": "caregist:rebuild_listing_index",
        "index": "idx_search",
        "rebuilt": True,
    }


async def _regenerate_export_artifact(_: dict[str, Any]) -> dict[str, Any]:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS active_providers,
                   MAX(updated_at) AS last_provider_update
            FROM care_providers
            WHERE UPPER(status) = 'ACTIVE'
            """
        )
    return {
        "action": "caregist:regenerate_export_artifact",
        "activeProviders": int(row["active_providers"] or 0),
        "lastProviderUpdate": row["last_provider_update"].isoformat() if row["last_provider_update"] else None,
        "artifactGeneratedAt": datetime.now(timezone.utc).isoformat(),
    }


async def _revalidate_report_schema(_: dict[str, Any]) -> dict[str, Any]:
    required_columns = {
        "care_providers": {
            "id",
            "provider_id",
            "name",
            "slug",
            "overall_rating",
            "quality_score",
            "quality_tier",
            "profile_tier",
            "profile_completeness",
        }
    }

    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = ANY($1::text[])
            """,
            list(required_columns.keys()),
        )

    actual: dict[str, set[str]] = {}
    for row in rows:
        actual.setdefault(str(row["table_name"]), set()).add(str(row["column_name"]))

    missing = {
        table: sorted(columns - actual.get(table, set()))
        for table, columns in required_columns.items()
    }
    schema_valid = all(not values for values in missing.values())

    return {
        "action": "caregist:revalidate_report_schema",
        "schemaValid": schema_valid,
        "missing": missing,
    }


async def _retry_claim_verification(payload: dict[str, Any]) -> dict[str, Any]:
    claim_id = payload.get("claimId")
    async with get_connection() as conn:
        if claim_id:
            updated = await conn.execute(
                """
                UPDATE provider_claims
                SET fast_track = true,
                    submitted_at = NOW()
                WHERE id = $1 AND status = 'pending'
                """,
                int(claim_id),
            )
        else:
            updated = await conn.execute(
                """
                UPDATE provider_claims
                SET fast_track = true,
                    submitted_at = NOW()
                WHERE status = 'pending'
                """,
            )
    return {
        "action": "caregist:retry_claim_verification",
        "updated": updated,
        "claimId": claim_id,
    }


async def _resume_failed_enquiry_delivery(payload: dict[str, Any]) -> dict[str, Any]:
    batch_size = int(payload.get("batchSize", 20))
    sent = await process_email_queue(batch_size=batch_size)
    return {
        "action": "caregist:resume_failed_enquiry_delivery",
        "batchSize": batch_size,
        "sent": sent,
    }


async def _recompute_profile_completeness(_: dict[str, Any]) -> dict[str, Any]:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE care_providers
            SET profile_completeness = calculate_profile_completeness(
                profile_description,
                profile_photos,
                virtual_tour_url,
                inspection_response,
                is_claimed,
                profile_tier
            )
            """
        )
        stats = await conn.fetchrow(
            """
            SELECT COUNT(*) AS provider_count,
                   AVG(profile_completeness)::numeric(10,2) AS average_completeness
            FROM care_providers
            """
        )
    return {
        "action": "caregist:recompute_profile_completeness",
        "providerCount": int(stats["provider_count"] or 0),
        "averageCompleteness": float(stats["average_completeness"] or 0.0),
    }


ACTION_HANDLERS = {
    "caregist:refresh_profile_projection": _refresh_profile_projection,
    "caregist:retry_profile_update_ingestion": _retry_profile_update_ingestion,
    "caregist:rebuild_listing_index": _rebuild_listing_index,
    "caregist:regenerate_export_artifact": _regenerate_export_artifact,
    "caregist:revalidate_report_schema": _revalidate_report_schema,
    "caregist:retry_claim_verification": _retry_claim_verification,
    "caregist:resume_failed_enquiry_delivery": _resume_failed_enquiry_delivery,
    "caregist:recompute_profile_completeness": _recompute_profile_completeness,
}


async def _run_internal_task(task_id: str, action: str, payload: dict[str, Any]) -> None:
    try:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE internal_tasks SET status = 'running', started_at = NOW() WHERE id = $1",
                task_id,
            )

        handler = ACTION_HANDLERS.get(action)
        if not handler:
            raise ValueError(f"Unsupported internal action: {action}")

        await asyncio.sleep(0)
        result = await handler(payload)
        await _complete_task(task_id, result)
    except Exception as exc:
        logger.exception("Internal remediation task failed: %s", exc)
        await _fail_task(task_id, str(exc))


@router.get("/diagnostics")
async def internal_diagnostics(_auth=Depends(validate_internal_token)) -> dict[str, Any]:
    async with get_connection() as conn:
        await conn.fetchrow("SELECT 1")
        counts = await conn.fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM care_providers WHERE UPPER(status) = 'ACTIVE') AS active_providers,
              (SELECT COUNT(*) FROM provider_claims WHERE status = 'pending') AS pending_claims,
              (SELECT COUNT(*) FROM pending_emails WHERE status = 'pending') AS pending_emails,
              (SELECT COUNT(*) FROM internal_tasks WHERE status IN ('pending', 'running')) AS pending_internal_tasks,
              (SELECT COALESCE(AVG(profile_completeness), 0) FROM care_providers) AS avg_profile_completeness
            """
        )
    return {
        "status": "ok",
        "database": "connected",
        "pendingInternalTasks": int(counts["pending_internal_tasks"] or 0),
        "providers": {
            "active": int(counts["active_providers"] or 0),
            "avgProfileCompleteness": float(counts["avg_profile_completeness"] or 0.0),
        },
        "claims": {
            "pending": int(counts["pending_claims"] or 0),
        },
        "emailQueue": {
            "pending": int(counts["pending_emails"] or 0),
        },
    }


@router.get("/pipeline")
async def internal_pipeline_status(_auth=Depends(validate_internal_token)) -> dict[str, Any]:
    async with get_connection() as conn:
        snapshot = await get_pipeline_health(conn)
        runs = await conn.fetch(
            """
            SELECT run_type, status, started_at, completed_at, records_added, records_updated, error_message
            FROM pipeline_runs
            WHERE run_type IN ('incremental', 'feed_cycle')
            ORDER BY started_at DESC
            LIMIT 10
            """
        )
        ledger = await conn.fetchrow(
            """
            SELECT
              COUNT(*) AS total_new_registration_events,
              COUNT(*) FILTER (WHERE observed_at >= NOW() - INTERVAL '7 days') AS new_registration_events_last_7d,
              MAX(observed_at) AS latest_observed_at,
              MAX(effective_date) AS latest_effective_date
            FROM trusted_event_ledger
            WHERE event_type = 'new_registration'
            """
        )

    return {
        "status": snapshot["status"],
        "readiness_ok": snapshot["readiness_ok"],
        "feed_fresh": snapshot["feed_fresh"],
        "checks": snapshot["checks"],
        "ledger": {
            "totalNewRegistrationEvents": int(ledger["total_new_registration_events"] or 0) if ledger else 0,
            "newRegistrationEventsLast7d": int(ledger["new_registration_events_last_7d"] or 0) if ledger else 0,
            "latestObservedAt": ledger["latest_observed_at"].isoformat() if ledger and ledger["latest_observed_at"] else None,
            "latestEffectiveDate": ledger["latest_effective_date"].isoformat() if ledger and ledger["latest_effective_date"] else None,
        },
        "recentRuns": [
            {
                "runType": row["run_type"],
                "status": row["status"],
                "startedAt": row["started_at"].isoformat() if row["started_at"] else None,
                "completedAt": row["completed_at"].isoformat() if row["completed_at"] else None,
                "recordsAdded": int(row["records_added"] or 0),
                "recordsUpdated": int(row["records_updated"] or 0),
                "error": row["error_message"],
            }
            for row in runs
        ],
    }


@router.post("/remediate", status_code=202)
async def internal_remediate(
    request: InternalRemediationRequest,
    background_tasks: BackgroundTasks,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    _auth=Depends(validate_internal_token),
) -> dict[str, str]:
    async with get_connection() as conn:
        if x_idempotency_key:
            existing = await conn.fetchrow(
                """
                SELECT id, status
                FROM internal_tasks
                WHERE idempotency_key = $1
                """,
                x_idempotency_key,
            )
            if existing:
                return {"taskId": str(existing["id"]), "status": existing["status"]}

        row = await conn.fetchrow(
            """
            INSERT INTO internal_tasks (action, tenant_id, status, payload, idempotency_key)
            VALUES ($1, $2, 'pending', $3::jsonb, $4)
            RETURNING id
            """,
            request.action,
            request.tenantId,
            json.dumps(request.payload),
            x_idempotency_key,
        )
    task_id = str(row["id"])
    background_tasks.add_task(_run_internal_task, task_id, request.action, request.payload)
    return {"taskId": task_id, "status": "pending"}


@router.get("/tasks/{task_id}")
async def get_internal_task(task_id: str, _auth=Depends(validate_internal_token)) -> dict[str, Any]:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, action, status, result, error, created_at, completed_at
            FROM internal_tasks
            WHERE id = $1
            """,
            task_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found.")

    data = dict(row)
    return {
        "id": str(data["id"]),
        "action": data["action"],
        "status": data["status"],
        "result": data["result"],
        "error": data["error"],
        "createdAt": data["created_at"].isoformat() if data["created_at"] else None,
        "completedAt": data["completed_at"].isoformat() if data["completed_at"] else None,
    }
