"""Tests for the nightly CQC report: truthful cadence, buckets, verdicts, ratios.

The report's whole job is to be literally true, so these tests pin the four
things that made earlier reports lie:

1. the expected poll count is derived from the configured cron, and a constant
   that contradicts the cron is loud rather than silently used;
2. the five coverage buckets (expected/attempted/successful/failed/missed) are
   counted separately, and unknown is never rendered as zero;
3. DATA ALIGNMENT and PIPELINE HEALTH pick their verdict independently;
4. every completeness figure carries an explicit numerator and denominator.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "nightly_cqc_db_check.py"
FIXTURE = Path(__file__).resolve().parent / "data" / "nightly-report-no-remote.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("nightly_cqc_db_check", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["nightly_cqc_db_check"] = module
    spec.loader.exec_module(module)
    return module


nightly = _load_module()

NOW = datetime(2026, 9, 20, 4, 10, tzinfo=UTC)
WINDOW_START = NOW - timedelta(days=7)
WINDOW_END = NOW


def _schedules(path: Path | str = nightly.SIGNAL_POLL_WORKFLOW):
    parsed = nightly.workflow_schedule(path)
    return [nightly.parse_cron(expr) for expr in parsed["crons"]]


def _run(moment: datetime, *, event: str = "schedule", conclusion: str = "success") -> dict:
    return {
        "created_at": moment,
        "event": event,
        "conclusion": conclusion,
        "database_id": 1,
        "status": "completed",
    }


def _fire_times(schedules, start: datetime, end: datetime) -> list[datetime]:
    return sorted(
        {fire for schedule in schedules for fire in schedule.fires_between(start, end)}
    )


# --------------------------------------------------------------------------
# 1. cadence derived from the workflow, with a loud drift guard
# --------------------------------------------------------------------------
def test_expected_cadence_is_derived_from_the_workflow_cron():
    cadence = nightly.derive_cadence(now=NOW)
    assert cadence["expressions"] == ["37 18,21,0,3 * * *"]
    assert cadence["runs_per_day"] == 4
    assert cadence["runs_per_week"] == 28
    assert "cqc-signal-poll.yml" in cadence["source"]


def test_required_weekly_constant_matches_the_cron_or_fails_loudly():
    """The drift guard: the named fallback constant must equal the live cron."""
    notes = nightly.cadence_drift_notes(nightly.SIGNAL_POLL_WORKFLOW)
    assert notes == [], f"cadence constants drifted from the workflow cron: {notes}"
    fallback = nightly.parse_cron(nightly.WORKFLOW_CRON_FALLBACK)
    assert fallback.runs_per_week(NOW) == 28
    # 336 was the number a stale 48/day cron produced; it must never come back
    # as a hard-coded expectation.
    assert not hasattr(nightly, "REQUIRED_WEEKLY_POLLS")


def test_old_48_per_day_cron_yields_336_not_the_configured_28(tmp_path: Path):
    workflow = tmp_path / "cqc-signal-poll.yml"
    workflow.write_text(
        "on:\n  schedule:\n    - cron: \"7,37 * * * *\"\n", encoding="utf-8"
    )
    assert nightly.derive_cadence(path=workflow, now=NOW)["runs_per_week"] == 336
    assert nightly.cadence_drift_notes(workflow) != []


def test_drift_between_constant_and_cron_makes_pipeline_health_unverified(tmp_path: Path):
    workflow = tmp_path / "cqc-signal-poll.yml"
    workflow.write_text(
        "on:\n  schedule:\n    - cron: \"7,37 * * * *\"\n", encoding="utf-8"
    )
    verdict = nightly.pipeline_health_verdict(
        coverage=None,
        sweep=None,
        freshness=None,
        observed_sweep=None,
        run_history_status="ok",
        drift_notes=nightly.cadence_drift_notes(workflow),
    )
    assert verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert "disagree" in verdict["reasons"][0]


def test_cron_parser_rejects_malformed_expressions():
    with pytest.raises(ValueError):
        nightly.parse_cron("7 18,21 * *")  # four fields
    with pytest.raises(ValueError):
        nightly.parse_cron_field("99", name="hour")  # hour 99 is out of range
    with pytest.raises(ValueError):
        nightly.parse_cron("nonsense")


# --------------------------------------------------------------------------
# 2. five coverage buckets
# --------------------------------------------------------------------------
def test_five_coverage_buckets_are_counted_separately():
    schedules = _schedules()
    fires = _fire_times(schedules, WINDOW_START, WINDOW_END)
    assert len(fires) == 28  # 4 fires/day x 7 days, from the cron
    # the newest fire may still be inside the grace period, so the due set is
    # the denominator for the delivered buckets
    due = [fire for fire in fires if fire <= NOW - nightly.MISSED_GRACE]
    assert len(due) == 27
    skipped = [due[3], due[10], due[17]]
    ran = [fire for fire in due if fire not in skipped]

    coverage = nightly.poll_coverage(
        [_run(fire) for fire in ran],
        schedules=schedules,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        now=NOW,
    )
    assert coverage["expected"]["runs"] == 28
    assert coverage["expected"]["due"] == 27
    assert coverage["expected"]["not_yet_due"] == 1
    assert coverage["attempted"]["runs"] == 24
    assert coverage["successful"]["runs"] == 24
    assert coverage["failed"]["runs"] == 0
    assert coverage["missed"]["runs"] == 3
    # the fair statement of *which* fires went unpaired is greedy-matching
    # dependent, so only the count and the window are asserted
    assert len(coverage["missed"]["fires"]) == 3
    assert all(fire.startswith("2026-09-1") for fire in coverage["missed"]["fires"])
    assert "gh run list" in coverage["attempted"]["source"]
    assert "workflow cron" in coverage["expected"]["source"]
    # the buckets are mutually exclusive, so they reconcile against attempted
    consistency = coverage["consistency"]
    assert (
        consistency["successful_plus_failed_plus_cancelled_plus_in_flight"]
        == consistency["attempted"]
    )


def test_failed_cancelled_and_in_flight_are_not_counted_as_success():
    schedules = _schedules()
    due = _fire_times(schedules, WINDOW_START, WINDOW_END)[:4]
    runs = [
        _run(due[0]),
        _run(due[1], conclusion="failure"),
        _run(due[2], conclusion="cancelled"),
        _run(due[3], conclusion="in_progress"),
    ]
    coverage = nightly.poll_coverage(
        runs, schedules=schedules, window_start=WINDOW_START, window_end=WINDOW_END, now=NOW
    )
    assert coverage["successful"]["runs"] == 1
    assert coverage["failed"]["runs"] == 1
    assert coverage["cancelled"]["runs"] == 1
    assert coverage["in_flight"]["runs"] == 1
    assert coverage["failed"]["by_conclusion"] == {"failure": 1}
    assert "not counted as failed" in coverage["cancelled"]["source"]


def test_manual_dispatches_are_reported_but_not_counted_as_scheduled_ticks():
    schedules = _schedules()
    due = _fire_times(schedules, WINDOW_START, WINDOW_END)[:2]
    runs = [_run(due[0]), _run(due[1] + timedelta(minutes=5), event="workflow_dispatch")]
    coverage = nightly.poll_coverage(
        runs, schedules=schedules, window_start=WINDOW_START, window_end=WINDOW_END, now=NOW
    )
    assert coverage["attempted"]["runs"] == 1
    assert coverage["attempted"]["manual_or_other_event_runs"] == 1


def test_unavailable_run_history_never_renders_unknown_as_zero():
    schedules = _schedules()
    coverage = nightly.coverage_unavailable(
        "gh: not authenticated",
        schedules=schedules,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        now=NOW,
    )
    assert coverage["available"] is False
    assert coverage["expected"]["runs"] == 28  # the cron needs no network
    assert coverage["reason"] == "gh: not authenticated"
    # unknown, not zero: the delivered buckets exist but carry None
    assert coverage["attempted"]["runs"] is None
    assert coverage["successful"]["runs"] is None
    assert coverage["failed"]["runs"] is None
    assert coverage["missed"]["runs"] is None

    verdict = nightly.pipeline_health_verdict(
        coverage=coverage,
        sweep=None,
        freshness=None,
        observed_sweep=None,
        run_history_status="unavailable",
        drift_notes=[],
    )
    assert verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert verdict["verdict"] != nightly.VERDICT_MATCHED


def test_a_period_that_has_not_elapsed_is_not_claimed_as_missed():
    schedules = _schedules()
    coverage = nightly.poll_coverage(
        [],
        schedules=schedules,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        now=WINDOW_END + timedelta(minutes=5),  # the newest ticks are not yet due
    )
    assert coverage["expected"]["not_yet_due"] >= 1
    assert coverage["expected"]["due"] + coverage["expected"]["not_yet_due"] == 28
    assert coverage["missed"]["runs"] == coverage["expected"]["due"]


# --------------------------------------------------------------------------
# 3. verdict selection, per verdict domain
# --------------------------------------------------------------------------
FULL_SNAPSHOT = {
    "coverage": "full",
    "published_at": "2026-09-16",
    "sha256": "bed9e95a1701ade0c4933bdf3acda7a9c4c94e3940a19ad698575a05a66eecb0",
    "entity_count": 57127,
}
UP_TO_DATE = {"newest_snapshot_covered": True, "latest_covered_published_at": "2026-09-16"}


def _summary(*, defect: int = 0, unexplained: int = 0, legitimate: int = 0) -> dict:
    return {
        "confirmed_defect": defect,
        "unexplained": unexplained,
        "legitimate_timing_or_scope": legitimate,
        "defect_classes": {"db_active:confirmed_deregistered_still_active_in_db": defect} if defect else {},
        "unexplained_classes": {"only_in_db_active:unclassified_status": unexplained} if unexplained else {},
        "coverage": "full",
        "source": "live CQC API location detail",
    }


DIFF = {"overlap": 57066, "only_in_db_active": [], "only_in_source": []}


def test_alignment_matched_when_nothing_is_unexplained():
    verdict = nightly.data_alignment_verdict(
        snapshot=FULL_SNAPSHOT,
        diff=DIFF,
        summary=_summary(legitimate=67, unexplained=0, defect=0),
        ingested=UP_TO_DATE,
        # A complete run reports its reconciliation-input problems; the verdict
        # path now also derives them, so an unreported list is not "no problems".
        incompleteness=[],
    )
    assert verdict["verdict"] == nightly.VERDICT_MATCHED
    assert "no unexplained differences" in verdict["reasons"][0]


def test_alignment_mismatched_when_a_defect_or_an_unexplained_difference_exists():
    defects = nightly.data_alignment_verdict(
        snapshot=FULL_SNAPSHOT, diff=DIFF, summary=_summary(defect=3), ingested=UP_TO_DATE, incompleteness=[]
    )
    assert defects["verdict"] == nightly.VERDICT_MISMATCHED
    assert "confirmed defect" in defects["reasons"][0]

    unexplained = nightly.data_alignment_verdict(
        snapshot=FULL_SNAPSHOT, diff=DIFF, summary=_summary(unexplained=5), ingested=UP_TO_DATE, incompleteness=[]
    )
    assert unexplained["verdict"] == nightly.VERDICT_MISMATCHED
    assert any("unexplained difference" in reason for reason in unexplained["reasons"])


def test_alignment_unverified_when_the_newest_snapshot_is_not_covered_by_a_run():
    """Stale reconciliation is UNVERIFIED, not MATCHED and not MISMATCHED."""
    verdict = nightly.data_alignment_verdict(
        snapshot=FULL_SNAPSHOT,
        diff=DIFF,
        summary=_summary(legitimate=67),
        ingested={"newest_snapshot_covered": False, "latest_covered_published_at": "2026-09-09"},
    )
    assert verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("2026-09-09" in reason for reason in verdict["reasons"])


def test_alignment_unverified_when_the_snapshot_could_not_be_read():
    verdict = nightly.data_alignment_verdict(
        snapshot={"coverage": "unavailable", "error": "HTTP 503"},
        diff=None,
        summary=None,
        ingested=UP_TO_DATE,
    )
    assert verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("503" in reason for reason in verdict["reasons"])


def test_alignment_unverified_when_a_fetch_was_sampled_or_unchecksummed():
    sampled = nightly.data_alignment_verdict(
        snapshot={**FULL_SNAPSHOT, "coverage": "sampled", "entity_count": 5000, "byte_cap": 1, "id_cap": 5000},
        diff=DIFF,
        summary=_summary(legitimate=1),
        ingested=UP_TO_DATE,
    )
    assert sampled["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("sampled" in reason for reason in sampled["reasons"])

    unchecksummed = nightly.data_alignment_verdict(
        snapshot={**FULL_SNAPSHOT, "sha256": None}, diff=DIFF, summary=_summary(legitimate=1), ingested=UP_TO_DATE
    )
    assert unchecksummed["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("checksum" in reason for reason in unchecksummed["reasons"])


def test_the_two_verdicts_are_independent():
    """A stale datasource must not make the alignment verdict look healthy."""
    bundle = nightly.build_verdicts(
        snapshot={**FULL_SNAPSHOT, "coverage": "unavailable", "error": "no snapshot"},
        diff=None,
        summary=None,
        ingested=UP_TO_DATE,
        coverage=None,
        sweep=None,
        observed_sweep=None,
        freshness={
            "signal": {"within_sla": False, "age_hours": 21.0, "sla_hours": 16.0},
            "ingested_source": {"within_sla": False, "age_hours": 268.5, "published_at": "2026-09-09", "sla_hours": 192.0},
        },
        run_history_status="ok",
        drift_notes=[],
    )
    assert bundle["data_alignment"]["verdict"] == nightly.VERDICT_UNVERIFIED
    assert bundle["pipeline_health"]["verdict"] == nightly.VERDICT_MISMATCHED
    assert set(bundle["vocabulary"]) == {"MATCHED", "MISMATCHED", "UNVERIFIED"}


def test_pipeline_health_matched_only_when_every_documented_promise_holds():
    epochs = [epoch for epoch in nightly.schedule_history() if epoch.effective_from is not None]
    if not epochs:
        pytest.skip("shallow checkout: the workflow's schedule history is not available")
    due: list[datetime] = []
    for index, epoch in enumerate(epochs):
        start = max(WINDOW_START, epoch.effective_from)
        end = WINDOW_END
        if index + 1 < len(epochs) and epochs[index + 1].effective_from is not None:
            end = min(end, epochs[index + 1].effective_from)
        for schedule in epoch.schedules():
            due.extend(fire for fire in schedule.fires_between(start, end) if fire <= NOW - nightly.MISSED_GRACE)
    due = sorted(set(due))
    coverage = nightly.poll_coverage(
        [_run(fire) for fire in due],
        epochs=epochs,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        now=NOW,
        db_statuses={"completed": len(due), "partial": 0, "failed": 0, "total": len(due)},
    )
    assert coverage["missed"]["runs"] == 0 and coverage["expected"]["schedule_history_available"] is True
    assert coverage["successful"]["db_cross_checked"] is True
    fresh = {
        "signal": {"within_sla": True, "evaluated": True, "age_hours": 2.0, "sla_hours": 16.0},
        "ingested_source": {
            "within_sla": True,
            "evaluated": True,
            "age_hours": 20.0,
            "published_at": "2026-09-19",
            "sla_hours": 192.0,
        },
    }
    sweep = nightly.sweep_coverage(
        2000, runs_per_week=28, sweep_size=nightly.derive_cadence(now=NOW)["sweep_size"]
    )
    assert (
        nightly.pipeline_health_verdict(
            coverage=coverage,
            sweep=sweep,
            freshness=fresh,
            observed_sweep=None,
            run_history_status="ok",
            drift_notes=[],
        )["verdict"]
        == nightly.VERDICT_MATCHED
    )
    # MATCHED is only for promises that were actually evaluated: no sweep estimate
    # means the sweep-interval promise was never checked, so it cannot be claimed.
    assert (
        nightly.pipeline_health_verdict(
            coverage=coverage,
            sweep=None,
            freshness=fresh,
            observed_sweep=None,
            run_history_status="ok",
            drift_notes=[],
        )["verdict"]
        == nightly.VERDICT_UNVERIFIED
    )
    # a promise that was never evaluated is UNVERIFIED, not silently green
    assert (
        nightly.pipeline_health_verdict(
            coverage=coverage,
            sweep=sweep,
            freshness={"signal": {"within_sla": None, "evaluated": False}, "ingested_source": {}},
            observed_sweep=None,
            run_history_status="ok",
            drift_notes=[],
        )["verdict"]
        == nightly.VERDICT_UNVERIFIED
    )
    # a promise that was evaluated and broken is MISMATCHED, not UNVERIFIED
    assert (
        nightly.pipeline_health_verdict(
            coverage=coverage,
            sweep=sweep,
            freshness={
                "signal": {"within_sla": False, "evaluated": True, "age_hours": 30.0, "sla_hours": 16.0},
                "ingested_source": {"within_sla": True, "evaluated": True},
            },
            observed_sweep=None,
            run_history_status="ok",
            drift_notes=[],
        )["verdict"]
        == nightly.VERDICT_MISMATCHED
    )


# --------------------------------------------------------------------------
# 4. numerator / denominator rendering
# --------------------------------------------------------------------------
def test_ratios_state_numerator_and_denominator():
    assert nightly._ratio(24, 28) == "24 / 28 (85.7%)"
    assert nightly._ratio(28, 28, digits=0) == "28 / 28 (100%)"
    assert nightly._ratio(0, 28) == "0 / 28 (0.0%)"
    # a zero denominator must say so rather than printing a percentage
    assert nightly._ratio(1, 0) == "1 / 0 (n/a)"
    assert nightly._pct(24, 28) == 85.7
    assert nightly._pct(1, 0) == 0.0


def test_wilson_interval_stays_inside_the_unit_range():
    low, high = nightly.wilson_interval(21, 300)
    assert 0.0 <= low < high <= 100.0
    assert nightly.wilson_interval(0, 0) == (0.0, 0.0)  # no sample, no interval


def test_rating_completeness_is_carried_as_numerator_over_denominator():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rating = fixture["rating_events"]
    all_time = rating["all_time"]
    rendered = all_time["rendered"]
    for key in ("no_destination_value", "real_destination", "sentinel_destination", "old_value_sentinel"):
        value = rendered[key]
        assert "/" in value, f"{key} must print as a ratio, got {value!r}"
        assert "%" in value
    total = int(all_time["total"])
    assert int(all_time["no_destination_value"]) + int(all_time["real_destination"]) + int(
        all_time["sentinel_destination"]
    ) == total
    assert f"{total:,}" in rendered["no_destination_value"]
    # window and all-time are separate blocks, each with its own denominator
    window = rating["window"]
    assert "rendered" in window and "/" in window["rendered"]["no_destination_value"]
    assert window["start"] != all_time["start"]
    unresolved = rating["unresolved_detail"]
    assert unresolved["unresolved"] <= int(all_time["total"])
    assert unresolved["unresolved_with_sentinel_prior_value"] <= unresolved["unresolved"]
    assert "Not Yet Inspected" in unresolved["sentinel_values"]
    assert "not a rating" in unresolved["note"]
    # unresolved events are excluded from customer-facing movement claims
    assert "only events with a real published destination rating" in rating["customer_facing_scope"]
    assert "unresolved (null destination)" in rating["customer_facing_scope"]


# --------------------------------------------------------------------------
# 5. identifier-level reconciliation internals
# --------------------------------------------------------------------------
def test_identifier_diff_names_every_divergent_population():
    db = {
        "ACTIVE": frozenset({"A", "B", "C"}),
        "INACTIVE": frozenset({"D"}),
    }
    snapshot = frozenset({"A", "B", "E"})
    diff = nightly.identifier_diff(db, snapshot)
    assert diff["only_in_db_active"] == ["C"]
    assert diff["only_in_source"] == ["E"]
    assert diff["source_but_db_inactive"] == []
    assert diff["overlap"] == 2
    assert set(diff["definitions"]) >= {"only_in_db_active", "only_in_source", "source_but_db_inactive"}


def test_split_counts_separates_confirmed_defects_from_timing_differences():
    classification = {
        "coverage": "full",
        "source": "live CQC API location detail",
        "per_id": {
            "A": {"class": "registered_after_snapshot_publication"},
            "B": {"class": "confirmed_deregistered_still_active_in_db"},
            "C": {"class": "unclassified_status"},
        },
    }
    split = nightly.split_counts(classification, ["A", "B", "C"], side="db_active_absent_from_source")
    assert split["confirmed_defect"] == 1
    assert split["legitimate_timing_or_scope"] == 1
    assert split["unexplained"] == 1
    assert split["population"] == 3
    assert "note" not in split


def test_split_counts_flags_ids_that_were_never_classified():
    classification = {"coverage": "sampled", "per_id": {"A": {"class": "registered_after_snapshot_publication"}}}
    split = nightly.split_counts(classification, ["A", "B"], side="db_active_absent_from_source")
    assert split["classified"] == 1
    assert split["unexplained"] == 0  # the unclassified ID is outside the classified subset
    assert "not classified" in split["note"]


def test_merged_summary_reports_the_worst_coverage_of_any_population():
    merged = nightly.merge_summaries(
        {
            "only_in_db_active": {"coverage": "full", "confirmed_defect": 0, "legitimate_timing_or_scope": 67, "unexplained": 0},
            "source_but_db_inactive": {"coverage": "sampled", "confirmed_defect": 0, "legitimate_timing_or_scope": 61, "unexplained": 0},
        }
    )
    assert merged["coverage"] == "sampled"
    assert merged["legitimate_timing_or_scope"] == 128
    assert "only_in_db_active:legitimate_classes" not in merged


def test_unavailability_placeholder_is_not_a_clean_bill_of_health():
    classification = nightly.classification_unavailable(["A", "B"], side="db_active_absent_from_source")
    assert classification["coverage"] != "full"
    summary = nightly.summarize_classification(classification)
    assert summary["confirmed_defect"] == 0
    assert summary["coverage"] != "full"
    assert nightly.reconciliation_inputs_are_complete({"only_in_source": []}, classification)


# --------------------------------------------------------------------------
# 6. unrated population classification
# --------------------------------------------------------------------------
def _write_evidence(directory: Path, payload: dict) -> Path:
    path = directory / "2026-09-20-unrated-classification.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_unrated_classes_come_from_the_workstream_file_with_a_documented_mapping(tmp_path: Path):
    _write_evidence(
        tmp_path,
        {
            "generated_at": "2026-09-20T04:00:00Z",
            "unrated": {
                "total": 25753,
                "total_is_measured_full_population": True,
                "sample_size": 300,
                "classes": [
                    {"name": "has_published_rating_now", "count": 12, "population_estimate": 1030, "ci95_low_pct": 2.0, "ci95_high_pct": 8.0},
                    {"name": "never_rated_no_historic_overall", "count": 250, "population_estimate": 21460, "ci95_low_pct": 79.0, "ci95_high_pct": 88.0},
                    {"name": "api_404_or_gone", "count": 4, "population_estimate": 343, "ci95_low_pct": 0.5, "ci95_high_pct": 3.5},
                ],
            },
        },
    )
    classification = nightly.load_unrated_classification(tmp_path, count=25753)
    assert classification["source"].endswith("2026-09-20-unrated-classification.json")
    assert classification["population_measured"] is True
    classes = {item["class"] for item in classification["classes"]}
    assert classes == {"ingestion_omission", "not_yet_inspected", "entity_mapping"}
    assert classification["class_map"]["has_published_rating_now"] == "ingestion_omission"
    assert classification["class_map"]["api_404_or_gone"] == "entity_mapping"
    # raw workstream class names are preserved alongside the mapped names
    assert any(item.get("raw_class") for item in classification["classes"])


def test_unrated_classes_are_unknown_when_no_evidence_file_exists(tmp_path: Path, monkeypatch):
    # Neutralise the repo-level fallback so the assertion is about the honest
    # "no evidence" path, not about whatever happens to sit in artifacts/.
    monkeypatch.setattr(nightly, "UNRATED_CLASSIFICATION_FALLBACK_DIRS", ())
    classification = nightly.load_unrated_classification(tmp_path, count=25753)
    assert classification["source"] is None
    assert [item["class"] for item in classification["classes"]] == ["unknown"]
    only = classification["classes"][0]
    assert only["estimate"] == 25753  # the whole population, stated as one unknown class
    assert only["estimator"] is None  # no sample, so no extrapolation is claimed
    assert only["confidence_95_pct"] is None
    assert "rather than guessed" in classification["basis"]


def test_unrated_evidence_search_is_overridable_via_env(tmp_path: Path, monkeypatch):
    """The dated workstream file is found in out_dir; env override pins search dirs."""
    dated = tmp_path / "2026-09-20-unrated-classification.json"
    dated.write_text(
        json.dumps({"unrated": {"sample_size": 10, "class_counts": {"never_rated_no_historic_overall": 10}}}),
        encoding="utf-8",
    )
    assert nightly.unrated_classification_search_dirs(tmp_path)[0] == tmp_path
    monkeypatch.setenv("CQC_UNRATED_CLASSIFICATION_DIR", "")
    empty = tmp_path / "elsewhere"
    empty.mkdir()
    assert nightly.unrated_classification_search_dirs(empty) == [empty]
    classification = nightly.load_unrated_classification(empty, count=5)
    assert classification["source"] is None  # no fallback dir => honest unknown


def test_unrated_render_does_not_invent_classes_or_widths():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    unrated = fixture["unrated"]
    assert unrated["count"] == 25753
    assert unrated["active"] == 57193  # denominator is the location-id ACTIVE population
    assert unrated["classification"]["source"] is None
    classes = unrated["classification"]["classes"]
    assert len(classes) == 1 and classes[0]["class"] == "unknown"
    assert classes[0]["estimator"] is None


# --------------------------------------------------------------------------
# 7. churn is separated from genuine source changes
# --------------------------------------------------------------------------
def test_churn_and_source_changes_are_reported_as_different_quantities():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    churn = fixture["churn"]
    assert churn["rows_rewritten"] > 0
    assert churn["rows_rewritten"] >= churn["rows_rewritten_with_location_event"]
    assert churn["rows_rewritten_without_location_event"] == (
        churn["rows_rewritten"] - churn["rows_rewritten_with_location_event"]
    )
    # churn is many times the genuine change volume: that is the whole point
    assert churn["rows_rewritten_without_location_event"] > churn["ledger_events_in_window"]
    assert "not evidence that CQC published anything" in churn["note"]
    assert "no change" in churn["note"]


# --------------------------------------------------------------------------
# 8. rendering keeps the two verdicts apart
# --------------------------------------------------------------------------
def test_rendered_report_labels_both_verdicts_separately():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    schedules = _schedules()
    fires = _fire_times(schedules, WINDOW_START, WINDOW_END)
    due = [fire for fire in fires if fire <= NOW - nightly.MISSED_GRACE]
    skipped = [due[3], due[10], due[17]]
    coverage = nightly.poll_coverage(
        [_run(fire) for fire in due if fire not in skipped],
        schedules=schedules,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        now=NOW,
    )
    coverage["db_cross_check"] = {
        "source": "pipeline_runs (run_type = signal_poll)",
        "db_signal_poll_completed": 24,
        "db_signal_poll_total_rows": 24,
        "db_all_run_types_rows": 101,
        "db_reconciliation_rows": 3,
        "window": {"start": nightly._iso(WINDOW_START), "end": nightly._iso(WINDOW_END)},
        "reconciliation": "24 scheduled runs in GitHub Actions and 24 rows in pipeline_runs: agree",
    }
    fixture["polls"]["coverage"] = coverage
    fixture["verdicts"]["pipeline_health"] = nightly.pipeline_health_verdict(
        coverage=fixture["polls"]["coverage"],
        sweep=fixture.get("sweep"),
        freshness=fixture.get("freshness"),
        observed_sweep=fixture.get("observed_sweep"),
        run_history_status="ok",
        drift_notes=[],
    )
    markdown = nightly.render(fixture)
    assert "DATA ALIGNMENT: UNVERIFIED" in markdown
    assert "PIPELINE HEALTH" in markdown
    for label in ("Expected", "Attempted", "Successful", "Failed", "Missed"):
        assert label in markdown
    assert "24" in markdown and "27" in markdown  # numerator and denominator both printed
    assert "identifier-level reconciliation against the latest available validated snapshot" in markdown


# --------------------------------------------------------------------------
# 9. corrective commit for the independent FAIL review of 5dc1759
#    (reviewer gpt-5.6-sol: 2 high, 3 medium, 2 low - one test per finding)
# --------------------------------------------------------------------------
REVIEW_CHANGE_AT = datetime(2026, 9, 15, 10, 38, 36, tzinfo=UTC)
REVIEW_START = datetime(2026, 9, 13, 4, 37, tzinfo=UTC)
REVIEW_END = datetime(2026, 9, 20, 4, 37, tzinfo=UTC)
REVIEW_NOW = datetime(2026, 9, 20, 4, 10, tzinfo=UTC)
OLD_CRON = "7,37 * * * *"
NEW_CRON = "7 18,21,0,3 * * *"
CACHE_DIR = REPO_ROOT / "artifacts" / "cqc-nightly" / "cache"
# The commits at which each of the two schedules in force during the reviewed
# window became effective, read from the workflow file's own git history
# (``1e7d594`` 2026-08-31 for the one-hour cron, ``39fa9a3`` 2026-09-03 for the
# reverted two-per-hour cron, ``6bc9880`` 2026-09-15 for the four-a-day cron).
OLD_EFFECTIVE_FROM = datetime(2026, 9, 3, 12, 24, 24, tzinfo=UTC)


def _epoch(crons, effective_from):
    return nightly.ScheduleEpoch(
        crons=tuple(crons), effective_from=effective_from, commit="fixture", source="test fixture"
    )


def _straddling_epochs():
    """The two schedules the 2026-09-13..2026-09-20 window actually straddles.

    Both epochs carry the commit date at which their schedule became effective:
    an undated epoch is counted across the whole window, so it is reported as an
    unverified expectation rather than a measurement.
    """
    return [_epoch([OLD_CRON], OLD_EFFECTIVE_FROM), _epoch([NEW_CRON], REVIEW_CHANGE_AT)]


def _review_coverage(runs=(), *, epochs=None, db_statuses=None):
    return nightly.poll_coverage(
        list(runs),
        epochs=_straddling_epochs() if epochs is None else epochs,
        window_start=REVIEW_START,
        window_end=REVIEW_END,
        now=REVIEW_NOW,
        db_statuses=db_statuses,
    )


def _clean_coverage(*, epochs=None, db_statuses=None):
    """Every in-force tick in the window ran, so nothing but the tested factor moves.

    Without this the fixtures inherit a window full of missed ticks, and a
    MISMATCHED verdict would prove nothing about the promise under test.
    """
    epochs = _straddling_epochs() if epochs is None else epochs
    due: list[datetime] = []
    for index, epoch in enumerate(epochs):
        start = REVIEW_START if epoch.effective_from is None else max(REVIEW_START, epoch.effective_from)
        end = REVIEW_END
        if index + 1 < len(epochs) and epochs[index + 1].effective_from is not None:
            end = min(end, epochs[index + 1].effective_from)
        for expression in epoch.crons:
            due.extend(nightly.parse_cron(expression).fires_between(start, end))
    due = sorted({fire for fire in due if fire <= REVIEW_NOW - nightly.MISSED_GRACE})
    if db_statuses is None:
        db_statuses = {"completed": len(due), "partial": 0, "failed": 0, "total": len(due)}
    coverage = nightly.poll_coverage(
        [_run(fire) for fire in due],
        epochs=epochs,
        window_start=REVIEW_START,
        window_end=REVIEW_END,
        now=REVIEW_NOW,
        db_statuses=db_statuses,
    )
    assert coverage["missed"]["runs"] == 0, coverage["missed"]
    return coverage


def _fresh(**overrides):
    block = {
        "signal": {"within_sla": True, "evaluated": True, "age_hours": 2.0, "sla_hours": 16.0},
        "ingested_source": {
            "within_sla": True,
            "evaluated": True,
            "age_hours": 20.0,
            "published_at": "2026-09-16",
            "sla_hours": 192.0,
        },
    }
    block.update(overrides)
    return block


def _sweep_within_sla():
    cadence = nightly.derive_cadence(now=NOW)
    return nightly.sweep_coverage(2000, runs_per_week=cadence["runs_per_week"], sweep_size=cadence["sweep_size"])


def _health(coverage, freshness):
    return nightly.pipeline_health_verdict(
        coverage=coverage,
        sweep=_sweep_within_sla(),
        freshness=freshness,
        observed_sweep=None,
        run_history_status="ok",
        drift_notes=[],
    )


def test_high1_a_window_spanning_a_cadence_change_sums_every_schedule_in_force():
    """HIGH 1: 5dc1759 applied today's cron across a window that straddles a change.

    The review's arithmetic: 28 expected / 4 missed was the answer for one
    schedule, while the window in force held two - 108 old-cadence fires plus 20
    from the new cadence.
    """
    coverage = _review_coverage()
    assert coverage["expected"]["runs"] == 129
    assert [row["fires"] for row in coverage["expected"]["epochs"]] == [109, 20]
    assert coverage["expected"]["schedule_history_available"] is True
    assert coverage["expected"]["derivation"].endswith("summed per schedule epoch")
    assert coverage["cadence_change"]["expected_runs"] == 20


def test_high1_one_epoch_matches_the_reviewed_reports_28_expected():
    """The reviewed report's 28/4 is only right when one schedule covers the window."""
    single = _review_coverage(epochs=[_epoch([NEW_CRON], None)])
    assert single["expected"]["runs"] == 28
    assert "cadence_change" not in single


