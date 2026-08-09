from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from api.services.pipeline_health import get_pipeline_health


class HealthConnection:
    def __init__(
        self,
        *,
        now: datetime,
        active_count: int = 56_976,
        source_count: int = 56_976,
        latest_event_age: timedelta = timedelta(hours=1),
        signal_run_age: timedelta = timedelta(minutes=20),
        total_polls: int = 336,
        completed_polls: int = 336,
        measured_events: int = 20,
        p95_seconds: float | None = 1_800,
        stuck: int = 0,
        dead_letter: int = 0,
        tables: set[str] | None = None,
    ):
        self.now = now
        self.active_count = active_count
        self.source_count = source_count
        self.latest_event_age = latest_event_age
        self.signal_run_age = signal_run_age
        self.total_polls = total_polls
        self.completed_polls = completed_polls
        self.measured_events = measured_events
        self.p95_seconds = p95_seconds
        self.stuck = stuck
        self.dead_letter = dead_letter
        self.tables = tables or {
            "pipeline_runs",
            "trusted_event_ledger",
            "source_snapshots",
            "delivery_outbox",
        }

    async def fetchval(self, query: str, table_name: str):
        assert "information_schema.tables" in query
        return table_name in self.tables

    async def fetchrow(self, query: str, *_args):
        if "FROM care_providers" in query:
            return {
                "location_rows": self.active_count + 1,
                "active_location_rows": self.active_count,
                "active_provider_organisations": 37_100,
                "grouped_provider_organisations": 3_200,
                "named_group_labels": 2_900,
            }
        if "WHERE run_type = 'signal_poll'" in query and "LIMIT 1" in query:
            completed = self.now - self.signal_run_age
            return {
                "run_type": "signal_poll",
                "status": "completed",
                "started_at": completed - timedelta(minutes=5),
                "completed_at": completed,
                "error_message": None,
            }
        if "COUNT(*)::int AS total_polls" in query:
            return {
                "total_polls": self.total_polls,
                "completed_polls": self.completed_polls,
            }
        if "run_type IN ('incremental', 'reconciliation')" in query:
            return {
                "source_uri": "https://www.cqc.org.uk/current.csv",
                "source_published_at": self.now.date(),
                "source_retrieved_at": self.now - timedelta(hours=2),
                "source_checksum_sha256": "a" * 64,
                "source_record_count": self.source_count,
                "active_records_before": 56_742,
                "active_records_after": self.active_count,
                "completed_at": self.now - timedelta(hours=1),
            }
        if "MAX(observed_at)" in query:
            return {
                "latest_observed_at": self.now - self.latest_event_age,
                "latest_effective_date": date.today() - self.latest_event_age,
            }
        if "percentile_cont(0.95)" in query:
            return {
                "measured_events": self.measured_events,
                "p95_seconds": self.p95_seconds,
            }
        if "FROM delivery_outbox" in query:
            return {
                "pending": self.stuck,
                "stuck": self.stuck,
                "dead_letter": self.dead_letter,
            }
        raise AssertionError(f"Unexpected health query: {query}")


@pytest.mark.asyncio
async def test_pipeline_health_publishes_independent_readiness_dimensions():
    now = datetime.now(UTC)
    result = await get_pipeline_health(HealthConnection(now=now))

    assert result["freshness_ok"] is True
    assert result["commercialReadiness"]["checkoutReady"] is True
    assert result["source"]["sourcePublishedAt"] == now.date().isoformat()
    assert result["source"]["checksumSha256"] == "a" * 64
    assert result["delivery"] == {
        "healthy": True,
        "pending": 0,
        "stuck": 0,
        "deadLetter": 0,
    }
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
async def test_pipeline_health_fails_commerce_closed_when_counts_differ():
    now = datetime.now(UTC)
    result = await get_pipeline_health(
        HealthConnection(now=now, active_count=56_742, source_count=56_976)
    )

    assert result["freshness_ok"] is False
    assert result["status"] == "degraded"
    assert result["units"]["countsReconciled"] is False
    assert result["commercialReadiness"]["checkoutReady"] is False


@pytest.mark.asyncio
async def test_quiet_event_market_does_not_make_a_healthy_collector_stale():
    now = datetime.now(UTC)
    result = await get_pipeline_health(
        HealthConnection(now=now, latest_event_age=timedelta(days=9))
    )

    assert result["feed_fresh"] is True
    assert result["eventActivity"]["informational"] is True
    assert result["readiness_ok"] is True
    assert result["freshness_ok"] is True
    assert result["status"] == "healthy"
