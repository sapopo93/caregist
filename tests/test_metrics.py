"""Tests for the Prometheus metrics endpoint and middleware (F-47)."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api import metrics
from api.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_renders_prometheus_text():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"status": "pending", "n": 3}, {"status": "failed", "n": 1}])

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.health.get_connection", mock_get_connection):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/metrics",
                headers={"X-Internal-Token": "test-internal-token-for-pytest"},
            )

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    if metrics._ENABLED:
        # The pending-email gauge was refreshed from the DB rows.
        assert "caregist_pending_emails" in response.text


@pytest.mark.asyncio
async def test_request_latency_is_recorded():
    if not metrics._ENABLED:
        pytest.skip("prometheus_client not installed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/v1/health/liveness")
        response = await client.get(
            "/metrics",
            headers={"X-Internal-Token": "test-internal-token-for-pytest"},
        )

    # The liveness route shows up in the request histogram with its template label.
    assert "caregist_request_duration_seconds" in response.text
    assert "/api/v1/health/liveness" in response.text


@pytest.mark.asyncio
async def test_metrics_middleware_records_context_tier():
    if not metrics._ENABLED:
        pytest.skip("prometheus_client not installed")

    async def tiered_app(scope, receive, send):
        metrics.set_request_tier("free")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    client = AsyncClient(
        transport=ASGITransport(app=metrics.MetricsMiddleware(tiered_app)),
        base_url="http://test",
    )
    async with client:
        await client.get("/tiered")

    body, _ = metrics.render_latest()
    assert 'tier="free"' in body.decode()


@pytest.mark.asyncio
async def test_metrics_endpoint_requires_internal_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 401


def test_observe_webhook_delivery_does_not_raise():
    # Safe to call regardless of whether prometheus_client is installed.
    metrics.observe_webhook_delivery(True)
    metrics.observe_webhook_delivery(False)