def test_high1_an_unreadable_schedule_history_is_loud_and_unverified():
    """No git history means the expectation is not backed by the schedules in force."""
    coverage = nightly.poll_coverage(
        [],
        schedules=_schedules(),
        window_start=REVIEW_START,
        window_end=REVIEW_END,
        now=REVIEW_NOW,
    )
    assert coverage["expected"]["runs"] == 28
    assert coverage["expected"]["schedule_history_available"] is None  # nothing was claimed either way
    assert "cron fire times inside the window (UTC)" in coverage["expected"]["derivation"]
    covered = _clean_coverage(epochs=[_epoch([NEW_CRON], None)])
    assert covered["expected"]["schedule_history_available"] is False
    verdict = _health(covered, _fresh())
    assert verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("schedule history" in reason for reason in verdict["unverified_reasons"])


# The committed report's window (artifacts/cqc-nightly/2026-09-20-report.json)
# and the counts the reviewer verified independently: 107 fires from the
# two-per-hour cron in force until the 2026-09-15 changeover, then 20 from the
# four-a-day cron, 127 due in total.
COMMITTED_WINDOW_START = datetime(2026, 9, 13, 5, 11, 26, tzinfo=UTC)
COMMITTED_WINDOW_END = datetime(2026, 9, 20, 5, 11, 26, tzinfo=UTC)
COMMITTED_EPOCH_FIRES = [107, 20]
COMMITTED_EXPECTED_RUNS = 127


