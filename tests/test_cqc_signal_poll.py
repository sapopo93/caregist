from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools import poll_cqc_signals


def test_workflow_runs_poller_as_importable_module():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/cqc-signal-poll.yml").read_text()

    assert "python -m tools.poll_cqc_signals" in workflow
    assert "python tools/poll_cqc_signals.py" not in workflow


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
