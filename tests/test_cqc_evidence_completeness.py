"""Property tests over the evidence bundle: no incomplete bundle may be MATCHED.

Why this file exists
--------------------
Three review rounds each added a guard for one named bad input, and each round
the next reviewer found more inputs that still returned MATCHED while the
evidence needed for that verdict was absent. Guards keyed on the *shape* of the
bad input lose to input shapes nobody enumerated.

The tool now has one manifest-driven evidence-completeness gate: an enumerated
list of named required elements, each with a state (present / absent /
unevaluated / contradictory / unsupported / unqualified aggregate), and
``green_verdict`` refuses to build MATCHED unless every element of that manifest
is present and evaluated. The gate is recorded on the verdict, with the blocking
element named, so a reader of the report can see what was missing.

These tests drive the gate through the verdict path the nightly tool uses, over
bundles built here (fixtures plus the tool's own ``poll_coverage`` and
``summarize_classification``), not through the tool's snapshot/ingest parser, so
an incomplete bundle has to be refused whichever named way it is incomplete.

Every named shape is a *case of the gate*: a small function that removes,
blanks or contradicts one element of an otherwise complete bundle. The same
functions are combined at random in the fuzz test, so unlisted combinations of
listed shapes are covered too.

``python tests/test_cqc_evidence_completeness.py`` prints the shape-by-shape
matrix of verdicts and blocking elements; that matrix is how this file was
compared against the parent commit 72b391c.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "nightly_cqc_db_check.py"
BASE_TESTS_PATH = REPO_ROOT / "tests" / "test_nightly_cqc_db_check.py"

MATCHED = "MATCHED"
ALIGNMENT = "data_alignment"
PIPELINE = "pipeline_health"
DOMAINS = (ALIGNMENT, PIPELINE)


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


nightly = _load_module("nightly_cqc_db_check_property", TOOL_PATH)
base = _load_module("nightly_cqc_db_check_bundle_fixtures", BASE_TESTS_PATH)


# ---------------------------------------------------------------------------
# reading a verdict and the gate recorded on it
# ---------------------------------------------------------------------------
def _gate(verdict: dict, domain: str) -> dict:
    gate = verdict.get("evidence_gate")
    assert gate is not None, (
        f"the {domain} verdict carries no evidence gate, so MATCHED is reachable "
        "without one - the gate result has to be recorded on the verdict"
    )
    assert gate.get("domain") == domain
    return gate


def _blocked_elements(verdict: dict, domain: str) -> set[str]:
    return {row["element"] for row in _gate(verdict, domain).get("blocked_by", [])}


def _assert_domain_refused(bundle: dict, domain: str, *, closed_by: str, shape: str) -> None:
    """The named shape must not reach MATCHED, and the named element must be why."""
    verdict = bundle[domain]
    assert verdict["verdict"] != MATCHED, (
        f"{shape}: {domain} came back {verdict['verdict']}; an incomplete bundle reached "
        "green (" + "; ".join(verdict.get("reasons") or []) + ")"
    )
    gate = _gate(verdict, domain)
    assert gate["complete"] is False
    assert gate["blocked_by"], f"{shape}: {domain} not green, but the gate names no blocking element"
    blocked = {row["element"] for row in gate["blocked_by"]}
    assert closed_by in blocked, (
        f"{shape}: {domain} was refused, but not by {closed_by}: blocked={sorted(blocked)}"
    )
    row = next(entry for entry in gate["blocked_by"] if entry["element"] == closed_by)
    assert row["state"] in nightly.EVIDENCE_STATES, (shape, row["state"])
    assert row["detail"], (shape, row)


def _assert_domain_green(bundle: dict, domain: str) -> None:
    verdict = bundle[domain]
    assert verdict["verdict"] == MATCHED, (
        f"{domain} was refused with a complete bundle: {verdict.get('reasons')}"
    )
    gate = _gate(verdict, domain)
    assert gate["complete"] is True
    assert gate["blocked_by"] == []


# ---------------------------------------------------------------------------
# the complete bundle, and the shape registry
# ---------------------------------------------------------------------------
def _complete_kwargs() -> dict:
    """The bundle the tool is meant to call green: every element present and evaluated.

    Mirrors ``tests/test_nightly_cqc_db_check.py::_bundle`` through the tool's own
    ``build_verdicts``, with every input supplied explicitly so a shape can
    replace exactly one of them.
    """
    return {
        "snapshot": base.FULL_SNAPSHOT,
        "diff": base.DIFF,
        "summary": base._summary(legitimate=67),
        "ingested": base.UP_TO_DATE,
        "coverage": base._clean_coverage(),
        "sweep": base._sweep_within_sla(),
        "observed_sweep": None,
        "freshness": base._fresh(),
        "run_history_status": "ok",
        "drift_notes": [],
        "incompleteness": [],
    }


def _bundle(**overrides) -> dict:
    kwargs = _complete_kwargs()
    kwargs.update(overrides)
    return nightly.build_verdicts(**kwargs)


def _coverage() -> dict:
    return copy.deepcopy(base._clean_coverage())


def _classification_summary(*, fetched: int, reused: int, population: int) -> dict:
    """A full-coverage classification whose classes came from where the counters say."""
    per_id = {f"1-{index}": {"class": "legitimate_timing_or_scope"} for index in range(population)}
    return nightly.summarize_classification(
        {
            "coverage": "full",
            "classes": {"legitimate_timing_or_scope": population},
            "per_id": per_id,
            "fetched": fetched,
            "reused_from_cache": reused,
            "reused_cache_age_hours": {"oldest": 20.0, "newest": 2.0, "ttl": 168.0} if reused else None,
            "failures": 0,
        },
        population_size=population,
    )


def _case_b_coverage() -> dict:
    """128 attempted runs, none of them matching any due fire (the reproduced CASE B)."""
    epochs = base._straddling_epochs()
    stray = []
    for _ in range(128):
        item = base._run(base.REVIEW_START)
        item["created_at"] = base.REVIEW_START
        stray.append(item)
    return nightly.poll_coverage(
        stray,
        epochs=epochs,
        window_start=base.REVIEW_START,
        window_end=base.REVIEW_END,
        now=base.REVIEW_NOW,
        db_statuses={"completed": 128, "partial": 0, "failed": 0, "total": 128},
    )


@dataclasses.dataclass(frozen=True)
class Shape:
    """One named way for a bundle to be incomplete.

    ``mutate`` takes the complete bundle kwargs and returns them made incomplete
    in exactly one named way; ``closed_by`` is the manifest element that has to
    be the one refusing the verdict; ``domain`` is the verdict that is affected.
    """

    key: str
    shape: str
    closes: str
    domain: str
    closed_by: str
    mutate: Callable[[dict], dict]
    affects: tuple[str, ...] = ()

    @property
    def domains(self) -> tuple[str, ...]:
        """Every verdict this shape makes incomplete (some shapes break two)."""
        return self.affects or (self.domain,)

    def bundle(self) -> dict:
        return _bundle(**self.mutate(_complete_kwargs()))


def _m01(kwargs: dict) -> dict:
    """Per-class defect breakdown holds 5 while the aggregate defect count says 0."""
    kwargs["summary"] = {
        **base._summary(legitimate=188),
        "confirmed_defect": 0,
        "defect_classes": {"contradictory_defect": 5},
    }
    return kwargs


def _m02(kwargs: dict) -> dict:
    """128 attempted runs, no run matching a due fire, missed reads 0."""
    kwargs["coverage"] = _case_b_coverage()
    return kwargs


def _m03(kwargs: dict) -> dict:
    """Every class reused from cache, nothing fetched, coverage still 'full'."""
    kwargs["summary"] = _classification_summary(fetched=0, reused=188, population=188)
    return kwargs


def _m04(kwargs: dict) -> dict:
    """No classification summary at all: the identifier-level split was never measured."""
    kwargs["summary"] = None
    return kwargs


def _m05(kwargs: dict) -> dict:
    """Full coverage claimed, 100 of 188 identifiers classified."""
    kwargs["summary"] = {**base._summary(legitimate=188), "coverage": "full", "population": 188, "classified": 100}
    return kwargs


def _m06(kwargs: dict) -> dict:
    """No snapshot publication date, and no ingested-source date to age the promise against."""
    kwargs["snapshot"] = {key: value for key, value in base.FULL_SNAPSHOT.items() if key != "published_at"}
    kwargs["freshness"] = base._fresh(ingested_source={"within_sla": True, "evaluated": True, "age_hours": 20.0})
    return kwargs


def _m07(kwargs: dict) -> dict:
    """The GitHub run history could not be read."""
    kwargs["run_history_status"] = "unavailable"
    return kwargs


def _m08(kwargs: dict) -> dict:
    """Everything valid except the coverage block contradicting its own buckets."""
    coverage = _coverage()
    coverage["consistency"] = {
        **coverage["consistency"],
        "successful_plus_failed_plus_cancelled_plus_in_flight": 99,
    }
    kwargs["coverage"] = coverage
    return kwargs


def _m09(kwargs: dict) -> dict:
    """Per-class defects present, the aggregate defect count absent."""
    kwargs["summary"] = {"coverage": "full", "population": 5, "classified": 5, "defect_classes": {"contradictory_defect": 3}}
    return kwargs


def _m10(kwargs: dict) -> dict:
    """Ingestion state absent, then present but empty."""
    kwargs["ingested"] = {}
    return kwargs


def _m11(kwargs: dict) -> dict:
    """Schedule history flagged available while its gaps list is not empty."""
    coverage = _coverage()
    coverage["expected"] = {
        **coverage["expected"],
        "schedule_history_available": True,
        "schedule_history_gaps": ["2026-09-10T00:00Z..2026-09-11T00:00Z: no workflow revision could be read"],
    }
    kwargs["coverage"] = coverage
    return kwargs


def _m12(kwargs: dict) -> dict:
    """GitHub says 128 succeeded; the DB records 4 of those polls failed."""
    coverage = _coverage()
    coverage["successful"] = {
        **coverage["successful"],
        "db_cross_checked": True,
        "db_recorded_status": {"completed": 124, "partial": 0, "failed": 4, "total": 128},
    }
    kwargs["coverage"] = coverage
    return kwargs


def _m13(kwargs: dict) -> dict:
    """Every scheduled tick cancelled instead of delivered, 0 successes."""
    coverage = _coverage()
    coverage["cancelled"] = {**coverage["cancelled"], "runs": 128}
    coverage["successful"] = {
        **coverage["successful"],
        "runs": 0,
        "workflow_success_runs": 0,
        "db_recorded_status": {"completed": 0, "partial": 0, "failed": 0, "total": 0},
        "completed_polls": 0,
    }
    kwargs["coverage"] = coverage
    return kwargs


def _m14(kwargs: dict) -> dict:
    """The freshness block is present but carries no evaluated verdict."""
    kwargs["freshness"] = {}
    return kwargs


def _m15(kwargs: dict) -> dict:
    """A sweep block that is present and was never evaluated (meets_sla None)."""
    kwargs["sweep"] = {
        "directory_size": 2000,
        "runs_per_week": 28,
        "sweep_size": 1200,
        "full_sweep_days": None,
        "sla_days": 8.0,
        "meets_sla": None,
    }
    return kwargs


def _m16(kwargs: dict) -> dict:
    """An attempted-run count that no run record backs."""
    coverage = _coverage()
    coverage["attempted"] = {
        **coverage["attempted"],
        "runs": 128,
        "distinct_run_ids": 0,
        "runs_without_a_run_identity": 128,
    }
    kwargs["coverage"] = coverage
    return kwargs


SHAPES: tuple[Shape, ...] = (
    Shape(
        "T01",
        "per-class defect breakdown holds 5 while the aggregate defect count says 0",
        "reproduced fail-open A (MATCHED with classification_evidence_complete true)",
        ALIGNMENT,
        "defect_breakdown",
        _m01,
    ),
    Shape(
        "T02",
        "128 attempted runs, none matching any of the 128 due fires, missed reads 0",
        "reproduced fail-open B (MATCHED, reason 'expected cadence met')",
        PIPELINE,
        "fires_matched_to_runs",
        _m02,
    ),
    Shape(
        "T03",
        "classes all reused from cache, fetched 0, coverage still claims full",
        "partial fetch / cache evidence",
        ALIGNMENT,
        "classification_fetch",
        _m03,
    ),
    Shape(
        "T04",
        "no classification summary was produced at all",
        "missing classifications",
        ALIGNMENT,
        "classification_summary",
        _m04,
    ),
    Shape(
        "T05",
        "full coverage claimed while 100 of 188 identifiers were classified",
        "contradictory counts (same category as T01, different element)",
        ALIGNMENT,
        "classification_population",
        _m05,
    ),
    Shape(
        "T06",
        "no snapshot publication date, and no ingested-source date to age the promise against",
        "absent source dates",
        ALIGNMENT,
        "snapshot_publication_date",
        _m06,
        affects=(ALIGNMENT, PIPELINE),
    ),
    Shape(
        "T07",
        "the GitHub run history could not be read",
        "incomplete run history",
        PIPELINE,
        "run_history",
        _m07,
    ),
    Shape(
        "T08",
        "everything valid except a coverage block contradicting its own buckets",
        "mixed valid and invalid evidence",
        PIPELINE,
        "coverage_consistency",
        _m08,
    ),
    Shape(
        "T09",
        "per-class defects present while the aggregate defect count is absent",
        "absent classification fields",
        ALIGNMENT,
        "defect_breakdown",
        _m09,
    ),
    Shape(
        "T10",
        "ingestion state present but empty (and, separately, absent)",
        "absent ingestion evidence",
        ALIGNMENT,
        "ingestion_state",
        _m10,
    ),
    Shape(
        "T11",
        "schedule history flagged available while its gaps list is non-empty",
        "schedule-history gaps",
        PIPELINE,
        "schedule_history",
        _m11,
    ),
    Shape(
        "T12",
        "GitHub says 128 runs succeeded, the DB records 4 of those polls failed",
        "DB-failed polls",
        PIPELINE,
        "db_cross_check",
        _m12,
    ),
    Shape(
        "T13",
        "every scheduled tick cancelled, 0 successes, missed reads 0",
        "fully cancelled schedules",
        PIPELINE,
        "cancelled_ticks",
        _m13,
    ),
    Shape(
        "T14",
        "freshness block present but no evaluated promise inside it",
        "incomplete freshness verdicts",
        PIPELINE,
        "signal_freshness_promise",
        _m14,
    ),
    Shape(
        "T15",
        "sweep block present, never evaluated (meets_sla None)",
        "unevaluated sweep",
        PIPELINE,
        "sweep_promise",
        _m15,
    ),
    Shape(
        "T16",
        "attempted count of 128 with no run identity behind it",
        "the eighth shape of the killed reviewer's set (unnamed in the task text): "
        "an attempted count not backed by a run identity",
        PIPELINE,
        "attempted_runs",
        _m16,
    ),
)

SHAPE_BY_KEY = {shape.key: shape for shape in SHAPES}


# ---------------------------------------------------------------------------
# 0. negative control: a complete bundle is still green
# ---------------------------------------------------------------------------
def test_00_control_a_complete_bundle_is_still_matched():
    """The gate must not make green unreachable: the existing valid input stays green.

    If the gate refuses every input, it is not a gate, it is an outage.
    """
    bundle = _bundle()
    _assert_domain_green(bundle, ALIGNMENT)
    _assert_domain_green(bundle, PIPELINE)
    assert bundle["evidence_completeness"][ALIGNMENT]["complete"] is True
    assert bundle["evidence_completeness"][PIPELINE]["complete"] is True
    assert bundle["classification_evidence_complete"] is True


# ---------------------------------------------------------------------------
# the named shapes: one test per shape, each asserting the blocking element
# ---------------------------------------------------------------------------
def _assert_shape_refused(key: str) -> None:
    shape = SHAPE_BY_KEY[key]
    bundle = shape.bundle()
    _assert_domain_refused(bundle, shape.domain, closed_by=shape.closed_by, shape=f"{key} ({shape.shape})")
    # The other domain is not required to be green, but if it is, it must have
    # passed its own complete gate (checked in test_18).


def test_01_per_class_defects_against_an_aggregate_of_zero():
    """T01: per-class defects 5, aggregate defects 0 - two counts of one thing disagreeing."""
    _assert_shape_refused("T01")


def test_02_due_fires_with_no_matching_run():
    """T02: 128 attempted runs, none matching a due fire, missed reads 0."""
    _assert_shape_refused("T02")


def test_03_classifications_reused_from_cache_and_nothing_fetched():
    """T03: coverage is population coverage, so cached classes can look like a measurement."""
    _assert_shape_refused("T03")


def test_04_missing_classifications():
    """T04: no classification summary, so the split was never measured."""
    _assert_shape_refused("T04")


def test_05_contradictory_counts_population_against_classified():
    """T05: full coverage claimed while a third of the population was never classified."""
    _assert_shape_refused("T05")


def test_06_absent_source_dates():
    """T06: the snapshot date is absent and the ingested-source date is absent."""
    _assert_shape_refused("T06")


def test_07_incomplete_run_history():
    """T07: the run history could not be read, so nothing is known about the polls."""
    _assert_shape_refused("T07")


def test_08_mixed_valid_and_invalid_evidence():
    """T08: one contradiction inside otherwise valid, evaluated evidence."""
    _assert_shape_refused("T08")


def test_09_absent_classification_fields():
    """T09: a per-class breakdown with no aggregate to certify it."""
    _assert_shape_refused("T09")


def test_10_absent_ingestion_evidence():
    """T10: an empty ingestion state, and an absent one."""
    _assert_shape_refused("T10")
    _assert_domain_refused(
        _bundle(ingested=None), ALIGNMENT, closed_by="ingestion_state", shape="T10 (absent ingestion evidence)"
    )


def test_11_schedule_history_gaps():
    """T11: the schedules in force are flagged available while a gap is recorded."""
    _assert_shape_refused("T11")


def test_12_db_failed_polls():
    """T12: the DB records failing polls that GitHub counts as successes."""
    _assert_shape_refused("T12")


def test_13_fully_cancelled_schedules():
    """T13: attempted is not delivered - every tick cancelled, nothing delivered."""
    _assert_shape_refused("T13")


def test_14_incomplete_freshness_verdicts():
    """T14: one shape in three spellings - empty block, absent block, never evaluated."""
    _assert_shape_refused("T14")
    for label, freshness in (
        ("absent block", None),
        ("never evaluated", {"signal": {"evaluated": False, "within_sla": True, "age_hours": 2.0}}),
    ):
        bundle = _bundle(freshness=freshness)
        verdict = bundle[PIPELINE]
        assert verdict["verdict"] != MATCHED, f"T14 ({label}): pipeline came back {verdict['verdict']}"
        assert verdict.get("evidence_gate") is not None, f"T14 ({label}): no gate recorded"
        assert verdict["evidence_gate"]["complete"] is False, f"T14 ({label}): gate claims complete"
        assert "signal_freshness_promise" in _blocked_elements(verdict, PIPELINE), label


def test_15_unevaluated_sweep():
    """T15: a present sweep block that was never evaluated."""
    _assert_shape_refused("T15")


def test_16_attempted_runs_without_a_run_identity():
    """T16: an attempted count that no run record backs."""
    _assert_shape_refused("T16")


# ---------------------------------------------------------------------------
# the gate itself
# ---------------------------------------------------------------------------
def test_17_every_manifest_element_is_evaluated_and_named_on_every_verdict():
    """The requirement is enumerated data: a named element with a state, per verdict."""
    for domain in DOMAINS:
        expected = [name for name, _ in nightly.evidence_requirements(domain)]
        assert expected, domain
        bundle = _bundle()
        gate = bundle[domain]["evidence_gate"]
        assert gate["required_elements"] == expected, domain
        assert [row["element"] for row in gate["elements"]] == expected, domain
        assert all(row["state"] in nightly.EVIDENCE_STATES for row in gate["elements"])
        assert all(row["required_for"] for row in gate["elements"])
        assert sorted(gate["required_for"]) == sorted(expected)
        assert gate["complete"] is True and gate["blocked_by"] == []
        # The same manifest is reported at the top level of the bundle, so a
        # reader of the report JSON gets it whether they read the verdict or the
        # bundle summary.
        summary = bundle["evidence_completeness"][domain]
        assert summary["elements"] == expected
        assert summary["blocked_by"] == []
        assert summary["complete"] is True
        assert summary["verdict"] == bundle[domain]["verdict"]
        # ...and when an element is blocked, both places name it.
        blocked = _bundle(summary=None)
        blocked_name = "classification_summary" if domain == ALIGNMENT else "classification_output"
        assert blocked_name in blocked["evidence_completeness"][domain]["blocked_by"]
        assert blocked_name in {
            row["element"] for row in blocked[domain]["evidence_gate"]["blocked_by"]
        }


def test_18_no_verdict_is_matched_with_an_incomplete_or_absent_gate():
    """Falsification in the other direction: MATCHED implies a complete gate.

    This is the whole of Option A as a property - green is a consequence of the
    gate, not a path around it - checked over every bundle this file builds.
    """
    bundles = [(_bundle(), "CONTROL complete bundle")]
    bundles += [(shape.bundle(), shape.key) for shape in SHAPES]
    for bundle, label in bundles:
        for domain in DOMAINS:
            verdict = bundle[domain]
            if verdict["verdict"] != MATCHED:
                continue
            gate = verdict.get("evidence_gate")
            assert gate is not None and gate["complete"] is True, f"{label}: MATCHED without a complete {domain} gate"


def test_19_fuzz_and_unlisted_combinations_cannot_reach_green():
    """Unlisted inputs cannot reach green by being unlisted.

    Each named shape is a mutation of a complete bundle that breaks exactly one
    manifest element. Applying one to four of them at random produces
    combinations nobody enumerated - including incomplete bundles whose
    individual symptoms would have cancelled out under per-shape guards. None
    may be MATCHED.
    """
    rng = random.Random(20260920)
    iterations = 200
    for iteration in range(iterations):
        chosen = rng.sample(SHAPES, rng.randint(1, 4))
        kwargs = _complete_kwargs()
        for shape in chosen:
            kwargs = shape.mutate(kwargs)
        bundle = _bundle(**kwargs)
        label = "+".join(shape.key for shape in chosen)
        affected = {domain for shape in chosen for domain in shape.domains}
        for domain in DOMAINS:
            verdict = bundle[domain]
            if domain in affected:
                assert verdict["verdict"] != MATCHED, (
                    f"iteration {iteration} ({label}): {domain} reached MATCHED with an incomplete bundle"
                )
                gate = _gate(verdict, domain)
                assert gate["blocked_by"], f"iteration {iteration} ({label}): {domain} refused with no blocking element"
            elif verdict["verdict"] == MATCHED:
                # A domain no mutation touched may stay green - but only through
                # its own complete gate.
                gate = _gate(verdict, domain)
                assert gate["complete"] is True, f"iteration {iteration} ({label}): {domain} green without a complete gate"


def test_20_the_registry_covers_every_named_shape_once():
    """Guard against a shape being dropped, renamed, or silently duplicated."""
    keys = [shape.key for shape in SHAPES]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys)) == 16
    for shape in SHAPES:
        assert shape.bundle() is not None
        assert shape.closes and shape.shape


# ---------------------------------------------------------------------------
# diagnostic matrix (not an assertion): python tests/test_cqc_evidence_completeness.py
# ---------------------------------------------------------------------------
def shape_matrix() -> list[dict]:
    rows = []
    control = _bundle()
    rows.append(
        {
            "shape": "CONTROL complete bundle",
            **{
                domain: {
                    "verdict": control[domain]["verdict"],
                    "gate_complete": (control[domain].get("evidence_gate") or {}).get("complete"),
                    "blocked_by": [],
                }
                for domain in DOMAINS
            },
        }
    )
    for shape in SHAPES:
        bundle = shape.bundle()
        row = {"shape": f"{shape.key} {shape.shape}"}
        for domain in DOMAINS:
            verdict = bundle[domain]
            gate = verdict.get("evidence_gate")
            row[domain] = {
                "verdict": verdict["verdict"],
                "gate_complete": gate["complete"] if gate else None,
                "blocked_by": sorted(_blocked_elements(verdict, domain)) if gate else None,
            }
        rows.append(row)
    return rows


if __name__ == "__main__":  # pragma: no cover - diagnostic, not an assertion
    matrix = shape_matrix()
    print(json.dumps(matrix, indent=1))
    # A shape is fail-open when the verdict it targets still reads MATCHED. The
    # other domain is untouched by a single-domain shape and may legitimately
    # stay green, so the summary is scoped to the targeted (and, for the
    # two-domain shapes, every affected) verdict.
    still_green = []
    for shape, row in zip(SHAPES, matrix[1:], strict=False):
        for domain in shape.domains:
            if row[domain]["verdict"] == MATCHED:
                still_green.append(f"{row['shape']} -> {domain}")
    print("TARGETED VERDICTS THAT STILL REACH MATCHED:", json.dumps(still_green, indent=1))
    print(f"fail-open shapes: {len(still_green)} of {sum(len(s.domains) for s in SHAPES)} targeted verdicts")