def _independent_fires(cron: str, start: datetime, end: datetime) -> list[datetime]:
    """Enumerate a cron's fire times by scanning the window minute by minute.

    This oracle shares no code with the production parser: the two schedules in
    force are plain minute/hour lists, so scanning the clock and keeping the
    matching minutes (``start`` inclusive, ``end`` exclusive, matching
    ``fires_between``) is independent verification rather than a restatement of
    the code under test.
    """

    def members(field: str, high: int) -> set[int]:
        if field == "*":
            return set(range(high + 1))
        assert all(value.isdigit() for value in field.split(",")), cron
        return {int(value) for value in field.split(",")}

    minute_field, hour_field = cron.split()[:2]
    minutes, hours = members(minute_field, 59), members(hour_field, 23)
    fires: list[datetime] = []
    cursor = start.replace(second=0, microsecond=0)
    while cursor < end:
        if cursor.minute in minutes and cursor.hour in hours and start <= cursor < end:
            fires.append(cursor)
        cursor += timedelta(minutes=1)
    return fires


def test_medium_tests_the_committed_window_has_exact_independent_arithmetic():
    """MEDIUM tests:814: the old test asserted a different 04:37 window, 129 fires,
    loose bounds, and used the production cron parser as its own oracle."""
    epoch_a = _independent_fires(OLD_CRON, COMMITTED_WINDOW_START, REVIEW_CHANGE_AT)
    epoch_b = _independent_fires(NEW_CRON, REVIEW_CHANGE_AT, COMMITTED_WINDOW_END)
    # Independently derived, hardcoded as the expected values.
    assert [len(epoch_a), len(epoch_b)] == COMMITTED_EPOCH_FIRES
    assert epoch_a[0] == datetime(2026, 9, 13, 5, 37, tzinfo=UTC)
    assert epoch_a[-1] == datetime(2026, 9, 15, 10, 37, tzinfo=UTC)
    assert epoch_b[0] == datetime(2026, 9, 15, 18, 7, tzinfo=UTC)
    assert epoch_b[-1] == datetime(2026, 9, 20, 3, 7, tzinfo=UTC)
    fires = epoch_a + epoch_b
    # The parser-based derivation is the second assertion, never the oracle.
    assert len(nightly.parse_cron(OLD_CRON).fires_between(COMMITTED_WINDOW_START, REVIEW_CHANGE_AT)) == 107
    assert len(nightly.parse_cron(NEW_CRON).fires_between(REVIEW_CHANGE_AT, COMMITTED_WINDOW_END)) == 20

    epochs = nightly.schedule_history()
    if not any(epoch.effective_from for epoch in epochs):
        pytest.skip("shallow checkout: the workflow's schedule history is not available")
    missed_everything = nightly.poll_coverage(
        [],
        epochs=epochs,
        window_start=COMMITTED_WINDOW_START,
        window_end=COMMITTED_WINDOW_END,
        now=COMMITTED_WINDOW_END,
    )
    assert missed_everything["expected"]["schedule_history_available"] is True
    assert missed_everything["expected"]["due"] == COMMITTED_EXPECTED_RUNS
    assert sum(row["fires"] for row in missed_everything["expected"]["epochs"]) == COMMITTED_EXPECTED_RUNS
    # An epoch that ended before the window contributes nothing and is not an epoch.
    assert [row["fires"] for row in missed_everything["expected"]["epochs"] if row["fires"]] == COMMITTED_EPOCH_FIRES
    # Exact, not a bound: every committed fire is past the grace window, nothing ran.
    assert missed_everything["missed"]["runs"] == COMMITTED_EXPECTED_RUNS
    assert missed_everything["successful"]["runs"] == 0
    assert missed_everything["delivered_pct"] == 0.0

    # The reviewed report's own ratio falls out of the same arithmetic: 25 of the
    # 127 committed fires attempted and completed is 102 missed and 19.7% delivered.
    attempted = fires[:25]
    partially_run = nightly.poll_coverage(
        [_run(fire) for fire in attempted],
        epochs=epochs,
        window_start=COMMITTED_WINDOW_START,
        window_end=COMMITTED_WINDOW_END,
        now=COMMITTED_WINDOW_END,
        db_statuses={"completed": 25, "partial": 0, "failed": 0, "total": 25},
    )
    assert partially_run["attempted"]["runs"] == 25
    assert partially_run["missed"]["runs"] == 102
    assert partially_run["delivered_pct"] == 19.7
    assert partially_run["expected"]["due"] == COMMITTED_EXPECTED_RUNS

    # ...and the assembled verdict bundle consumes that arithmetic: the committed
    # window is MISMATCHED through build_verdicts, with the exact missed count in
    # the reasons, for both the 102-missed and the fully-missed variants.
    bundle = _bundle(coverage=partially_run, sweep=_sweep_within_sla(), freshness=_fresh())
    assert bundle["pipeline_health"]["verdict"] == nightly.VERDICT_MISMATCHED
    assert any("102 missed tick(s)" in reason for reason in bundle["pipeline_health"]["reasons"])
    missed_bundle = _bundle(coverage=missed_everything, sweep=_sweep_within_sla(), freshness=_fresh())
    assert missed_bundle["pipeline_health"]["verdict"] == nightly.VERDICT_MISMATCHED
    assert any("127 missed tick(s)" in reason for reason in missed_bundle["pipeline_health"]["reasons"])


