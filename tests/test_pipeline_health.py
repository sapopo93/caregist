from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from api.services.pipeline_health import get_pipeline_health


@pytest.mark.asyncio
async def test_pipeline_health_publishes_source_watermark_and_explicit_units():
    now = datetime.now(UTC)
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[True, True])
    conn.fetchrow = AsyncMock(
        side_effect=[
            {
                "location_rows": 56_977,
                "active_location_rows": 56_976,
                "active_provider_organisations": 37_100,
                "grouped_provider_organisations": 3_200,
                "named_group_labels": 2_900,
            },
            {
                "run_type": "incremental",
                "status": "completed",
                "started_at": now - timedelta(hours=2),
                "completed_at": now - timedelta(hours=1),
                "error_message": None,
            },
            {
                "source_uri": "https://www.cqc.org.uk/current.csv",
                "source_published_at": now.date(),
                "source_retrieved_at": now - timedelta(hours=2),
                "source_checksum_sha256": "a" * 64,
                "source_record_count": 56_976,
                "active_records_before": 56_742,
                "active_records_after": 56_976,
                "completed_at": now - timedelta(hours=1),
            },
            {
                "latest_observed_at": now - timedelta(hours=1),
                "latest_effective_date": date.today(),
            },
        ]
    )

    result = await get_pipeline_health(conn)

    assert result["freshness_ok"] is True
    assert result["source"]["sourcePublishedAt"] == now.date().isoformat()
    assert result["source"]["checksumSha256"] == "a" * 64
    assert result["units"] == {
        "locationRows": 56_977,
        "activeLocationRows": 56_976,
        "activeProviderOrganisations": 37_100,
        "groupedProviderOrganisations": 3_200,
        "namedGroupLabels": 2_900,
        "sourceActiveLocationRows": 56_976,
        "countsReconciled": True,
    }


@pytest.mark.asyncio
async def test_pipeline_health_fails_closed_when_source_and_database_counts_differ():
    now = datetime.now(UTC)
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[True, True])
    conn.fetchrow = AsyncMock(
        side_effect=[
            {
                "location_rows": 56_743,
                "active_location_rows": 56_742,
                "active_provider_organisations": 36_944,
                "grouped_provider_organisations": 3_000,
                "named_group_labels": 2_800,
            },
            {
                "run_type": "incremental",
                "status": "completed",
                "started_at": now - timedelta(hours=2),
                "completed_at": now - timedelta(hours=1),
                "error_message": None,
            },
            {
                "source_uri": "https://www.cqc.org.uk/current.csv",
                "source_published_at": now.date(),
                "source_retrieved_at": now - timedelta(hours=2),
                "source_checksum_sha256": "b" * 64,
                "source_record_count": 56_976,
                "active_records_before": 56_742,
                "active_records_after": 56_742,
                "completed_at": now - timedelta(hours=1),
            },
            {
                "latest_observed_at": now - timedelta(hours=1),
                "latest_effective_date": date.today(),
            },
        ]
    )

    result = await get_pipeline_health(conn)

    assert result["freshness_ok"] is False
    assert result["status"] == "degraded"
    assert result["units"]["countsReconciled"] is False


@pytest.mark.asyncio
async def test_pipeline_health_readiness_stays_ok_when_only_feed_is_stale():
    """readiness_ok gates traffic-serving (DB tables reachable); feed staleness must NOT
    fail it, or an upstream CQC publishing lag would take fully-working routes (search,
    groups, pricing) offline along with it. Staleness is surfaced via freshness_ok /
    the separate /freshness endpoint for alerting, not as a traffic gate."""
    now = datetime.now(UTC)
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[True, True])
    conn.fetchrow = AsyncMock(
        side_effect=[
            {
                "location_rows": 56_977,
                "active_location_rows": 56_976,
                "active_provider_organisations": 37_100,
                "grouped_provider_organisations": 3_200,
                "named_group_labels": 2_900,
            },
            {
                "run_type": "incremental",
                "status": "completed",
                "started_at": now - timedelta(hours=2),
                "completed_at": now - timedelta(hours=1),
                "error_message": None,
            },
            {
                "source_uri": "https://www.cqc.org.uk/current.csv",
                "source_published_at": now.date(),
                "source_retrieved_at": now - timedelta(hours=2),
                "source_checksum_sha256": "a" * 64,
                "source_record_count": 56_976,
                "active_records_before": 56_742,
                "active_records_after": 56_976,
                "completed_at": now - timedelta(hours=1),
            },
            {
                # Newest feed event is 9 days old — outside the 168h/7-day SLA.
                "latest_observed_at": now - timedelta(days=9),
                "latest_effective_date": date.today() - timedelta(days=9),
            },
        ]
    )

    result = await get_pipeline_health(conn)

    assert result["feed_fresh"] is False
    assert result["readiness_ok"] is True
    assert result["freshness_ok"] is False
    assert result["status"] == "degraded"
