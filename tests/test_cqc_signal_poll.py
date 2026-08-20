from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from tools import poll_cqc_signals


def test_workflow_runs_poller_as_importable_module():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/cqc-signal-poll.yml").read_text()

    assert "python -m tools.poll_cqc_signals" in workflow
    assert "python tools/poll_cqc_signals.py" not in workflow
    assert "timeout-minutes: 50" in workflow


def test_scheduled_production_smoke_keeps_release_identity_check():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/production-smoke.yml").read_text()

    assert "CAREGIST_EXPECTED_GIT_SHA: ${{ github.sha }}" in workflow


def test_stale_running_polls_are_failed_closed():
    cursor = Mock()
    cursor.rowcount = 2

    closed = poll_cqc_signals._close_stale_running_polls(cursor, older_than_minutes=40)

    assert closed == 2
    sql, params = cursor.execute.call_args.args
    assert "stale_running_signal_poll" in sql
    assert "status = 'running'" in sql
    assert params[1] == 40


def test_stop_signal_handler_raises_bounded_interruption():
    installed = {}

    with patch.object(
        poll_cqc_signals.signal,
        "signal",
        side_effect=lambda signum, handler: installed.__setitem__(signum, handler),
    ):
        poll_cqc_signals._install_stop_signals()

    with pytest.raises(poll_cqc_signals.SignalPollInterrupted, match="signal"):
        installed[poll_cqc_signals.signal.SIGTERM](poll_cqc_signals.signal.SIGTERM, None)


def test_interrupted_poll_fails_active_run_and_releases_lock():
    cursor = Mock()
    cursor.fetchone.side_effect = [(True,), (77,)]
    connection = Mock()
    connection.cursor.return_value = cursor

    with patch.object(poll_cqc_signals.psycopg2, "connect", return_value=connection), \
         patch.object(poll_cqc_signals, "_close_stale_running_polls", return_value=0), \
         patch.object(
             poll_cqc_signals,
             "_fetch_all_cqc_location_stubs",
             side_effect=poll_cqc_signals.SignalPollInterrupted("received signal 15"),
         ), pytest.raises(poll_cqc_signals.SignalPollInterrupted):
        poll_cqc_signals.run_signal_poll("postgresql://example", "key", report_enabled=False)

    executed_sql = [call.args[0] for call in cursor.execute.call_args_list]
    assert any("status = 'failed'" in sql for sql in executed_sql)
    assert any("pg_advisory_unlock" in sql for sql in executed_sql)
    connection.rollback.assert_called_once()
    assert connection.commit.call_count >= 3
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_interruption_after_partial_progress_preserves_attempted_evidence():
    cursor = Mock()
    cursor.fetchone.side_effect = [(True,), (77,), (0,)]
    connection = Mock()
    connection.cursor.return_value = cursor
    details = [
        {"locationId": "1-10000"},
        poll_cqc_signals.SignalPollInterrupted("received signal 15"),
    ]

    with patch.object(poll_cqc_signals.psycopg2, "connect", return_value=connection), \
         patch.object(poll_cqc_signals, "_close_stale_running_polls", return_value=0), \
         patch.object(
             poll_cqc_signals,
             "fetch_report_candidates",
             return_value=({"1-10000", "1-10001"}, b"report index", "https://example.test/reports"),
         ), patch.object(poll_cqc_signals, "_upsert_source_snapshot", return_value=9), \
         patch.object(poll_cqc_signals, "_rolling_sweep_ids", return_value=[]), \
         patch.object(poll_cqc_signals, "fetch_location_detail", side_effect=details), \
         patch.object(poll_cqc_signals, "clean_location", return_value={"id": "1-10000"}), \
         patch.object(poll_cqc_signals, "upsert_provider", return_value="updated"), \
         patch.object(poll_cqc_signals.time, "sleep"), \
         pytest.raises(poll_cqc_signals.SignalPollInterrupted):
        poll_cqc_signals.run_signal_poll(
            "postgresql://example",
            "key",
            index_enabled=False,
            report_enabled=True,
            checkpoint_size=100,
        )

    failed_update = next(
        call for call in cursor.execute.call_args_list if "status = 'failed'" in call.args[0]
    )
    failed_state = json.loads(failed_update.args[1][1])
    assert failed_state["attemptedOffset"] == 2
    assert failed_state["lastAttemptedLocationId"] == "1-10001"
    assert failed_state["attemptedSuccessCount"] == 1
    assert failed_state["attemptedFailureCount"] == 0
    assert failed_state["attemptedSkippedNotFoundCount"] == 0
    connection.rollback.assert_called_once()


class IndexCursor:
    def __init__(self, count: int, known: set[str] | None = None):
        self.count = count
        self.known = known or set()
        self.current = ""

    def execute(self, query: str, *_args):
        self.current = query

    def fetchone(self):
        if "COUNT(*)" in self.current:
            return (self.count,)
        raise AssertionError(self.current)

    def fetchall(self):
        if "location_id = ANY" in self.current:
            return [(value,) for value in sorted(self.known)]
        raise AssertionError(self.current)


def test_disabled_collectors_skip_before_database_connection():
    with patch.object(poll_cqc_signals.psycopg2, "connect") as connect:
        result = poll_cqc_signals.run_signal_poll(
            "postgresql://unused",
            "unused",
            index_enabled=False,
            report_enabled=False,
        )

    assert result == {
        "skipped": True,
        "new_ids": 0,
        "report_candidates": 0,
        "processed": 0,
        "events": 0,
    }
    connect.assert_not_called()