def test_high2_a_sampled_classification_cannot_produce_matched():
    """HIGH 2a: MATCHED is not ours to claim while the classification is sampled."""
    classification = {
        "coverage": "sampled",
        "selected": 130,
        "population": 188,
        "cap": 130,
        "failures": 2,
        "classes": {"unexplained_source_id_absent_from_db": 3},
    }
    sampled = nightly.reconciliation_inputs_are_complete(DIFF, classification)
    assert any("classification sampled" in problem for problem in sampled)
    assert any("could not be classified" in problem for problem in sampled)
    assert any("unexplained class" in problem for problem in sampled)
    # a complete classification produces no incompleteness reasons...
    assert nightly.reconciliation_inputs_are_complete(DIFF, {"coverage": "full", "classes": {}}) == []
    # ...and only then may the alignment verdict be MATCHED
    incomplete_verdict = nightly.data_alignment_verdict(
        snapshot=FULL_SNAPSHOT,
        diff=DIFF,
        summary=_summary(defect=0, legitimate=0),
        ingested=UP_TO_DATE,
        incompleteness=sampled,
    )
    assert incomplete_verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("sampled" in reason for reason in incomplete_verdict["reasons"])
    complete_verdict = nightly.data_alignment_verdict(
        snapshot=FULL_SNAPSHOT,
        diff=DIFF,
        summary=_summary(defect=0, legitimate=0),
        ingested=UP_TO_DATE,
        incompleteness=[],
    )
    assert complete_verdict["verdict"] == nightly.VERDICT_MATCHED


