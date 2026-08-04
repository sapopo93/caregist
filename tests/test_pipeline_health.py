from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from api.services.pipeline_health import get_pipeline_health


def _connection(
    *,
    active_locations: int,
    source_locations: int,
    latest_observed_at: datetime | None = None,
    run_status: str = "completed",
    run_age: timedelta = timedelta(0),
) -> AsyncMock:
    now = datetime.now(UTC)
    run_time = now - run_age
    conn = AsyncMock()
    conn.fetchval.side_effect = [True, True]
    conn.fetchrow.side_effect = [
        {
            "location_rows": active_locations + 1,
            "active_location_rows": active_locations,
            "active_provider_organisations": active_locations,
            "grouped_provider_organisations": 0,
            "named_group_labels": 0,
        },
        {
            "run_type": "reconciliation",
            "status": run_status,
            "started_at": run_time,
            "completed_at": run_time,
            "error_message": None if run_status == "completed" else "pipeline failed",
        },
        {
            "run_type": "reconciliation",
            "source_uri": "https://www.cqc.org.uk/current.csv",
            "source_published_at": date.today(),
            "source_retrieved_at": now,
            "source_checksum_sha256": "a" * 64,
            "source_record_count": source_locations,
            "active_records_before": active_locations + 1,
            "active_records_after": source_locations,
            "completed_at": now,
        },
        {
            "latest_observed_at": latest_observed_at,
            "latest_effective_date": date.today() if latest_observed_at else None,
        },
    ]
    return conn


@pytest.mark.asyncio
async def test_reconciliation_run_is_a_valid_freshness_source():
    snapshot = await get_pipeline_health(
        _connection(
            active_locations=3,
            source_locations=3,
            latest_observed_at=datetime.now(UTC),
        )
    )

    assert snapshot["status"] == "healthy"
    assert snapshot["freshness_ok"] is True
    assert snapshot["source"]["sourceRunType"] == "reconciliation"
    assert snapshot["source"]["countsReconciled"] is True
    assert snapshot["units"]["activeLocationRows"] == 3


@pytest.mark.asyncio
async def test_quiet_feed_without_a_recent_event_is_not_falsely_stale():
    snapshot = await get_pipeline_health(
        _connection(active_locations=3, source_locations=3, latest_observed_at=None)
    )

    assert snapshot["status"] == "healthy"
    assert snapshot["freshness_ok"] is True
    assert snapshot["feed_fresh"] is True
    feed_check = next(
        check
        for check in snapshot["checks"]
        if check["name"] == "new_registration_feed_processing"
    )
    assert feed_check["ok"] is True
    assert feed_check["details"]["latestObservedAt"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("run_status", "run_age"),
    [("failed", timedelta(0)), ("completed", timedelta(days=2))],
)
async def test_quiet_feed_still_fails_closed_for_failed_or_old_processing(
    run_status: str, run_age: timedelta
):
    snapshot = await get_pipeline_health(
        _connection(
            active_locations=3,
            source_locations=3,
            latest_observed_at=None,
            run_status=run_status,
            run_age=run_age,
        )
    )

    assert snapshot["status"] == "degraded"
    assert snapshot["freshness_ok"] is False
    assert snapshot["feed_fresh"] is False


@pytest.mark.asyncio
async def test_source_count_mismatch_fails_closed_even_when_run_is_recent():
    snapshot = await get_pipeline_health(_connection(active_locations=2, source_locations=3))

    assert snapshot["status"] == "degraded"
    assert snapshot["freshness_ok"] is False
    assert snapshot["source_fresh"] is True
    assert snapshot["source"]["countsReconciled"] is False
