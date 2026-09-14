"""The reconciliation divergence block is report-only and must never fail a run.

These tests pin the three properties that a cross-family review found defective
in the first cut of the divergence gate:

1. a batch the finalize guard legitimately accepted (manifest-scoped inactivity
   at the 5% bound) must not be reported as a failure, even though the
   estate-wide drop ratio comes out above the guard's bound;
2. a large drop on a single historical batch must not fail anything here (the
   lookback window, which keeps such a batch out of the query entirely, is
   covered by the query itself and exercised against real Postgres in the PR
   evidence);
3. a completed batch whose ``active_records_after`` is NULL must be surfaced as
   unmeasured instead of being silently dropped from the report.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from tools.verify_reconciliation_gates import DIVERGENCE_WINDOW_DAYS, _divergence_report

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
# Sentinel so a test can pass an explicit completed_at=None, which is exactly
# the half-written state the report must not hide.
_UNSET = object()


def _row(
    *,
    before: int | None,
    after: int | None,
    location_count: int = 1000,
    records_deactivated: int = 0,
    completed_at: object = _UNSET,
    batch_id: uuid.UUID | None = None,
) -> dict:
    """A reconciliation_batches row as asyncpg would hand it to the summariser."""
    return {
        "id": batch_id or uuid.uuid4(),
        "location_count": location_count,
        "active_records_before": before,
        "active_records_after": after,
        "records_deactivated": records_deactivated,
        "completed_at": NOW if completed_at is _UNSET else completed_at,
    }


def _assert_never_fails(report: dict) -> None:
    assert report["passed"] is True
    assert report["report_only"] is True
    assert report["issues"] == []


def test_guard_approved_batch_is_reported_as_information_not_a_failure():
    """1000 manifest locations, 50 inactive (= 5.00%, guard accepts) + 52 rogue rows deactivated.

    The estate-wide figures read 1002 -> 950, a 5.19% drop that is above the
    guard's 5% bound while the guard correctly accepted the batch. Report-only
    means that must be surfaced as a number and nothing more.
    """
    report = _divergence_report([_row(before=1002, after=950, records_deactivated=52)], 30)

    _assert_never_fails(report)
    assert report["values"]["reconciliation_batches_checked"] == 1
    assert report["values"]["batches_with_a_measured_drop"] == 1
    assert report["values"]["max_active_drop_ratio_in_window"] == round(52 / 1002, 6)
    assert report["values"]["max_active_drop_ratio_in_window"] > 0.05
    batch = report["values"]["batches"][0]
    assert batch["active_drop"] == 52
    assert batch["active_drop_ratio"] == round(52 / 1002, 6)
    assert batch["measured"] is True


def test_a_historical_batch_above_the_bound_still_fails_nothing():
    """A completed batch with a 50% drop is reported, never asserted against."""
    report = _divergence_report([_row(before=100, after=50, completed_at=NOW - timedelta(days=3650))], 30)

    _assert_never_fails(report)
    assert report["values"]["max_active_drop_ratio_in_window"] == 0.5
    assert report["values"]["batches"][0]["active_drop_ratio"] == 0.5
    assert "threshold" in report["values"]["note"]


def test_completed_batch_without_active_records_after_is_surfaced_not_silently_skipped():
    """The NULL active_records_after state must appear in the report."""
    missing_id = uuid.uuid4()
    report = _divergence_report(
        [
            _row(before=1000, after=990, batch_id=uuid.uuid4()),
            _row(before=1002, after=None, batch_id=missing_id),
        ],
        30,
    )

    _assert_never_fails(report)
    assert report["values"]["reconciliation_batches_checked"] == 2
    assert report["values"]["batches_with_a_measured_drop"] == 1
    assert report["values"]["batches_unmeasured"] == {str(missing_id): "active_records_after is NULL"}
    assert any(str(missing_id) in observation for observation in report["observations"])
    # The measured batch is still reported alongside the unmeasured one.
    assert report["values"]["max_active_drop_ratio_in_window"] == 0.01


def test_completed_batch_without_a_completion_timestamp_is_surfaced_not_silently_skipped():
    """A completed batch the window cannot place must still appear in the report.

    ``completed_at >= NOW() - interval`` is NULL-false, so a completed batch with
    a NULL completed_at would vanish from a naive windowed query — the same class
    of hole as the NULL active_records_after that was filtered away before.
    """
    undated_id = uuid.uuid4()
    report = _divergence_report([_row(before=1000, after=950, completed_at=None, batch_id=undated_id)], 30)

    _assert_never_fails(report)
    assert report["values"]["reconciliation_batches_checked"] == 1
    assert report["values"]["batches_without_completed_at"] == [str(undated_id)]
    assert report["values"]["batches_unmeasured"] == {}
    # The drop is still measured for the reader; it just cannot count towards
    # the window maximum because the batch cannot be placed in the window.
    assert report["values"]["max_active_drop_ratio_in_window"] is None
    assert report["values"]["batches"][0]["active_drop_ratio"] == 0.05
    assert report["values"]["batches"][0]["in_window"] is False
    assert any(str(undated_id) in observation for observation in report["observations"])


def test_missing_before_figure_is_reported_as_unmeasurable_rather_than_dividing_by_nothing():
    report = _divergence_report([_row(before=None, after=10)], 30)

    _assert_never_fails(report)
    assert report["values"]["batches_with_a_measured_drop"] == 0
    assert report["values"]["max_active_drop_ratio_in_window"] is None
    assert list(report["values"]["batches_unmeasured"].values()) == [
        "active_records_before is None, so there is no denominator"
    ]


def test_empty_window_states_that_there_is_nothing_to_report():
    report = _divergence_report([], DIVERGENCE_WINDOW_DAYS)

    _assert_never_fails(report)
    assert report["values"]["window_days"] == DIVERGENCE_WINDOW_DAYS
    assert report["values"]["reconciliation_batches_checked"] == 0
    assert report["values"]["max_active_drop_ratio_in_window"] is None
    assert report["values"]["note"] == "no completed reconciliation batches in the window"


def test_the_report_never_carries_a_pass_fail_assertion_for_any_batch_shape():
    """Sweep the plausible row shapes: no combination may produce an issue."""
    report = _divergence_report(
        [
            _row(before=1002, after=950, records_deactivated=52),
            _row(before=100, after=50),
            _row(before=1000, after=1000, records_deactivated=0),
            _row(before=0, after=0),
            _row(before=None, after=None),
            _row(before=10, after=20),
            _row(before=1000, after=950, completed_at=None),
        ],
        7,
    )

    _assert_never_fails(report)
    assert report["values"]["reconciliation_batches_checked"] == 7
    assert report["values"]["max_active_drop_ratio_in_window"] == 0.5
    assert report["observations"]