def test_high2_freshness_promises_must_be_evaluated_to_be_claimed():
    """HIGH 2b: an absent freshness block is unverified, never a stated success."""
    coverage = _clean_coverage()
    assert _health(coverage, None)["verdict"] == nightly.VERDICT_UNVERIFIED
    unevaluated = _fresh(signal={"within_sla": False, "evaluated": False, "age_hours": None, "sla_hours": 16.0})
    assert _health(coverage, unevaluated)["verdict"] == nightly.VERDICT_UNVERIFIED
    beyond = _fresh(signal={"within_sla": False, "evaluated": True, "age_hours": 40.0, "sla_hours": 16.0})
    assert _health(coverage, beyond)["verdict"] == nightly.VERDICT_MISMATCHED
    matched = _health(coverage, _fresh())
    assert matched["verdict"] == nightly.VERDICT_MATCHED
    assert not matched["unverified_reasons"]


def test_high2_a_sweep_that_was_never_estimated_is_not_a_promise_that_held():
    """The same overclaim: MATCHED may not list a promise nobody evaluated."""
    coverage = _clean_coverage()
    verdict = nightly.pipeline_health_verdict(
        coverage=coverage,
        sweep=None,
        freshness=_fresh(),
        observed_sweep=None,
        run_history_status="ok",
        drift_notes=[],
    )
    assert verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("sweep" in reason for reason in verdict["unverified_reasons"])


