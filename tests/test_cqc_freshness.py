from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from contextlib import asynccontextmanager

import pytest

from api.services.cqc_freshness import build_cqc_freshness, get_cqc_freshness


NOW = datetime(2026, 8, 10, 22, 0, tzinfo=UTC)


def _run(**overrides):
    row = {
        "id": 41,
        "status": "completed",
        "started_at": NOW - timedelta(hours=2),
        "completed_at": NOW - timedelta(minutes=55),
        "source_uri": "https://api.service.cqc.org.uk/public/v1/locations",
        "source_published_at": date(2026, 8, 10),
        "source_retrieved_at": NOW - timedelta(hours=1),
        "source_checksum_sha256": "a" * 64,
        "source_total_count": 56_742,
        "checked_count": 56_742,
        "success_count": 56_742,
        "failure_count": 0,
        "reconciled_at": NOW - timedelta(minutes=55),
        "counts_reconciled": True,
    }
    row.update(overrides)
    return row


def test_fresh_result_uses_only_persisted_authoritative_evidence():
    row = _run()

    result = build_cqc_freshness(row, row, now=NOW)

    assert result == {
        "status": "fresh",
        "source": "https://api.service.cqc.org.uk/public/v1/locations",
        "sourcePublishedAt": "2026-08-10",
        "sourceRetrievedAt": "2026-08-10T21:00:00+00:00",
        "reconciledAt": "2026-08-10T21:05:00+00:00",
        "totalSourceLocations": 56_742,
        "checkedLocations": 56_742,
        "successfullyCheckedLocations": 56_742,
        "coveragePercentage": 100.0,
        "successCount": 56_742,
        "failureCount": 0,
        "countsReconciled": True,
        "checksumSha256": "a" * 64,
        "latestAttempt": {
            "status": "completed",
            "startedAt": "2026-08-10T20:00:00+00:00",
            "completedAt": "2026-08-10T21:05:00+00:00",
            "totalSourceLocations": 56_742,
            "checkedLocations": 56_742,
            "coveragePercentage": 100.0,
            "successCount": 56_742,
            "failureCount": 0,
            "countsReconciled": True,
        },
        "reason": None,
        "message": (
            "CareGist data is current as of 10 August 2026 at 21:00 UTC. "
            "The last successful CQC retrieval checked 56,742 of 56,742 active locations, "
            "reconciled successfully, and completed without collection errors."
        ),
    }


def test_newer_failed_attempt_fails_closed_without_leaking_error_details():
    watermark = _run()
    failed = _run(
        id=42,
        status="failed",
        started_at=NOW - timedelta(minutes=30),
        completed_at=NOW - timedelta(minutes=20),
        source_total_count=56_900,
        checked_count=120,
        success_count=119,
        failure_count=1,
        counts_reconciled=False,
        reconciled_at=None,
        source_checksum_sha256=None,
        error_message="secret=must-not-appear",
    )

    result = build_cqc_freshness(watermark, failed, now=NOW)

    assert result["status"] == "partial"
    assert result["reason"] == "latest_authoritative_attempt_incomplete"
    assert result["sourceRetrievedAt"] == "2026-08-10T21:00:00+00:00"
    assert result["latestAttempt"]["status"] == "failed"
    assert result["latestAttempt"]["coveragePercentage"] == pytest.approx(0.2109)
    assert "secret" not in str(result)


def test_partial_attempt_without_a_watermark_does_not_claim_retrieval_time():
    partial = _run(
        status="running",
        completed_at=None,
        checked_count=400,
        success_count=400,
        failure_count=0,
        reconciled_at=None,
        counts_reconciled=False,
    )

    result = build_cqc_freshness(None, partial, now=NOW)

    assert result["status"] == "partial"
    assert result["sourceRetrievedAt"] is None
    assert result["reconciledAt"] is None
    assert result["coveragePercentage"] is None
    assert result["latestAttempt"]["coveragePercentage"] == pytest.approx(0.70495)


def test_stale_result_is_based_on_successful_retrieval_not_publication_date():
    stale = _run(
        source_published_at=NOW,
        source_retrieved_at=NOW - timedelta(days=8, seconds=1),
    )

    result = build_cqc_freshness(stale, stale, now=NOW)

    assert result["status"] == "stale"
    assert result["reason"] == "latest_successful_retrieval_exceeds_freshness_sla"
    assert result["sourcePublishedAt"] == "2026-08-10T22:00:00+00:00"


def test_missing_and_incomplete_evidence_are_unknown():
    missing = build_cqc_freshness(None, None, now=NOW)
    incomplete = build_cqc_freshness(
        _run(source_checksum_sha256=None),
        _run(source_checksum_sha256=None),
        now=NOW,
    )

    assert missing["status"] == "unknown"
    assert missing["reason"] == "no_completed_reconciled_authoritative_retrieval"
    assert incomplete["status"] == "unknown"
    assert incomplete["reason"] == "completed_retrieval_evidence_incomplete"


class FreshnessConnection:
    def __init__(self, *, schema_ready=True, watermark=None, attempt=None):
        self.schema_ready = schema_ready
        self.watermark = watermark
        self.attempt = attempt
        self.queries = []

    @asynccontextmanager
    async def transaction(self, **options):
        assert options == {"isolation": "repeatable_read", "readonly": True}
        yield

    async def fetchval(self, query, *args):
        self.queries.append(query)
        assert args[0] == "pipeline_runs"
        return self.schema_ready

    async def fetchrow(self, query):
        self.queries.append(query)
        if "counts_reconciled = TRUE" in query:
            return self.watermark
        return self.attempt


@pytest.mark.asyncio
async def test_query_selects_only_completed_reconciled_authoritative_watermark():
    row = _run()
    conn = FreshnessConnection(watermark=row, attempt=row)

    result = await get_cqc_freshness(conn, now=NOW)

    assert result["status"] == "fresh"
    assert "run_type = 'reconciliation'" in conn.queries[1]
    assert "status = 'completed'" in conn.queries[1]
    assert "counts_reconciled = TRUE" in conn.queries[1]
    assert "reconciled_at IS NOT NULL" in conn.queries[1]
    assert "source_retrieved_at IS NOT NULL" in conn.queries[1]
    assert "care_providers" not in " ".join(conn.queries)


@pytest.mark.asyncio
async def test_pre_migration_schema_returns_unknown_without_querying_runs():
    conn = FreshnessConnection(schema_ready=False)

    result = await get_cqc_freshness(conn, now=NOW)

    assert result["status"] == "unknown"
    assert len(conn.queries) == 1


def test_invalid_coverage_and_naive_authoritative_times_fail_closed():
    invalid_coverage = build_cqc_freshness(
        _run(source_total_count=10, checked_count=11, success_count=11),
        _run(source_total_count=10, checked_count=11, success_count=11),
        now=NOW,
    )
    naive_time = build_cqc_freshness(
        _run(source_retrieved_at=datetime(2026, 8, 10, 21, 0)),
        _run(source_retrieved_at=datetime(2026, 8, 10, 21, 0)),
        now=NOW,
    )

    assert invalid_coverage["status"] == "unknown"
    assert invalid_coverage["coveragePercentage"] is None
    assert naive_time["status"] == "unknown"
