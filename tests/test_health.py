from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


@pytest.mark.asyncio
async def test_preview_database_failure_starts_explicitly_degraded():
    with patch("api.main.init_pool", new=AsyncMock(side_effect=RuntimeError("database unavailable"))), \
         patch("api.main.runtime_requires_production_secrets", return_value=False):
        from api.main import _initialize_database

        assert await _initialize_database() is False


@pytest.mark.asyncio
async def test_production_database_failure_still_fails_startup():
    with patch("api.main.init_pool", new=AsyncMock(side_effect=RuntimeError("database unavailable"))), \
         patch("api.main.runtime_requires_production_secrets", return_value=True):
        from api.main import _initialize_database

        with pytest.raises(RuntimeError, match="database unavailable"):
            await _initialize_database()


@pytest.mark.asyncio
async def test_health_endpoint_returns_degraded_snapshot():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "degraded",
        "readiness_ok": False,
        "feed_fresh": False,
        "checks": {"database": "ok"},
    }

    with patch.dict("os.environ", {"CAREGIST_RELEASE_SHA": "a" * 40}), \
         patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_pipeline_health", new=AsyncMock(return_value=snapshot)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["release"] == {"git_sha": "a" * 40}


@pytest.mark.asyncio
async def test_health_endpoint_does_not_drain_email_queue():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "healthy",
        "readiness_ok": True,
        "feed_fresh": True,
        "checks": {
            "database": "ok",
            "incremental_fresh": True,
            "feed_cycle_fresh": True,
            "email_backlog_healthy": True,
            "email_processing_healthy": True,
            "last_incremental_completed_at": "2026-04-13T09:00:00+00:00",
            "last_feed_cycle_completed_at": "2026-04-13T09:05:00+00:00",
            "latest_new_registration_observed_at": "2026-04-13T09:05:00+00:00",
            "new_registration_events_last_24h": 10,
            "pending_email_count": 0,
            "stuck_processing_email_count": 0,
        },
    }

    drain = AsyncMock(side_effect=RuntimeError("resend down"))
    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_pipeline_health", new=AsyncMock(return_value=snapshot)), \
         patch("api.routers.health.process_email_queue", new=drain, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    drain.assert_not_awaited()


@pytest.mark.asyncio
async def test_crm_health_fails_closed_when_tps_cron_is_stale():
    from api.routers import health

    conn = AsyncMock()
    conn.transaction = lambda: _Transaction()
    conn.fetchrow = AsyncMock(
        return_value={
            "worker_age_seconds": None,
            "worker_status": None,
            "monthly_spend_usd": 0,
            "expired_backlog": 0,
            "retention_failures": 0,
            "tps_enabled_organizations": 1,
            "tps_stale_organizations": 1,
            "tps_failed_organizations": 0,
            "tps_pending_jobs": 25,
            "tps_review_jobs": 2,
        }
    )
    with (
        patch.object(health.settings, "crm_recording_enabled", False),
        patch.object(health.settings, "crm_ai_enabled", False),
        patch.object(health.settings, "crm_tps_automation_enabled", True),
        patch("api.routers.health.set_crm_operations") as metrics,
    ):
        result = await health._crm_operations(conn)

    assert result["tps_ok"] is False
    assert result["ok"] is False
    metrics.assert_called_once_with(
        worker_age_seconds=None,
        monthly_spend_usd=0.0,
        expired_backlog=0,
        retention_failures=0,
        tps_stale_organizations=1,
        tps_failed_organizations=0,
        tps_pending_jobs=25,
        tps_review_jobs=2,
    )


@pytest.mark.asyncio
async def test_security_headers_include_hsts_in_production():
    with patch("api.main._is_local", False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
            response = await client.get("/api/v1/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.asyncio
async def test_security_headers_leave_local_without_hsts():
    with patch("api.main._is_local", True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" not in response.headers
    assert "Content-Security-Policy" not in response.headers


@pytest.mark.asyncio
async def test_readiness_endpoint_returns_503_when_pipeline_not_ready():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "degraded",
        "readiness_ok": False,
        "feed_fresh": True,
        "checks": {
            "database": "ok",
            "incremental_fresh": True,
            "feed_cycle_fresh": True,
            "email_backlog_healthy": True,
            "email_processing_healthy": False,
            "last_incremental_completed_at": "2026-04-13T09:00:00+00:00",
            "last_feed_cycle_completed_at": "2026-04-13T09:05:00+00:00",
            "latest_new_registration_observed_at": "2026-04-13T09:05:00+00:00",
            "new_registration_events_last_24h": 10,
            "pending_email_count": 0,
            "stuck_processing_email_count": 2,
        },
    }

    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_pipeline_health", new=AsyncMock(return_value=snapshot)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/readiness")

    assert response.status_code == 503
    assert response.json()["readiness_ok"] is False


@pytest.mark.asyncio
async def test_freshness_endpoint_returns_503_when_feed_stale():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "stale",
        "source": "https://api.service.cqc.org.uk/public/v1/locations",
        "sourcePublishedAt": "2026-04-01",
        "sourceRetrievedAt": "2026-04-01T09:00:00+00:00",
        "reconciledAt": "2026-04-01T09:05:00+00:00",
        "reason": "latest_successful_retrieval_exceeds_freshness_sla",
        "message": "Freshness cannot currently be confirmed.",
    }

    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_cqc_freshness", new=AsyncMock(return_value=snapshot)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/freshness")

    assert response.status_code == 503
    assert response.json()["status"] == "stale"