def test_medium3_a_partial_database_run_is_not_a_complete_poll():
    """MEDIUM 3: poll_cqc_signals.py records 'partial'; GitHub still says success."""
    due = [
        fire
        for fire in _fire_times(_schedules(), WINDOW_START, WINDOW_END)
        if fire <= NOW - nightly.MISSED_GRACE
    ]
    coverage = nightly.poll_coverage(
        [_run(fire) for fire in due],
        schedules=_schedules(),
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        now=NOW,
        db_statuses={"completed": len(due) - 4, "partial": 4, "failed": 0, "total": len(due)},
    )
    assert coverage["missed"]["runs"] == 0 and coverage["failed"]["runs"] == 0
    assert coverage["successful"]["incomplete_runs"] == 4
    assert "partial" in coverage["successful"]["note"]
    verdict = _health(coverage, _fresh())
    assert verdict["verdict"] == nightly.VERDICT_MISMATCHED
    assert any("partial" in reason for reason in verdict["reasons"])


def test_medium4_the_publication_date_is_read_as_a_date_not_a_string():
    """MEDIUM 4: '16 September 2026' is a date the report could not previously read."""
    assert nightly.parse_publication_date("16 September 2026") == "2026-09-16"
    assert nightly.parse_publication_date("16/09/2026") == "2026-09-16"
    assert nightly.parse_publication_date("2026-09-16") == "2026-09-16"
    assert nightly.parse_publication_date("2026-09-16T04:37:00Z") == "2026-09-16"
    assert nightly.parse_publication_date("") is None
    assert nightly.parse_publication_date("not a date") is None
    assert nightly.parse_publication_date(None) is None


def test_medium4_the_mixed_format_comparison_can_no_longer_classify_an_id():
    """The fail-open defect the review found under MEDIUM 4.

    Comparing an ISO registration date with a natural-language publication date
    put ``2026-09-15`` *after* ``16 September 2026`` on the string "2" > "1", so
    the timing class could never be reached.
    """
    assert nightly.timing_order("2026-09-15", "16 September 2026") == -1
    assert nightly.timing_order("2026-09-16", "16 September 2026") == -1
    assert nightly.timing_order("2026-09-17", "16 September 2026") == 1
    assert nightly.timing_order(None, "16 September 2026") is None
    assert nightly.timing_order("2026-09-17", "not a date") is None
    assert (
        nightly.classify_id(
            side="db_active_absent_from_source",
            status="Registered",
            registration_date="2026-09-15",
            deregistration_date=None,
            snapshot_published_at="16 September 2026",
        )
        == "registered_on_or_before_snapshot_but_absent"
    )
    assert (
        nightly.classify_id(
            side="db_active_absent_from_source",
            status="Registered",
            registration_date="2026-09-17",
            deregistration_date=None,
            snapshot_published_at="16 September 2026",
        )
        == "registered_after_snapshot_publication"
    )
    undated = nightly.classify_id(
        side="db_active_absent_from_source",
        status="Registered",
        registration_date=None,
        deregistration_date=None,
        snapshot_published_at="16 September 2026",
    )
    assert undated == "unclassified_publication_date"
    assert undated in nightly.UNEXPLAINED_CLASSES


def test_medium4_cached_classifications_are_re_derived_before_they_are_reused():
    """The review's acceptance test, run against the committed cache.

    The cache labels 60 IDs ``registered_after_snapshot_publication`` under the
    string comparison. Re-derived against the snapshot's own publication date
    ("16 September 2026") only 20 of them really registered after it; the other
    40 registered on or before it and sit in the timing class the broken
    comparison could not reach. The date-independent half of the split - 4
    ``db_inactive_matches_deregistration`` and 67
    ``confirmed_deregistered_still_active_in_db`` - reproduces exactly.
    """
    if not (CACHE_DIR / "divergent-db-active.json").is_file():
        pytest.skip("classification cache is not present in this checkout")
    published = "16 September 2026"
    classes: dict[str, int] = {}
    for name, side, expected_entries in (
        ("divergent-db-active.json", "db_active_absent_from_source", 127),
        ("source-inactive-vs-db.json", "source_present_db_inactive", 61),
    ):
        entries = json.loads((CACHE_DIR / name).read_text(encoding="utf-8"))["classes"]
        assert len(entries) == expected_entries
        for entry in entries.values():
            recomputed = nightly._reclassify_cached_entry(
                entry, side=side, snapshot_published_at=published
            )["class"]
            classes[recomputed] = classes.get(recomputed, 0) + 1
    assert sum(classes.values()) == 188
    assert classes["db_inactive_matches_deregistration"] == 4
    assert classes["db_inactive_but_source_registered"] == 57
    assert classes["confirmed_deregistered_still_active_in_db"] == 67
    assert classes["registered_after_snapshot_publication"] == 20
    assert classes["registered_on_or_before_snapshot_but_absent"] == 40
    assert "unclassified_publication_date" not in classes


def test_medium5_a_cited_checksum_must_match_the_file_the_run_leaves_behind(tmp_path):
    """A cited checksum that does not match the committed file is not evidence.

    ``state.json`` is rewritten by every run, so hashing it before it is rewritten cites
    the previous run's file - exactly the mismatch the reviewer would find next.
    """
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["evidence"] = []  # non-None, so the run recomputes it
    stale = tmp_path / "state.json"
    stale.write_text('{"generated_at": "2026-09-19T04:33:56Z"}', encoding="utf-8")

    report_md = nightly.finalize_outputs(payload, tmp_path, now=REVIEW_END)

    written = json.loads(
        (tmp_path / f"{REVIEW_END:%Y-%m-%d}-report.json").read_text(encoding="utf-8")
    )
    entry = next(e for e in written["evidence"] if e["path"].endswith("state.json"))
    assert entry["present"] is True
    assert entry["sha256"] == hashlib.sha256(stale.read_bytes()).hexdigest()
    assert entry["bytes"] == stale.stat().st_size
    assert entry["sha256"] != json.loads(stale.read_text(encoding="utf-8")).get("generated_at")
    assert report_md.name.endswith("-report.md")


