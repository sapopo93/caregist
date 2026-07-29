from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware.internal_auth import validate_internal_token
from api.routers.internal import (
    InternalRemediationRequest,
    _remediation_inflight_fingerprints,
    _remediation_locks,
    _remediation_request_times,
    _run_smoke_verification,
    internal_remediate,
)
from tools.check_new_registration_pipeline import _build_alert_body, _derive_alert_keys


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
async def test_internal_pipeline_endpoint_is_available_under_api_v1_alias():
    conn = AsyncMock()
    conn.fetch.return_value = []
    conn.fetchrow.side_effect = [
        {
            "total_new_registration_events": 0,
            "new_registration_events_last_7d": 0,
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
        "checks": {},
    }

    with patch("api.routers.internal.get_connection", mock_get_connection), \
         patch("api.routers.internal.get_pipeline_health", new=AsyncMock(return_value=snapshot)):
        app.dependency_overrides = {}
        app.dependency_overrides[validate_internal_token] = lambda: {"scope": "internal", "actor": "hermes"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/internal/pipeline", headers={"X-Internal-Token": "test"})
        app.dependency_overrides = {}

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_smoke_verification_consumes_real_pipeline_check_list_shape():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"connected": 1},
            {"active_providers": 125, "pending_emails": 2},
        ]
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    snapshot = {
        "status": "degraded",
        "readiness_ok": True,
        "feed_fresh": False,
        "checks": [
            {"name": "pipeline_runs_table", "ok": True, "details": {"present": True}},
            {
                "name": "new_registration_feed_freshness",
                "ok": False,
                "details": {"latestObservedAt": None, "slaHours": 168},
            },
        ],
    }

    with patch("api.routers.internal.get_connection", mock_get_connection), patch(
        "api.routers.internal.get_pipeline_health",
        new=AsyncMock(return_value=snapshot),
    ):
        result = await _run_smoke_verification({})

    assert result["ok"] is False
    assert result["failedChecks"] == ["new_registration_feed_freshness"]
    assert result["activeProviders"] == 125
    assert result["pendingEmails"] == 2


def test_pipeline_alert_helpers_consume_real_pipeline_check_list_shape():
    snapshot = {
        "status": "degraded",
        "readiness_ok": True,
        "feed_fresh": False,
        "checks": [
            {"name": "recent_pipeline_run", "ok": True, "details": {"latestStatus": "completed"}},
            {
                "name": "new_registration_feed_freshness",
                "ok": False,
                "details": {"latestObservedAt": "2026-07-20T09:00:00+00:00", "slaHours": 168},
            },
        ],
    }

    assert _derive_alert_keys(snapshot) == ["new_registration_feed_freshness"]
    body = _build_alert_body(snapshot)
    assert "new_registration_feed_freshness: FAILED" in body
    assert "latestObservedAt=2026-07-20T09:00:00+00:00" in body


@pytest.mark.asyncio
async def test_hermes_internal_token_identifies_hermes_actor(monkeypatch):
    monkeypatch.setattr("api.middleware.internal_auth.settings.hermes_internal_token", "hermes-token", raising=False)

    auth = await validate_internal_token("hermes-token")

    assert auth == {"scope": "internal", "actor": "hermes"}


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
            x_idempotency_key="support-queue-1",
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
        first = await internal_remediate(request, first_background_tasks, x_idempotency_key="dupe-1", _auth={"scope": "internal"})
        _remediation_inflight_fingerprints.clear()
        second = await internal_remediate(request, second_background_tasks, x_idempotency_key="dupe-1", _auth={"scope": "internal"})

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
                x_idempotency_key=f"rate-{idx}",
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
                x_idempotency_key="rate-over-limit",
                _auth={"scope": "internal"},
            )

    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_internal_remediate_requires_idempotency_key_for_mutations():
    with pytest.raises(HTTPException) as exc:
        await internal_remediate(
            InternalRemediationRequest(
                action="caregist:resume_failed_enquiry_delivery",
                tenantId="tenant-1",
                payload={"batchSize": 1},
            ),
            MagicMock(),
            _auth={"scope": "internal", "actor": "hermes"},
        )

    assert exc.value.status_code == 400
    assert "X-Idempotency-Key" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_hermes_remediate_audits_actor_as_hermes_and_queues_allowed_action():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[None, {"id": "task-hermes-1"}])
    background_tasks = MagicMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.internal.get_connection", mock_get_connection):
        response = await internal_remediate(
            InternalRemediationRequest(
                action="caregist:resume_failed_enquiry_delivery",
                tenantId="tenant-1",
                payload={"batchSize": 1},
            ),
            background_tasks,
            x_idempotency_key="hermes-email-flush-1",
            _auth={"scope": "internal", "actor": "hermes"},
        )

    assert response == {"taskId": "task-hermes-1", "status": "pending"}
    audit_args = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_args[3] == "internal"
    assert audit_args[7] == "hermes"
    task_args = background_tasks.add_task.call_args.args
    assert task_args[0].__name__ == "_run_internal_task"
    assert task_args[5] == {"type": "internal", "name": "hermes"}


@pytest.mark.asyncio
async def test_hermes_remediate_rejects_actions_outside_hermes_allowlist():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.internal.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await internal_remediate(
                InternalRemediationRequest(
                    action="caregist:rebuild_listing_index",
                    tenantId="tenant-1",
                    payload={},
                ),
                MagicMock(),
                x_idempotency_key="hermes-not-allowed-1",
                _auth={"scope": "internal", "actor": "hermes"},
            )

    assert exc.value.status_code == 403
    conn.fetchrow.assert_not_called()
