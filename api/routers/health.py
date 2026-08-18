"""Health check endpoint (no auth required)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from api.config import settings
from api.database import get_connection
from api.metrics import render_latest, set_crm_operations, set_pending_emails
from api.middleware.internal_auth import validate_internal_token
from api.release import release_metadata
from api.middleware.rate_limit import redis_health
from api.services.cqc_freshness import get_cqc_freshness
from api.services.pipeline_health import get_pipeline_health

logger = logging.getLogger("caregist.health")
router = APIRouter(tags=["health"])


async def _crm_operations(conn) -> dict:
    calling = {
        "enabled": bool(
            settings.crm_enabled
            and settings.crm_calling_enabled
            and settings.outbound_communications_enabled
        ),
        "crm_enabled": bool(settings.crm_enabled),
        "recording_enabled": bool(settings.crm_recording_enabled),
        "ai_enabled": bool(settings.crm_ai_enabled),
        "tps_automation_enabled": bool(settings.crm_tps_automation_enabled),
    }
    if not (
        settings.crm_recording_enabled
        or settings.crm_ai_enabled
        or settings.crm_tps_automation_enabled
    ):
        return {"enabled": False, "ok": True, "calling": calling}
    async with conn.transaction():
        await conn.execute("SELECT set_config('caregist.worker', 'crm_health', true)")
        row = await conn.fetchrow(
            """
            SELECT
              EXTRACT(EPOCH FROM (NOW() - heartbeat.last_seen_at)) AS worker_age_seconds,
              heartbeat.status AS worker_status,
              COALESCE((SELECT SUM(cost_usd) FROM crm_ai_usage_attempts
                        WHERE incurred_at >= date_trunc('month', NOW())), 0) AS monthly_spend_usd,
              (SELECT COUNT(*) FROM crm_recordings
               WHERE expires_at <= NOW() AND status <> 'deleted') AS expired_backlog,
              (SELECT COUNT(*) FROM crm_recordings
               WHERE expires_at <= NOW() AND status = 'error') AS retention_failures
              ,(SELECT COUNT(*) FROM crm_tps_automation_settings
                WHERE enabled = TRUE) AS tps_enabled_organizations
              ,(SELECT COUNT(*) FROM crm_tps_automation_settings
                WHERE enabled = TRUE
                  AND (last_run_at IS NULL OR last_run_at < NOW() - INTERVAL '3 minutes'))
                AS tps_stale_organizations
              ,(SELECT COUNT(*) FROM crm_tps_automation_settings
                WHERE enabled = TRUE AND last_error IS NOT NULL)
                AS tps_failed_organizations
              ,(SELECT COUNT(*) FROM crm_tps_screening_jobs
                WHERE status IN ('queued', 'retryable', 'processing')) AS tps_pending_jobs
              ,(SELECT COUNT(*) FROM crm_tps_screening_jobs
                WHERE status = 'review_required') AS tps_review_jobs
            FROM (SELECT 1) anchor
            LEFT JOIN crm_worker_heartbeats heartbeat ON heartbeat.worker_name = 'crm_ai'
            """
        )
    result = dict(row)
    worker_required = settings.crm_ai_enabled
    worker_ok = not worker_required or (
        result["worker_age_seconds"] is not None
        and float(result["worker_age_seconds"]) <= 120
        and result["worker_status"] != "error"
    )
    result.update(
        enabled=True,
        calling=calling,
        worker_required=worker_required,
        worker_ok=worker_ok,
        retention_ok=int(result["expired_backlog"]) == 0,
        tps_ok=(
            not settings.crm_tps_automation_enabled
            or (
                int(result["tps_stale_organizations"]) == 0
                and int(result["tps_failed_organizations"]) == 0
            )
        ),
    )
    result["ok"] = result["worker_ok"] and result["retention_ok"] and result["tps_ok"]
    set_crm_operations(
        worker_age_seconds=(
            float(result["worker_age_seconds"])
            if result["worker_age_seconds"] is not None else None
        ),
        monthly_spend_usd=float(result["monthly_spend_usd"]),
        expired_backlog=int(result["expired_backlog"]),
        retention_failures=int(result["retention_failures"]),
        tps_stale_organizations=int(result["tps_stale_organizations"]),
        tps_failed_organizations=int(result["tps_failed_organizations"]),
        tps_pending_jobs=int(result["tps_pending_jobs"]),
        tps_review_jobs=int(result["tps_review_jobs"]),
    )
    return result


@router.get("/metrics")
async def metrics(_auth: dict = Depends(validate_internal_token)) -> Response:
    """Prometheus metrics endpoint (F-47).

    Refreshes the pending-email gauges from the DB, then renders all collectors.
    A DB hiccup must not break scraping, so gauge refresh failures are swallowed.
    """
    try:
        async with get_connection() as conn:
            rows = await conn.fetch(
                "SELECT status, COUNT(*) AS n FROM pending_emails GROUP BY status"
            )
            await _crm_operations(conn)
        for row in rows:
            set_pending_emails(row["status"], int(row["n"]))
    except Exception as exc:
        logger.warning("Metrics gauge refresh failed: %s", exc)

    body, content_type = render_latest()
    return Response(content=body, media_type=content_type)


@router.get("/api/v1/health/liveness")
async def liveness_check() -> JSONResponse:
    """Liveness probe — always 200 while the process can serve requests.

    No external dependencies are touched, so an orchestrator won't kill the pod
    just because the DB or Redis is briefly unavailable (that's readiness, F-25).
    """
    return JSONResponse(
        status_code=200,
        content={"status": "alive", "release": release_metadata()},
    )


@router.get("/api/v1/version")
async def version_check() -> JSONResponse:
    """Publish the immutable release identity used by deployment smoke tests."""
    return JSONResponse(
        status_code=200,
        content={"application": "caregist-api", "version": "1.0.0", "release": release_metadata()},
    )


@router.get("/api/v1/health")
async def health_check() -> JSONResponse:
    """Health check — verifies database connectivity and freshness indicators."""
    try:
        async with get_connection() as conn:
            snapshot = await get_pipeline_health(conn)
            snapshot["crm_operations"] = await _crm_operations(conn)
        snapshot["release"] = release_metadata()
        return JSONResponse(
            status_code=200,
            content=snapshot,
        )
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
            },
        )


@router.get("/api/v1/health/readiness")
async def readiness_check() -> JSONResponse:
    """Readiness check for traffic and automation dependencies (DB + Redis, F-25)."""
    try:
        async with get_connection() as conn:
            snapshot = await get_pipeline_health(conn)
            snapshot["crm_operations"] = await _crm_operations(conn)
        redis = await redis_health()
        snapshot["redis"] = redis
        snapshot["release"] = release_metadata()
        ready = bool(snapshot["readiness_ok"]) and redis["ok"] and snapshot["crm_operations"]["ok"]
        snapshot["readiness_ok"] = ready
        return JSONResponse(status_code=200 if ready else 503, content=snapshot)
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        return JSONResponse(status_code=503, content={"status": "unhealthy"})


@router.get("/api/v1/health/freshness")
async def freshness_check() -> JSONResponse:
    """Publish aggregate evidence from authoritative CQC reconciliations."""
    try:
        async with get_connection() as conn:
            snapshot = await get_cqc_freshness(conn)
        snapshot["release"] = release_metadata()
        return JSONResponse(status_code=200 if snapshot["status"] == "fresh" else 503, content=snapshot)
    except Exception as exc:
        logger.error("Freshness check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unknown",
                "source": None,
                "sourcePublishedAt": None,
                "sourceRetrievedAt": None,
                "reconciledAt": None,
                "totalSourceLocations": None,
                "checkedLocations": None,
                "successfullyCheckedLocations": None,
                "coveragePercentage": None,
                "successCount": None,
                "failureCount": None,
                "countsReconciled": False,
                "checksumSha256": None,
                "latestAttempt": None,
                "reason": "freshness_evidence_query_failed",
                "message": "Freshness cannot currently be confirmed.",
                "release": release_metadata(),
            },
        )