def test_medium5_cited_evidence_is_flagged_when_the_commit_does_not_carry_it(tmp_path):
    """MEDIUM 5: 5dc1759's report cited evidence the reviewed SHA did not contain."""
    out_dir = tmp_path / "cqc-nightly"
    (out_dir / "cache").mkdir(parents=True)
    (out_dir / "cache" / "divergent-db-active.json").write_text('{"classes": {}}', encoding="utf-8")
    index = nightly.evidence_index(out_dir, now=NOW)
    by_suffix = {entry["path"].split("/")[-1]: entry for entry in index}
    cited = by_suffix["divergent-db-active.json"]
    assert cited["present"] is True and cited["sha256"] and cited["bytes"]
    assert cited["checksum_only"] is False
    assert cited["git_tracked"] is False  # a path outside the repository is not committed
    assert by_suffix["directory-snapshot.json"]["checksum_only"] is True
    assert by_suffix["2026-09-20-unrated-classification.json"]["present"] is False
    findings = nightly.findings({"evidence": index})
    assert any(
        "[evidence] cited evidence is not tracked by git" in reason and "divergent-db-active.json" in reason
        for reason in findings
    )
    assert any("[evidence] cited evidence is missing" in reason for reason in findings)
    marked_up = nightly.render({**json.loads(FIXTURE.read_text(encoding="utf-8")), "evidence": index})
    assert "## Evidence index" in marked_up
    assert "divergent-db-active.json" in marked_up


