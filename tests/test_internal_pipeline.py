from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.routers.internal import (
    InternalRemediationRequest,
    _remediation_inflight_fingerprints,
    _remediation_locks,
    _remediation_request_times,
    internal_remediate,
)


@pytest.fixture(autouse=True)
def clear_remediation_guards():
    _remediation_request_times.clear()
    _remediation_inflight_fingerprints.clear()
    _remediation_locks.clear()
    yield
    _remediation_request_times.clear()
    _remediation_inflight_fingerprints.clear()
    _remediation_locks.clear()


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


@pytest.mark.asyncio
async def test_internal_remediate_legitimate_request_queues_task():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[None, {"id": "task-1"}])
    background_tasks = MagicMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.internal.get_connection", mock_get_connection):
        response = await internal_remediate(
            InternalRemediationRequest(
                action="caregist:refresh_profile_projection",
                tenantId="tenant-1",
                payload={"providerId": "1-123"},
            ),
            background_tasks,
            _auth={"scope": "internal"},
        )

    assert response == {"taskId": "task-1", "status": "pending"}
    background_tasks.add_task.assert_called_once()
    audit_args = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_args[1] == "internal.remediation.queue"
    assert "1-123" not in repr(audit_args)


@pytest.mark.asyncio
async def test_internal_remediate_duplicate_payload_reuses_existing_task():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": "task-1"},
            {"id": "task-1", "status": "pending"},
        ]
    )
    first_background_tasks = MagicMock()
    second_background_tasks = MagicMock()
    request = InternalRemediationRequest(
        action="caregist:refresh_profile_projection",
        tenantId="tenant-1",
        payload={"providerId": "1-123"},
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.internal.get_connection", mock_get_connection):
        first = await internal_remediate(request, first_background_tasks, _auth={"scope": "internal"})
        _remediation_inflight_fingerprints.clear()
        second = await internal_remediate(request, second_background_tasks, _auth={"scope": "internal"})

    assert first == {"taskId": "task-1", "status": "pending"}
    assert second == {"taskId": "task-1", "status": "pending"}
    first_background_tasks.add_task.assert_called_once()
    second_background_tasks.add_task.assert_not_called()


@pytest.mark.asyncio
async def test_internal_remediate_repeated_rapid_requests_are_limited(monkeypatch):
    monkeypatch.setattr("api.routers.internal.REMEDIATION_RATE_LIMIT", 2)
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[None, {"id": "task-1"}, None, {"id": "task-2"}])

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.internal.get_connection", mock_get_connection):
        for idx in range(2):
            await internal_remediate(
                InternalRemediationRequest(
                    action="caregist:refresh_profile_projection",
                    tenantId="tenant-1",
                    payload={"providerId": f"1-{idx}"},
                ),
                MagicMock(),
                _auth={"scope": "internal"},
            )

        with pytest.raises(HTTPException) as exc:
            await internal_remediate(
                InternalRemediationRequest(
                    action="caregist:refresh_profile_projection",
                    tenantId="tenant-1",
                    payload={"providerId": "1-999"},
                ),
                MagicMock(),
                _auth={"scope": "internal"},
            )

    assert exc.value.status_code == 429
