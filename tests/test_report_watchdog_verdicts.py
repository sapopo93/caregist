"""Monitor health and source freshness must never collapse into one verdict."""

from __future__ import annotations

import json

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