def test_low6_the_change_window_heading_names_both_ends():
    """LOW 6: the heading ended the window at its own start timestamp."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    markdown = nightly.render(payload)
    heading = next(line for line in markdown.splitlines() if line.startswith("## Pipeline runs in the change window"))
    start, end = payload["window_start"], payload["generated_at"]
    assert start in heading and end in heading
    assert heading.index(start) < heading.index(end)
    assert f"{payload['window_hours']}h," in heading


def test_low7_the_historical_336_polls_per_week_figure_is_marked_historical():
    """LOW 7: a 2026-08-10 audit kept stating 336/week as if it were current."""
    audit = REPO_ROOT / "artifacts" / "audits" / "2026-08-10-cqc-database-change-frequency-report.md"
    text = audit.read_text(encoding="utf-8")
    assert "336 polls/seven days" in text  # the historical finding is preserved, not rewritten
    assert "Historical figures — do not read as current (annotated 2026-09-20)" in text
    assert "4 polls/day, 28/week" in text
    assert "Every `336` below is historical." in text
    annotation = text[text.index("Historical figures"):]
    for expression in ("`37 * * * *`", "`7,37 * * * *`", "`7 18,21,0,3 * * *`"):
        assert expression in annotation
    for commit in ("1e7d594", "39fa9a3", "6bc9880"):
        assert commit in annotation


# ---------------------------------------------------------------------------
# round 2: the verdict entry point itself (build_verdicts), not its helpers
# ---------------------------------------------------------------------------
# The first corrective round tested data_alignment_verdict and
# pipeline_health_verdict directly, with fixtures that omitted the completeness
# evidence, so no test ever assembled a verdict bundle and the fail-open paths
# (a missing summary read as "zero defects", missing / available:false coverage
# read as a clean window) survived a green suite. Every test below calls
# nightly.build_verdicts.

_UNSET = object()


def _bundle(
    *,
    summary=_UNSET,
    coverage=_UNSET,
    sweep=_UNSET,
    freshness=_UNSET,
    incompleteness=_UNSET,
    ingested=_UNSET,
    run_history_status="ok",
    drift_notes=(),
):
    """build_verdicts over a window in which every input is present and complete."""
    return nightly.build_verdicts(
        snapshot=FULL_SNAPSHOT,
        diff=DIFF,
        summary=_summary(legitimate=67) if summary is _UNSET else summary,
        ingested=UP_TO_DATE if ingested is _UNSET else ingested,
        coverage=_clean_coverage() if coverage is _UNSET else coverage,
        sweep=_sweep_within_sla() if sweep is _UNSET else sweep,
        observed_sweep=None,
        freshness=_fresh() if freshness is _UNSET else freshness,
        run_history_status=run_history_status,
        drift_notes=list(drift_notes),
        **({} if incompleteness is _UNSET else {"incompleteness": incompleteness}),
    )


def _unavailable_coverage(reason="the GitHub run list could not be read"):
    return nightly.coverage_unavailable(
        reason,
        epochs=_straddling_epochs(),
        window_start=REVIEW_START,
        window_end=REVIEW_END,
        now=REVIEW_NOW,
    )


def test_round2_control_every_present_and_complete_input_is_still_matched():
    """Positive control: MATCHED stays reachable, so the tests below prove the
    missing piece of evidence is what flips the verdict."""
    bundle = _bundle()
    assert bundle["classification_evidence_complete"] is True
    assert bundle["completeness_derived_in_verdict_path"] is True
    assert bundle["data_alignment"]["verdict"] == nightly.VERDICT_MATCHED
    assert bundle["pipeline_health"]["verdict"] == nightly.VERDICT_MATCHED


def test_round2_1_an_absent_classification_summary_is_unverified_in_both_verdicts():
    """HIGH tools:1726: summary=None was read as zero defects and returned MATCHED."""
    bundle = _bundle(summary=None)
    assert bundle["classification_evidence_complete"] is False
    alignment = bundle["data_alignment"]
    assert alignment["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("no classification summary was produced" in reason for reason in alignment["reasons"])
    pipeline = bundle["pipeline_health"]
    assert pipeline["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("classification summary" in reason for reason in pipeline["reasons"])


def test_round2_2_a_sampled_classification_with_an_observed_defect_is_unverified():
    """HIGH tools:1726: a defect over a sampled population returned MISMATCHED."""
    sampled = {**_summary(defect=3), "coverage": "sampled", "selected": 130, "population": 188, "cap": 130}
    bundle = _bundle(summary=sampled)
    assert bundle["classification_evidence_complete"] is False
    alignment = bundle["data_alignment"]
    assert alignment["verdict"] == nightly.VERDICT_UNVERIFIED
    assert alignment["verdict"] != nightly.VERDICT_MISMATCHED
    assert any("coverage is sampled" in reason for reason in alignment["reasons"])
    # Nothing is hidden: the observed defect is still reported, as part of the
    # reason the split is not a complete account of the population.
    assert any("confirmed defect" in reason for reason in alignment["reasons"])
    assert bundle["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED


def test_round2_3_a_failed_or_capped_classification_is_unverified():
    """HIGH tools:1726: a failed or capped classification is a missing measurement."""
    failed = {**_summary(legitimate=1), "failures": 7}
    bundle_failed = _bundle(summary=failed)
    assert bundle_failed["data_alignment"]["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any(
        "could not be classified (CQC API errors)" in reason
        for reason in bundle_failed["data_alignment"]["reasons"]
    )
    assert bundle_failed["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED

    capped = {**_summary(legitimate=1), "coverage": "capped", "selected": 188, "population": 188}
    bundle_capped = _bundle(summary=capped)
    assert bundle_capped["data_alignment"]["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("coverage is capped" in reason for reason in bundle_capped["data_alignment"]["reasons"])
    assert bundle_capped["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED


def test_round2_4_absent_coverage_is_unverified_not_matched():
    """HIGH tools:1777: coverage=None with an ok run history returned MATCHED."""
    bundle = _bundle(coverage=None)
    pipeline = bundle["pipeline_health"]
    assert pipeline["verdict"] == nightly.VERDICT_UNVERIFIED
    assert pipeline["verdict"] != nightly.VERDICT_MATCHED
    assert any("no polling-coverage block" in reason for reason in pipeline["reasons"])
    assert not any("expected cadence met" in reason for reason in pipeline["reasons"])


def test_round2_5_coverage_marked_unavailable_is_unverified_not_matched():
    """HIGH tools:1777: coverage with available:false returned MATCHED."""
    coverage = _unavailable_coverage()
    assert coverage["available"] is False
    bundle = _bundle(coverage=coverage)
    pipeline = bundle["pipeline_health"]
    assert pipeline["verdict"] == nightly.VERDICT_UNVERIFIED
    assert pipeline["verdict"] != nightly.VERDICT_MATCHED
    assert any("poll coverage is unavailable" in reason for reason in pipeline["reasons"])
    assert not any("expected cadence met" in reason for reason in pipeline["reasons"])


def test_round2_6_an_unreadable_schedule_history_is_unverified_with_the_on_disk_fallback(monkeypatch):
    """HIGH tools:1777 (kept passing): an undated, on-disk-derived expectation is
    not evidence, even when every GitHub run in the window succeeded."""
    real_which = nightly.shutil.which
    monkeypatch.setattr(nightly.shutil, "which", lambda name: None if name == "git" else real_which(name))
    epochs = nightly.schedule_history()
    assert len(epochs) == 1 and epochs[0].effective_from is None
    assert "on disk" in epochs[0].source or "disk" in epochs[0].source
    coverage = _clean_coverage(epochs=epochs)
    assert coverage["expected"]["schedule_history_available"] is False
    assert coverage["missed"]["runs"] == 0
    bundle = _bundle(coverage=coverage)
    pipeline = bundle["pipeline_health"]
    assert pipeline["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("could not be established from the workflow's git history" in reason for reason in pipeline["reasons"])
    assert not any("expected cadence met" in reason for reason in pipeline["reasons"])


def test_round2_7_database_partial_polls_are_excluded_from_delivery_and_block_green():
    """MEDIUM tools:831: four DB-partial rows read as 27 successful / 100% delivered."""
    complete = _clean_coverage()
    total = complete["expected"]["due"]
    assert total > 4
    coverage = _clean_coverage(
        db_statuses={"completed": total - 4, "partial": 4, "failed": 0, "total": total}
    )
    successful = coverage["successful"]
    assert successful["workflow_success_runs"] == total
    assert successful["completed_polls"] == total - 4
    assert successful["runs"] == total - 4, "a DB-partial poll is not a completed poll"
    assert successful["partial_runs_excluded"] == 4
    assert successful["incomplete_runs"] == 4
    assert abs(coverage["delivered_pct"] - round((total - 4) / total * 100, 1)) < 0.05
    assert coverage["delivered_pct"] < 100.0
    assert "completed DB polls" in coverage["delivered_basis"]
    # ...while the workflow-conclusion coverage stays what it is: the point is that
    # the two numbers are separated, not that the workflow successes vanished.
    assert coverage["coverage_pct"] == complete["coverage_pct"] == 100.0
    bundle = _bundle(coverage=coverage)
    pipeline = bundle["pipeline_health"]
    assert pipeline["verdict"] == nightly.VERDICT_MISMATCHED
    assert any("recorded 'partial' in the DB" in reason for reason in pipeline["reasons"])


def test_round2_9_epoch_start_dates_use_the_earliest_commit_a_schedule_was_in_force_from():
    """LOW tools:617: the one-hour cron began 2026-08-31, not 2026-09-03."""
    one_hour_commit = "1e7d594c6516f9e1071eddb021b85285972624d0"
    later_identical_commit = "5707021ae397696a683a573f54236c0c1928a466"
    epochs = nightly.schedule_history()
    assert epochs, "a full checkout must expose the workflow file's schedule history"
    starts = [(list(epoch.crons)[0], epoch.effective_from, epoch.commit) for epoch in epochs]
    assert all(effective_from is not None for _, effective_from, _ in starts)
    assert [effective_from for _, effective_from, _ in starts] == sorted(
        effective_from for _, effective_from, _ in starts
    ), "epochs must be built oldest-first"
    # The earliest commit at which each schedule became effective, read from the
    # workflow file's own revision history (git log --format=%H%x09%cI).
    assert starts == [
        ("7,37 * * * *", datetime(2026, 8, 9, 14, 49, 7, tzinfo=UTC), "218f608e09cbb4f3715b8f15959b3460640ab72b"),
        ("37 * * * *", datetime(2026, 8, 31, 13, 48, 47, tzinfo=UTC), one_hour_commit),
        ("7,37 * * * *", datetime(2026, 9, 3, 12, 24, 24, tzinfo=UTC), "39fa9a39d56a042abaa20057d008392706ff21f0"),
        ("7 18,21,0,3 * * *", datetime(2026, 9, 15, 10, 38, 36, tzinfo=UTC), "6bc98802611b5e98fad9410677c1fea1f5fc2209"),
        ("37 18,21,0,3 * * *", datetime(2026, 9, 23, 3, 22, 10, tzinfo=UTC), "12d0584d24a80b7a0f659f07a22cf4bca4105460"),
    ]
    # Regression guard for the reported bug: the identical-run compression used to
    # keep the newest commit in the run (2026-09-03T10:23:23Z).
    one_hour = [row for row in starts if row[0] == "37 * * * *"]
    assert len(one_hour) == 1
    assert one_hour[0][2] == one_hour_commit != later_identical_commit
    assert one_hour[0][1] != datetime(2026, 9, 3, 10, 23, 23, tzinfo=UTC)
    # ...and the verdict path consumes those dated epochs as verified history: the
    # same window a fallback-derived expectation leaves UNVERIFIED (round 2.6)
    # greens only while the in-force schedules are established from git history.
    coverage = _clean_coverage(epochs=epochs)
    assert coverage["expected"]["schedule_history_available"] is True
    assert coverage["expected"]["schedule_history_gaps"] == []
    rows = coverage["expected"]["epochs"]
    assert [row["crons"] for row in rows] == [["7,37 * * * *"], ["7 18,21,0,3 * * *"]]
    assert [row["effective_from"] for row in rows] == [
        "2026-09-03T12:24:24Z",
        "2026-09-15T10:38:36Z",
    ]
    assert [row["commit"] for row in rows] == [
        "39fa9a39d56a042abaa20057d008392706ff21f0",
        "6bc98802611b5e98fad9410677c1fea1f5fc2209",
    ]
    assert sum(row["fires"] for row in rows) == coverage["expected"]["runs"] == 129
    assert coverage["expected"]["due"] == 128 and coverage["expected"]["not_yet_due"] == 1
    bundle = _bundle(coverage=coverage)
    assert bundle["pipeline_health"]["verdict"] == nightly.VERDICT_MATCHED


def test_round2_10_an_ingestion_lag_is_disclosed_and_still_blocks_a_green_verdict():
    """The database lagging a publication is context, not a hole in the
    measurement: the observed defects are still MISMATCHED (and now carry the
    lag in their reasons, where the original path silently dropped it), while a
    lag with nothing unexplained still cannot read as agreement."""
    lagging = {**UP_TO_DATE, "newest_snapshot_covered": False, "latest_covered_published_at": "2026-09-09"}
    bundle = _bundle(summary=_summary(defect=124, legitimate=64), ingested=lagging)
    verdict = bundle["data_alignment"]
    assert verdict["verdict"] == nightly.VERDICT_MISMATCHED
    assert any("one publication behind" in reason for reason in verdict["reasons"])
    assert any("confirmed defect" in reason for reason in verdict["reasons"])

    clean = _bundle(summary=_summary(legitimate=188), ingested=lagging)
    assert clean["data_alignment"]["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("one publication behind" in reason for reason in clean["data_alignment"]["reasons"])


def test_round2_11_a_full_coverage_label_cannot_outrun_its_own_class_counts():
    """The merged summary records the offered population and the classified
    subset as sizes: 'coverage: full' over 180 of 200 IDs is not a complete
    account and must be UNVERIFIED, not MATCHED/MISMATCHED."""
    partial = {**_summary(legitimate=180), "coverage": "full", "population": 200, "classified": 180}
    bundle = _bundle(summary=partial)
    assert bundle["classification_evidence_complete"] is False
    verdict = bundle["data_alignment"]
    assert verdict["verdict"] == nightly.VERDICT_UNVERIFIED
    assert any("only 180 of 200 divergent IDs were classified" in reason for reason in verdict["reasons"])
    assert bundle["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED


def test_round2_12_absent_pipeline_evidence_is_unverified_and_never_green():
    """The evidence a green pipeline verdict rests on has to be *present*: an
    unevaluated sweep, an unevaluated freshness promise, a coverage block whose
    DB cross-check never ran, and a coverage block with no schedule history all
    return UNVERIFIED rather than a bare MATCHED."""
    assert _bundle(sweep=None)["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED

    no_sweep = {**_clean_coverage()}
    no_sweep.pop("successful", None)
    assert _bundle(coverage=no_sweep)["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED

    no_cross_check = json.loads(json.dumps(_clean_coverage()))
    no_cross_check["successful"]["db_cross_checked"] = False
    assert _bundle(coverage=no_cross_check)["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED

    no_history = json.loads(json.dumps(_clean_coverage()))
    no_history["expected"]["schedule_history_available"] = False
    assert _bundle(coverage=no_history)["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED

    assert _bundle(freshness=None)["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED
    assert _bundle(run_history_status="unavailable")["pipeline_health"]["verdict"] == nightly.VERDICT_UNVERIFIED
