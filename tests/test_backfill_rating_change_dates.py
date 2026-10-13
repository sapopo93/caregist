"""Tests for tools/backfill_rating_change_dates.py.

The rule under test: a NULL-dated rating_changed row gains a date only from
CQC's own report date for the rating it moved to, never from observation time.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from tools import backfill_rating_change_dates as tool

OBSERVED = datetime(2026, 9, 1, 3, 0, tzinfo=timezone.utc)


def _row(**overrides):
    row = {
        "id": 7,
        "location_id": "1-100",
        "old_value": json.dumps("Good"),
        "new_value": json.dumps("Requires improvement"),
        "observed_at": OBSERVED,
        "effective_date": None,
        "rating_state": "rated",
        "overall_rating": "Requires Improvement",
        "last_published_rating_date": date(2026, 8, 20),
    }
    row.update(overrides)
    return row


def test_dates_a_grade_move_from_the_cqc_report_date():
    decision = tool.decide(_row())
    assert decision.reason == "dated"
    assert decision.effective_date == date(2026, 8, 20)


def test_never_dates_sentinel_or_blank_destinations():
    for new in (json.dumps("Not Yet Inspected"), json.dumps(""), None):
        assert tool.decide(_row(new_value=new)).reason == "not_a_grade_to_grade_move"


def test_never_dates_when_the_location_has_moved_on():
    assert tool.decide(_row(overall_rating="Good")).reason == "current_rating_differs_from_destination"
    assert tool.decide(_row(rating_state="not_published")).reason == "location_not_currently_rated"


def test_never_substitutes_observation_time_for_a_missing_report_date():
    decision = tool.decide(_row(last_published_rating_date=None))
    assert decision.effective_date is None
    assert decision.reason == "no_cqc_report_date_on_record"


def test_rejects_a_report_date_after_the_observation():
    decision = tool.decide(_row(last_published_rating_date=date(2026, 9, 2)))
    assert decision.effective_date is None
    assert decision.reason == "report_date_after_observation"


def test_leaves_already_dated_rows_alone():
    assert tool.decide(_row(effective_date=date(2026, 8, 1))).reason == "already_dated"


class _FakeConn:
    def __init__(self, rows, undated):
        self.rows = rows
        self.undated = undated
        self.updates = []

    async def fetchval(self, sql, *args):
        return self.undated

    async def fetch(self, sql, *args):
        return self.rows

    async def execute(self, sql, *args):
        self.updates.append(args)
        return "UPDATE 1"

    def transaction(self):
        conn = self

        class _Tx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *exc):
                return False

        return _Tx()


async def test_dry_run_writes_nothing_and_counts_superseded_rows():
    conn = _FakeConn([_row(), _row(id=8, location_id="1-200", overall_rating="Good")], undated=5)
    report = await tool.backfill(conn, apply=False)
    assert conn.updates == []
    assert report["datable_rows"] == 1
    assert report["rows_written"] == 0
    assert report["reasons"]["superseded_by_later_move"] == 3


async def test_apply_writes_only_datable_rows_with_the_cqc_source_label():
    conn = _FakeConn([_row(), _row(id=8, location_id="1-200", overall_rating="Good")], undated=2)
    report = await tool.backfill(conn, apply=True)
    assert conn.updates == [(7, date(2026, 8, 20), tool.EFFECTIVE_DATE_SOURCE)]
    assert report["rows_written"] == 1
