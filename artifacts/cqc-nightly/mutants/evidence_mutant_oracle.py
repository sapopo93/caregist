#!/usr/bin/env python3
"""Adversarial mutants for the nightly CQC evidence-completeness gate.

This is deliberately not a product test helper.  It imports the real nightly
tool from this worktree, sends complete and mutated evidence bundles through
``build_verdicts``, and reports every fail-open input without stopping at the
first one.

Exit status is 0 only when the negative control reaches MATCHED and every
mutant is blocked with at least one named evidence element.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "nightly_cqc_db_check.py"
MATCHED = "MATCHED"
ALIGNMENT = "data_alignment"
PIPELINE = "pipeline_health"


def _load_real_tool() -> Any:
    spec = importlib.util.spec_from_file_location("nightly_cqc_db_check_mutant_target", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import real gate from {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


nightly = _load_real_tool()


def _coverage() -> dict[str, Any]:
    """Small, internally consistent pipeline-health measurement."""
    return {
        "available": True,
        "expected": {
            "runs": 4,
            "due": 4,
            "not_yet_due": 0,
            "epochs": [{"crons": ["7 0,6,12,18 * * *"], "fires": 4}],
            "schedule_history_available": True,
            "schedule_history_gaps": [],
            "derivation": "four fires from the dated schedule epoch",
        },
        "attempted": {
            "runs": 4,
            "distinct_run_ids": 4,
            "runs_without_a_run_identity": 0,
        },
        "successful": {
            "runs": 4,
            "workflow_success_runs": 4,
            "db_cross_checked": True,
            "db_recorded_status": {"completed": 4, "partial": 0, "failed": 0, "total": 4},
            "completed_polls": 4,
            "incomplete_runs": 0,
        },
        "failed": {"runs": 0, "by_conclusion": {}},
        "cancelled": {"runs": 0},
        "in_flight": {"runs": 0},
        "missed": {"runs": 0, "fires": [], "definition": "due fires minus attempted runs"},
        "fires_without_a_matching_run": {"runs": 0, "definition": "due fires without a run record"},
        "consistency": {
            "successful_plus_failed_plus_cancelled_plus_in_flight": 4,
            "attempted": 4,
            "due_plus_not_yet_due": 4,
            "expected": 4,
        },
    }


def _summary() -> dict[str, Any]:
    """Ten source-only identifiers, all classified as legitimate."""
    return {
        "confirmed_defect": 0,
        "unexplained": 0,
        "legitimate_timing_or_scope": 10,
        "defect_classes": {},
        "unexplained_classes": {},
        "legitimate_classes": {"registered_after_snapshot_publication": 10},
        "classes": {"registered_after_snapshot_publication": 10},
        "coverage": "full",
        "population": 10,
        "classified": 10,
        "fetched": 10,
        "reused_from_cache": 0,
        "failures": 0,
        "source": "live CQC API location detail",
    }


def _complete_kwargs() -> dict[str, Any]:
    return {
        "snapshot": {
            "coverage": "full",
            "published_at": "2026-09-16",
            "sha256": "a" * 64,
            "checksum_verified": True,
            "complete": True,
            "identity_from_cache": False,
            "entity_count": 100,
        },
        "diff": {
            "overlap": 90,
            "only_in_db_active": [],
            "only_in_source": [f"SRC-{number:02d}" for number in range(10)],
        },
        "summary": _summary(),
        "ingested": {
            "newest_snapshot_covered": True,
            "latest_covered_published_at": "2026-09-16",
        },
        "coverage": _coverage(),
        "sweep": {
            "directory_size": 100,
            "runs_per_week": 28,
            "sweep_size": 25,
            "full_sweep_days": 1.0,
            "sla_days": 8.0,
            "meets_sla": True,
            "min_runs_per_week_for_sla": 1,
            "arithmetic": "100 / (28 x 25) = 1.0 day after rounding",
        },
        "observed_sweep": None,
        "freshness": {
            "signal": {
                "within_sla": True,
                "evaluated": True,
                "age_hours": 2.0,
                "sla_hours": 16.0,
            },
            "ingested_source": {
                "within_sla": True,
                "evaluated": True,
                "age_hours": 96.0,
                "sla_hours": 192.0,
                "published_at": "2026-09-16",
            },
        },
        "run_history_status": "ok",
        "drift_notes": [],
        "incompleteness": [],
    }


def _build(kwargs: dict[str, Any]) -> dict[str, Any]:
    return nightly.build_verdicts(**kwargs)


def _set(path: str, value: Any) -> Callable[[dict[str, Any]], None]:
    keys = path.split(".")

    def mutate(bundle: dict[str, Any]) -> None:
        target = bundle
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value

    return mutate


def _delete(path: str) -> Callable[[dict[str, Any]], None]:
    keys = path.split(".")

    def mutate(bundle: dict[str, Any]) -> None:
        target = bundle
        for key in keys[:-1]:
            target = target[key]
        target.pop(keys[-1], None)

    return mutate


def _measurement(*, value: Any, source: str, observed_at: str, derivation: str) -> dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "observed_at": observed_at,
        "derivation": derivation,
    }


@dataclass(frozen=True)
class Mutant:
    ident: str
    family: str
    domain: str
    detail: str
    mutate: Callable[[dict[str, Any]], None]
    expected_blocking: tuple[str, ...] = ()


def _mutate_unmatched_127(bundle: dict[str, Any]) -> None:
    coverage = bundle["coverage"]
    coverage["expected"].update(
        runs=127,
        due=127,
        not_yet_due=0,
        epochs=[{"crons": ["fixture"], "fires": 127}],
    )
    coverage["attempted"].update(runs=127, distinct_run_ids=127)
    coverage["successful"].update(
        runs=127,
        workflow_success_runs=127,
        completed_polls=127,
        db_recorded_status={"completed": 127, "partial": 0, "failed": 0, "total": 127},
    )
    coverage["fires_without_a_matching_run"]["runs"] = 127
    coverage["consistency"].update(
        successful_plus_failed_plus_cancelled_plus_in_flight=127,
        attempted=127,
        due_plus_not_yet_due=127,
        expected=127,
    )


def _mutate_cancelled_counted_as_fired(bundle: dict[str, Any]) -> None:
    coverage = bundle["coverage"]
    coverage["expected"].update(runs=1, due=1, not_yet_due=0, epochs=[{"crons": ["fixture"], "fires": 1}])
    coverage["attempted"].update(runs=1, distinct_run_ids=1)
    coverage["successful"].update(
        runs=0,
        workflow_success_runs=0,
        completed_polls=0,
        db_recorded_status={"completed": 0, "partial": 0, "failed": 0, "total": 0},
    )
    coverage["cancelled"]["runs"] = 1
    coverage["consistency"].update(
        successful_plus_failed_plus_cancelled_plus_in_flight=1,
        attempted=1,
        due_plus_not_yet_due=1,
        expected=1,
    )


def _mutate_db_failure(bundle: dict[str, Any]) -> None:
    bundle["coverage"]["successful"]["db_recorded_status"] = {
        "completed": 3,
        "partial": 0,
        "failed": 1,
        "total": 4,
    }


def _mutate_db_gh_disagreement(bundle: dict[str, Any]) -> None:
    bundle["coverage"]["successful"]["db_recorded_status"] = {
        "completed": 3,
        "partial": 0,
        "failed": 0,
        "total": 3,
    }


def _mutate_provenance(
    path: str, *, value: Any, source: str, observed_at: str, derivation: str
) -> Callable[[dict[str, Any]], None]:
    keys = path.split(".")

    def mutate(bundle: dict[str, Any]) -> None:
        target = bundle
        for key in keys:
            target = target[key]
        target["measurement"] = _measurement(
            value=value,
            source=source,
            observed_at=observed_at,
            derivation=derivation,
        )

    return mutate


MUTANTS: tuple[Mutant, ...] = (
    # 1. Boolean values passed where actual measurements are required.
    Mutant("M01", "boolean-as-measurement", ALIGNMENT, "snapshot entity_count=True", _set("snapshot.entity_count", True), ("snapshot_population",)),
    Mutant("M02", "boolean-as-measurement", ALIGNMENT, "classification population=True", _set("summary.population", True), ("classification_population",)),
    Mutant("M03", "boolean-as-measurement", PIPELINE, "expected run count=True", _set("coverage.expected.runs", True), ("expected_fires",)),
    Mutant("M04", "boolean-as-measurement", PIPELINE, "signal measurement replaced by bare True", _set("freshness.signal", True), ("signal_freshness_promise",)),
    Mutant("M05", "boolean-as-measurement", ALIGNMENT, "aggregate defect count=True", _set("summary.confirmed_defect", True), ("defect_breakdown",)),
    Mutant("M06", "boolean-as-measurement", PIPELINE, "completed poll count=True", _set("coverage.successful.completed_polls", True), ("delivered_polls",)),

    # 2. Counts and totals disagree while each individual value looks plausible.
    Mutant("M07", "count-total-inconsistency", ALIGNMENT, "classified 68 of population 67", lambda b: (b["summary"].update(population=67, classified=68, fetched=68)), ("classification_population",)),
    Mutant("M08", "count-total-inconsistency", ALIGNMENT, "legitimate class aggregate is 999 for a population of 10", _set("summary.legitimate_timing_or_scope", 999), ("classification_population",)),
    Mutant("M09", "count-total-inconsistency", ALIGNMENT, "aggregate class totals sum to 9 while classified is 10", _set("summary.legitimate_timing_or_scope", 9), ("classification_population",)),
    Mutant("M10", "count-total-inconsistency", ALIGNMENT, "per-class classes sum to 11 while population is 10", _set("summary.classes.registered_after_snapshot_publication", 11), ("classification_population",)),
    Mutant("M11", "count-total-inconsistency", ALIGNMENT, "zero population with one classified identifier", lambda b: b["summary"].update(population=0, classified=1, fetched=1, legitimate_timing_or_scope=1, classes={"registered_after_snapshot_publication": 1}, legitimate_classes={"registered_after_snapshot_publication": 1}), ("classification_population",)),
    Mutant("M12", "count-total-inconsistency", ALIGNMENT, "snapshot population 99 but diff accounts for 100", _set("snapshot.entity_count", 99), ("snapshot_population", "identifier_diff")),

    # 3. Freshness conclusions with the actual comparison missing.
    Mutant("M13", "freshness-without-measurement", PIPELINE, "signal has no age_hours", _delete("freshness.signal.age_hours"), ("signal_freshness_promise",)),
    Mutant("M14", "freshness-without-measurement", PIPELINE, "signal has no sla_hours", _delete("freshness.signal.sla_hours"), ("signal_freshness_promise",)),
    Mutant("M15", "freshness-without-measurement", PIPELINE, "signal says evaluated but comparison is unstated", _delete("freshness.signal.within_sla"), ("signal_freshness_promise",)),
    Mutant("M16", "freshness-without-measurement", PIPELINE, "source has no age_hours", _delete("freshness.ingested_source.age_hours"), ("source_freshness_promise",)),
    Mutant("M17", "freshness-without-measurement", PIPELINE, "source has no sla_hours", _delete("freshness.ingested_source.sla_hours"), ("source_freshness_promise",)),
    Mutant("M18", "freshness-without-measurement", PIPELINE, "source says evaluated but comparison is unstated", _delete("freshness.ingested_source.within_sla"), ("source_freshness_promise",)),

    # 4. A checksum token exists, but nobody affirmatively verified it.
    Mutant("M19", "unverified-checksum", ALIGNMENT, "valid-looking token with verification outcome absent", _delete("snapshot.checksum_verified"), ("snapshot_identity",)),
    Mutant("M20", "unverified-checksum", ALIGNMENT, "valid-looking token with verification outcome None", _set("snapshot.checksum_verified", None), ("snapshot_identity",)),
    Mutant("M21", "unverified-checksum", ALIGNMENT, "valid-looking token with empty verification outcome", _set("snapshot.checksum_verified", ""), ("snapshot_identity",)),
    Mutant("M22", "unverified-checksum", ALIGNMENT, "non-empty token marked unverified as text", lambda b: b["snapshot"].update(sha256="not-a-checksum", checksum_verified="unverified"), ("snapshot_identity",)),

    # 5. Well-formed measurement objects whose provenance cannot support them.
    Mutant("M23", "provenance-layer", ALIGNMENT, "entity count is a fabricated constant", _mutate_provenance("snapshot", value=100, source="operator literal", observed_at="2026-09-20T04:00:00Z", derivation="constant 100"), ("snapshot_population",)),
    Mutant("M24", "provenance-layer", ALIGNMENT, "classification measurement predates its attributed snapshot", _mutate_provenance("summary", value=10, source="CQC API", observed_at="2026-09-01T00:00:00Z", derivation="count response rows for snapshot 2026-09-16"), ("classification_summary",)),
    Mutant("M25", "provenance-layer", ALIGNMENT, "classification value copied from a different element", _mutate_provenance("summary", value=10, source="snapshot.entity_count", observed_at="2026-09-20T04:00:00Z", derivation="copy another element then relabel"), ("classification_population",)),
    Mutant("M26", "provenance-layer", PIPELINE, "signal age attributed to workflow YAML, which has no observation timestamp", _mutate_provenance("freshness.signal", value=2.0, source=".github/workflows/cqc-signal-poll.yml", observed_at="2026-09-20T04:00:00Z", derivation="subtract latest signal time from report time"), ("signal_freshness_promise",)),
    Mutant("M27", "provenance-layer", PIPELINE, "completed-poll value copied from expected fires", _mutate_provenance("coverage.successful", value=4, source="coverage.expected.runs", observed_at="2026-09-20T04:00:00Z", derivation="copy expected rather than count DB completions"), ("delivered_polls", "db_cross_check")),
    Mutant("M28", "provenance-layer", ALIGNMENT, "snapshot checksum attributed to a source incapable of producing file bytes", _mutate_provenance("snapshot", value="a" * 64, source="workflow cron expression", observed_at="2026-09-20T04:00:00Z", derivation="label cron text as snapshot sha256"), ("snapshot_identity",)),

    # The eight previously known attack shapes, kept explicit even where a
    # family above probes a related invariant.
    Mutant("M29", "count-total-inconsistency", ALIGNMENT, "per-class defect breakdown nonzero while aggregate says zero", _set("summary.defect_classes", {"confirmed_deregistered_still_active_in_db": 5}), ("defect_breakdown",)),
    Mutant("M30", "count-total-inconsistency", PIPELINE, "pipeline health with 127 unmatched due fires and missed zero", _mutate_unmatched_127, ("fires_matched_to_runs", "missed_ticks")),
    Mutant("M31", "provenance-layer", ALIGNMENT, "cache-only classification with fetched zero across full population", lambda b: b["summary"].update(fetched=0, reused_from_cache=10), ("classification_fetch",)),
    Mutant("M32", "freshness-without-measurement", ALIGNMENT, "absent ingestion evidence treated as current", _set("ingested", None), ("ingestion_state",)),
    Mutant("M33", "count-total-inconsistency", PIPELINE, "cancelled schedule counted as fired", _mutate_cancelled_counted_as_fired, ("cancelled_ticks", "delivered_polls")),
    Mutant("M34", "count-total-inconsistency", PIPELINE, "DB failure not reflected in GitHub failed count", _mutate_db_failure, ("db_cross_check",)),
    Mutant("M35", "count-total-inconsistency", PIPELINE, "DB and GitHub run records disagree without a failed DB status", _mutate_db_gh_disagreement, ("db_cross_check", "delivered_polls")),
    Mutant("M36", "provenance-layer", PIPELINE, "attempted runs have no identity", lambda b: b["coverage"]["attempted"].update(distinct_run_ids=0, runs_without_a_run_identity=4), ("attempted_runs",)),
)


def _blocked_rows(verdict: dict[str, Any]) -> list[dict[str, Any]]:
    gate = verdict.get("evidence_gate")
    if not isinstance(gate, dict):
        return []
    rows = gate.get("blocked_by")
    return rows if isinstance(rows, list) else []


def _exercise(mutant: Mutant) -> bool:
    kwargs = copy.deepcopy(_complete_kwargs())
    mutant.mutate(kwargs)
    bundle = _build(kwargs)
    verdict = bundle[mutant.domain]
    blocked = _blocked_rows(verdict)
    try:
        assert verdict.get("verdict") != MATCHED
        assert blocked
        assert all(row.get("element") and row.get("detail") for row in blocked)
        if mutant.expected_blocking:
            names = {row["element"] for row in blocked}
            assert names.intersection(mutant.expected_blocking)
    except AssertionError:
        reason = mutant.detail.replace(" ", "_")
        print(f"{mutant.ident} STATUS=ESCAPED family={mutant.family} detail={reason}")
        return False
    names = ",".join(row["element"] for row in blocked)
    print(f"{mutant.ident} STATUS=BLOCKED family={mutant.family} blocking={names}")
    return True


def main() -> int:
    control = _build(copy.deepcopy(_complete_kwargs()))
    alignment_control = control[ALIGNMENT].get("verdict")
    pipeline_control = control[PIPELINE].get("verdict")
    control_ok = alignment_control == MATCHED and pipeline_control == MATCHED
    control_status = "MATCHED" if control_ok else "FAILED"
    print(
        "CONTROL "
        f"STATUS={control_status} alignment={alignment_control} pipeline={pipeline_control}"
    )

    blocked = sum(1 for mutant in MUTANTS if _exercise(mutant))
    escaped = len(MUTANTS) - blocked
    print(
        f"SUMMARY mutants={len(MUTANTS)} blocked={blocked} escaped={escaped} "
        f"negative_control={control_status}"
    )
    return 0 if control_ok and escaped == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
