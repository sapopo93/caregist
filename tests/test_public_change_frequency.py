from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware.ip_rate_limit import check_public_rate_limit


@pytest.mark.asyncio
async def test_public_change_frequency_reports_substantive_events_and_collection_coverage():
    conn = AsyncMock()
    conn.fetch.side_effect = [
        [
            {
                "day": date(2026, 8, 8),
                "events": 3,
                "new_registrations": 1,
                "rating_changes": 2,
                "status_changes": 0,
                "ownership_changes": 0,
                "group_movements": 0,
            },
            {
                "day": date(2026, 8, 9),
                "events": 0,
                "new_registrations": 0,
                "rating_changes": 0,
                "status_changes": 0,
                "ownership_changes": 0,
                "group_movements": 0,
            },
            {
                "day": date(2026, 8, 10),
                "events": 1,
                "new_registrations": 0,
                "rating_changes": 0,
                "status_changes": 1,
                "ownership_changes": 0,
                "group_movements": 0,
            },
        ],
        [
            {
                "day": date(2026, 8, 8),
                "run_type": "signal_poll",
                "status": "completed",
                "runs": 2,
                "latest_run_at": datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
            },
            {
                "day": date(2026, 8, 10),
                "run_type": "signal_poll",
                "status": "completed",
                "runs": 2,
                "latest_run_at": datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
            },
            {
                "day": date(2026, 8, 9),
                "run_type": "signal_poll",
                "status": "failed",
                "runs": 1,
                "latest_run_at": datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
            },
        ],
    ]

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.public_tools.get_connection", mock_get_connection):
        app.dependency_overrides[check_public_rate_limit] = lambda: None
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/tools/cqc-change-frequency?days=3")
        finally:
            app.dependency_overrides.pop(check_public_rate_limit, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["period"] == {"from": "2026-08-08", "to": "2026-08-10", "days": 3}
    assert payload["summary"]["eventCount"] == 4
    assert payload["summary"]["activeChangeDays"] == 2
    assert payload["summary"]["quietDays"] == 1
    assert payload["summary"]["longestQuietStreakDays"] == 1
    assert payload["summary"]["changesEveryDay"] is False
    assert payload["summary"]["changesAtLeastEveryThreeDays"] is True
    assert payload["summary"]["changesAtLeastWeekly"] is True
    assert payload["byEventType"] == {
        "newRegistration": 1,
        "ratingChanged": 2,
        "statusChanged": 1,
        "ownershipChanged": 0,
        "groupMovement": 0,
    }
    assert payload["collectionCoverage"]["daysWithSuccessfulCollection"] == 2
    assert payload["collectionCoverage"]["coverageRatio"] == pytest.approx(0.66667)
    assert payload["collectionCoverage"]["interpretationReliable"] is False
    assert payload["collectionCoverage"]["completedRuns"] == 4
    assert payload["collectionCoverage"]["failedRuns"] == 1
    assert len(payload["daily"]) == 3

    daily_sql, daily_days = conn.fetch.await_args_list[0].args
    coverage_sql, coverage_days = conn.fetch.await_args_list[1].args
    assert daily_days == coverage_days == 3
    assert "trusted_event_ledger" in daily_sql
    assert "care_providers" not in daily_sql
    assert "AT TIME ZONE 'UTC'" in daily_sql
    assert "signal_poll" in coverage_sql
    assert "reconciliation" in coverage_sql
    assert "AT TIME ZONE 'UTC'" in coverage_sql


@pytest.mark.asyncio
async def test_public_change_frequency_rejects_an_unbounded_window():
    app.dependency_overrides[check_public_rate_limit] = lambda: None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/tools/cqc-change-frequency?days=366")
    finally:
        app.dependency_overrides.pop(check_public_rate_limit, None)

    assert response.status_code == 422