@pytest.mark.asyncio
async def test_freshness_endpoint_returns_stable_public_evidence():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "fresh",
        "source": "https://api.service.cqc.org.uk/public/v1/locations",
        "sourcePublishedAt": "2026-08-10",
        "sourceRetrievedAt": "2026-08-10T21:00:00+00:00",
        "reconciledAt": "2026-08-10T21:05:00+00:00",
        "totalSourceLocations": 56_742,
        "checkedLocations": 56_742,
        "successfullyCheckedLocations": 56_742,
        "coveragePercentage": 100.0,
        "successCount": 56_742,
        "failureCount": 0,
        "countsReconciled": True,
        "checksumSha256": "a" * 64,
        "latestAttempt": None,
        "reason": None,
        "message": "CareGist data is current as of 10 August 2026 at 21:00 UTC.",
    }

    with patch.dict("os.environ", {"CAREGIST_RELEASE_SHA": "a" * 40}), \
         patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_cqc_freshness", new=AsyncMock(return_value=snapshot)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.get("/api/v1/health/freshness")
            second = await client.get("/api/v1/health/freshness")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["release"] == {"git_sha": "a" * 40}
    assert "generated_at" not in first.json()


@pytest.mark.asyncio
async def test_freshness_endpoint_query_failure_returns_complete_unknown_contract():
    @asynccontextmanager
    async def mock_get_connection():
        yield AsyncMock()

    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch(
             "api.routers.health.get_cqc_freshness",
             new=AsyncMock(side_effect=RuntimeError("database unavailable")),
         ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/freshness")

    payload = response.json()
    assert response.status_code == 503
    assert payload["status"] == "unknown"
    assert payload["sourceRetrievedAt"] is None
    assert payload["reconciledAt"] is None
    assert payload["countsReconciled"] is False
    assert payload["reason"] == "freshness_evidence_query_failed"


@pytest.mark.asyncio
async def test_liveness_always_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_version_publishes_validated_release_sha():
    with patch.dict("os.environ", {"CAREGIST_RELEASE_SHA": "B" * 40}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {
        "application": "caregist-api",
        "version": "1.0.0",
        "release": {"git_sha": "b" * 40},
    }


@pytest.mark.asyncio
async def test_version_does_not_reflect_invalid_release_value():
    with patch.dict("os.environ", {"CAREGIST_RELEASE_SHA": "not-a-sha<script>"}, clear=False):
        with patch("api.release._SHA_ENV_KEYS", ("CAREGIST_RELEASE_SHA",)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/version")

    assert response.json()["release"] == {"git_sha": "unknown"}


@pytest.mark.asyncio
async def test_readiness_503_when_redis_unreachable():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "healthy",
        "readiness_ok": True,
        "feed_fresh": True,
        "checks": {"database": "ok"},
    }

    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_pipeline_health", new=AsyncMock(return_value=snapshot)), \
         patch("api.routers.health.redis_health", new=AsyncMock(return_value={"configured": True, "ok": False})):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/readiness")

    assert response.status_code == 503
    assert response.json()["readiness_ok"] is False
    assert response.json()["redis"] == {"configured": True, "ok": False}


@pytest.mark.asyncio
async def test_readiness_ok_when_db_and_redis_healthy():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "healthy",
        "readiness_ok": True,
        "feed_fresh": True,
        "checks": {"database": "ok"},
    }

    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_pipeline_health", new=AsyncMock(return_value=snapshot)), \
         patch("api.routers.health.redis_health", new=AsyncMock(return_value={"configured": True, "ok": True})):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/readiness")

    assert response.status_code == 200
    assert response.json()["readiness_ok"] is True
