from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_internal_pipeline_endpoint_returns_snapshot_and_recent_runs():
    conn = AsyncMock()
    conn.fetch.return_value = [
        {
            "run_type": "feed_cycle",
            "status": "completed",
            "started_at": None,
            "completed_at": None,
            "records_added": 5,
            "records_updated": 2,
            "error_message": None,
        }
    ]
    conn.fetchrow.side_effect = [
        {
            "total_new_registration_events": 123,
            "new_registration_events_last_7d": 21,
            "latest_observed_at": None,
            "latest_effective_date": None,
        }
    ]

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

    with patch("api.routers.internal.get_connection", mock_get_connection), \
         patch("api.routers.internal.get_pipeline_health", new=AsyncMock(return_value=snapshot)), \
         patch("api.routers.internal.validate_internal_token", new=AsyncMock(return_value={"scope": "internal"})):
        app.dependency_overrides = {}
        from api.middleware.internal_auth import validate_internal_token
        app.dependency_overrides[validate_internal_token] = lambda: {"scope": "internal"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/internal/pipeline", headers={"X-Internal-Token": "test"})
        app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["ledger"]["totalNewRegistrationEvents"] == 123
    assert payload["recentRuns"][0]["runType"] == "feed_cycle"
