from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


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
        "checks": {
            "database": "ok",
            "incremental_fresh": False,
            "feed_cycle_fresh": False,
            "email_backlog_healthy": True,
            "email_processing_healthy": True,
            "last_incremental_completed_at": None,
            "last_feed_cycle_completed_at": None,
            "latest_new_registration_observed_at": None,
            "new_registration_events_last_24h": 0,
            "pending_email_count": 0,
            "stuck_processing_email_count": 0,
        },
    }

    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_pipeline_health", new=AsyncMock(return_value=snapshot)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


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
        "status": "degraded",
        "readiness_ok": False,
        "feed_fresh": False,
        "checks": {
            "database": "ok",
            "incremental_fresh": False,
            "feed_cycle_fresh": False,
            "email_backlog_healthy": True,
            "email_processing_healthy": True,
            "last_incremental_completed_at": None,
            "last_feed_cycle_completed_at": None,
            "latest_new_registration_observed_at": None,
            "new_registration_events_last_24h": 0,
            "pending_email_count": 0,
            "stuck_processing_email_count": 0,
        },
    }

    with patch("api.routers.health.get_connection", mock_get_connection), \
         patch("api.routers.health.get_pipeline_health", new=AsyncMock(return_value=snapshot)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/freshness")

    assert response.status_code == 503
    assert response.json()["status"] == "stale"
