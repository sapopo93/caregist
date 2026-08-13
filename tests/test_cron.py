"""Vercel Cron endpoint authentication and execution tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_cron_email_queue_requires_bearer_secret():
    with patch("api.routers.cron.settings.cron_secret", "cron-test-secret"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/cron/email-queue")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cron_email_queue_drains_pending_delivery():
    drain = AsyncMock(return_value=4)
    with (
        patch("api.routers.cron.settings.cron_secret", "cron-test-secret"),
        patch("api.routers.cron.process_email_queue", new=drain),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/cron/email-queue",
                headers={"Authorization": "Bearer cron-test-secret"},
            )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "sent": 4}
    drain.assert_awaited_once_with(batch_size=50)


@pytest.mark.asyncio
async def test_cron_feed_cycle_runs_registration_webhooks_and_digests():
    result = {
        "inserted_events": 3,
        "webhook_deliveries": 2,
        "digests_queued": 1,
        "digests_skipped": 0,
        "skipped": 0,
    }
    run_cycle = AsyncMock(return_value=result)
    with (
        patch("api.routers.cron.settings.cron_secret", "cron-test-secret"),
        patch("api.routers.cron.settings.database_url", "postgresql://caregist"),
        patch("api.routers.cron.run_feed_cycle", new=run_cycle),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/cron/feed-cycle",
                headers={"Authorization": "Bearer cron-test-secret"},
            )

    assert response.status_code == 200
    assert response.json() == {"ok": True, **result}
    run_cycle.assert_awaited_once_with("postgresql://caregist", skip_digests=False)


@pytest.mark.asyncio
async def test_cron_crm_maintenance_runs_bounded_workers():
    call_order: list[str] = []
    recordings = AsyncMock(return_value={"processed": 1, "failed": 0})
    source_cleanup = AsyncMock(return_value={"deleted": 1, "failed": 0})
    retention = AsyncMock(return_value={"deleted": 2, "failed": 0})
    campaigns = AsyncMock(return_value=3)
    recordings.side_effect = lambda **_kwargs: call_order.append("recordings") or {"processed": 1, "failed": 0}
    source_cleanup.side_effect = lambda **_kwargs: call_order.append("twilio_sources") or {"deleted": 1, "failed": 0}
    retention.side_effect = lambda **_kwargs: call_order.append("retention") or {"deleted": 2, "failed": 0}
    campaigns.side_effect = lambda: call_order.append("campaigns") or 3
    with (
        patch("api.routers.cron.settings.cron_secret", "cron-test-secret"),
        patch("api.routers.cron.process_recording_jobs", new=recordings),
        patch("api.routers.cron.cleanup_twilio_sources", new=source_cleanup),
        patch("api.routers.cron.purge_expired_recordings", new=retention),
        patch("api.routers.cron.finalize_campaigns", new=campaigns),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/cron/crm-maintenance",
                headers={"Authorization": "Bearer cron-test-secret"},
            )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "recordings": {"processed": 1, "failed": 0},
        "twilio_sources": {"deleted": 1, "failed": 0},
        "retention": {"deleted": 2, "failed": 0},
        "campaigns_completed": 3,
    }
    recordings.assert_awaited_once_with(limit=1)
    source_cleanup.assert_awaited_once_with(limit=50)
    retention.assert_awaited_once_with(limit=50)
    assert call_order == ["recordings", "twilio_sources", "retention", "campaigns"]