def test_location_index_bootstrap_does_not_emit_historical_ids():
    cursor = IndexCursor(count=0)
    checked_at = datetime.now(UTC)

    with patch.object(poll_cqc_signals, "execute_values") as execute_values:
        bootstrapping, new_ids = poll_cqc_signals._record_location_index(
            cursor,
            {"1-12345", "1-67890"},
            snapshot_id=7,
            checked_at=checked_at,
        )

    assert bootstrapping is True
    assert new_ids == []
    assert len(execute_values.call_args.args[2]) == 2


def test_location_index_emits_only_stable_ids_not_seen_before():
    cursor = IndexCursor(count=2, known={"1-12345"})

    with patch.object(poll_cqc_signals, "execute_values"):
        bootstrapping, new_ids = poll_cqc_signals._record_location_index(
            cursor,
            {"1-12345", "1-67890"},
            snapshot_id=8,
            checked_at=datetime.now(UTC),
        )

    assert bootstrapping is False
    assert new_ids == ["1-67890"]


def test_report_index_extraction_keeps_only_cqc_location_ids():
    response = SimpleNamespace(
        content=b"report index",
        text=(
            '<a href="/location/1-12345/reports">one</a>'
            '<a href="/location/not-an-id">bad</a>'
            '<a href="https://www.cqc.org.uk/location/1-678901?referer=report">two</a>'
        ),
        url="https://www.cqc.org.uk/search/all?sort=date",
    )
    with patch.object(poll_cqc_signals, "_request_with_retries", return_value=response):
        location_ids, content, source_url = poll_cqc_signals.fetch_report_candidates()

    assert location_ids == {"1-12345", "1-678901"}
    assert content == b"report index"
    assert source_url.startswith("https://www.cqc.org.uk/search/all")


def test_source_snapshot_checksum_conflict_preserves_original_observation():
    cursor = Mock()
    cursor.fetchone.side_effect = [None, (41,)]

    snapshot_id = poll_cqc_signals._upsert_source_snapshot(
        cursor,
        source_type="cqc_location_index",
        source_uri="https://api.service.cqc.org.uk/public/v1/locations",
        checksum_sha256="a" * 64,
        record_count=12,
        checked_at=datetime(2026, 8, 10, tzinfo=UTC),
    )

    assert snapshot_id == 41
    insert_sql = cursor.execute.call_args_list[0].args[0]
    assert "ON CONFLICT (source_type, checksum_sha256) DO NOTHING" in insert_sql
    assert "DO UPDATE" not in insert_sql
    assert "SELECT id FROM source_snapshots" in cursor.execute.call_args_list[1].args[0]


def test_signal_run_evidence_persists_bounded_checkpoint_counts():
    cursor = Mock()

    poll_cqc_signals._update_run_evidence(
        cursor,
        91,
        source_total=10,
        checked=7,
        successes=6,
        failures=1,
        checkpoint_state={"nextOffset": 7, "restartable": True},
    )

    sql, params = cursor.execute.call_args.args
    assert "source_total_count = %s" in sql
    assert "checked_count = %s" in sql
    assert "success_count = %s" in sql
    assert "failure_count = %s" in sql
    assert params[:4] == (10, 7, 6, 1)
    assert json.loads(params[4]) == {"nextOffset": 7, "restartable": True}


def test_checkpoint_evidence_preserves_confirmed_not_found_records():
    state = poll_cqc_signals._signal_checkpoint_state(
        next_offset=5,
        last_location_id="1-12345",
        failure_details=[{"locationId": "1-99999", "reason": "timeout"}],
        skipped_not_found=["1-11111", "1-22222"],
        full_coverage=False,
    )

    assert state == {
        "nextOffset": 5,
        "lastLocationId": "1-12345",
        "restartable": False,
        "restartMode": "fresh_run",
        "failures": [{"locationId": "1-99999", "reason": "timeout"}],
        "skippedNotFound": ["1-11111", "1-22222"],
        "skippedNotFoundCount": 2,
        "fullCoverage": False,
    }


def test_signal_poll_records_bounded_per_location_failure_reasons():
    source = Path("tools/poll_cqc_signals.py").read_text(encoding="utf-8")

    assert '"reason": "detail_fetch_failed"' in source
    assert '"reason": "detail_clean_failed"' in source
    assert "failure_details=failure_details" in source


def test_main_kill_switch_skips_without_reading_credentials(monkeypatch):
    monkeypatch.setenv("CQC_LOCATION_INDEX_POLL_ENABLED", "false")
    monkeypatch.setenv("CQC_REPORT_POLL_ENABLED", "false")
    monkeypatch.setattr(poll_cqc_signals, "parse_args", lambda: SimpleNamespace(
        database_url=None,
        base_url=poll_cqc_signals.DEFAULT_BASE_URL,
        sweep_size=1_200,
        checkpoint_size=100,
        sleep=0.0,
    ))

    with patch.object(poll_cqc_signals, "get_database_url") as database_url, \
         patch.object(poll_cqc_signals, "get_api_key") as api_key:
        assert poll_cqc_signals.main() == 0

    database_url.assert_not_called()
    api_key.assert_not_called()
