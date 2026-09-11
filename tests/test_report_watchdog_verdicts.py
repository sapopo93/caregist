"""Monitor health and source freshness must never collapse into one verdict."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.report_watchdog_verdicts import (
    FRESH,
    MONITOR_FAILED,
    MONITOR_OK,
    STALE,
    UNKNOWN,
    build_report,
    load_snapshot,
)


def _write(tmp_path, payload):
    path = tmp_path / "snapshot.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return path


def test_healthy_monitor_with_stale_source_is_not_reported_fresh(tmp_path):
    """The core property: a monitor that ran fine does not make data fresh."""
    path = _write(tmp_path, {"status": "degraded", "readiness_ok": True, "source_fresh": False})
    report = build_report("failure", load_snapshot(path))

    assert report["monitor_execution"]["verdict"] == MONITOR_OK
    assert report["source_data_freshness"]["verdict"] == STALE


def test_fresh_source_is_reported_fresh(tmp_path):
    path = _write(tmp_path, {"status": "healthy", "readiness_ok": True, "source_fresh": True})
    report = build_report("success", load_snapshot(path))

    assert report["monitor_execution"]["verdict"] == MONITOR_OK
    assert report["source_data_freshness"]["verdict"] == FRESH


def test_crashed_monitor_reports_unknown_freshness_not_fresh(tmp_path):
    report = build_report("failure", load_snapshot(tmp_path / "missing.json"))

    assert report["monitor_execution"]["verdict"] == MONITOR_FAILED
    assert report["source_data_freshness"]["verdict"] == UNKNOWN
    assert report["source_data_freshness"]["verdict"] != FRESH


@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_unparseable_snapshot_fails_closed(tmp_path, payload):
    path = _write(tmp_path, payload)
    report = build_report("success", load_snapshot(path))

    assert report["monitor_execution"]["verdict"] == MONITOR_FAILED
    assert report["source_data_freshness"]["verdict"] == UNKNOWN


def test_snapshot_without_source_fresh_field_is_unknown(tmp_path):
    path = _write(tmp_path, {"status": "healthy", "readiness_ok": True})
    report = build_report("success", load_snapshot(path))

    assert report["monitor_execution"]["verdict"] == MONITOR_OK
    assert report["source_data_freshness"]["verdict"] == UNKNOWN


class _SnapshotContract:
    """Locks the contract between the monitor's stdout and the reporter.

    The workflow tees the monitor's stdout into /tmp/snapshot.json and the
    reporter derives the freshness verdict from it. If the monitor stops
    printing a JSON object with a boolean source_fresh, freshness silently
    becomes UNKNOWN forever. These tests fail instead.
    """


@pytest.mark.asyncio
async def test_monitor_snapshot_carries_boolean_source_fresh():
    from datetime import UTC, datetime

    from api.services.pipeline_health import get_pipeline_health
    from tests.test_pipeline_health import HealthConnection

    snapshot = await get_pipeline_health(HealthConnection(now=datetime.now(UTC)))

    assert isinstance(snapshot, dict)
    assert isinstance(snapshot.get("source_fresh"), bool), (
        "report_watchdog_verdicts derives FRESH/STALE from a boolean "
        "source_fresh; without it every run reports UNKNOWN."
    )


@pytest.mark.asyncio
async def test_reporter_reads_a_real_monitor_snapshot_end_to_end(tmp_path):
    """The monitor's actual stdout, fed to the reporter, yields a real verdict."""
    from datetime import UTC, datetime

    from api.services.pipeline_health import get_pipeline_health
    from tests.test_pipeline_health import HealthConnection

    snapshot = await get_pipeline_health(HealthConnection(now=datetime.now(UTC)))
    # Exactly what tools/check_new_registration_pipeline.py writes to stdout.
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2))

    report = build_report("success", load_snapshot(path))

    assert report["monitor_execution"]["verdict"] == MONITOR_OK
    assert report["source_data_freshness"]["verdict"] in (FRESH, STALE)
    assert report["source_data_freshness"]["verdict"] != UNKNOWN


def test_monitor_prints_the_snapshot_as_json():
    """The tee'd stdout must be the JSON snapshot, not formatted prose."""
    source = Path("tools/check_new_registration_pipeline.py").read_text(encoding="utf-8")
    assert "print(json.dumps(snapshot, indent=2))" in source
