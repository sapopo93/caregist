#!/usr/bin/env python3
"""Nightly off-peak CQC report: data alignment and pipeline health, separately.

Design rules, each one written because an earlier nightly report broke it:

1.  **Cadence comes from the workflow, never from memory.** ``expected`` polling
    coverage is derived by parsing the cron in
    ``.github/workflows/cqc-signal-poll.yml``. A stale constant (48/day, i.e.
    336/week) produced a permanent, false shortfall in every report published
    after the schedule moved to 4/day.
2.  **Every number is attributed.** Poll counts say whether they came from
    GitHub Actions (``gh run list``) or from the DB (``pipeline_runs``), and the
    two are reconciled on the page instead of being blended.
3.  **Not-yet-due is not missed.** Fires still inside the grace window are
    ``not_yet_due``; coverage is never claimed for a period that has not
    elapsed.
4.  **Alignment is identifier-level**, against the newest snapshot we can
    validate, with a bounded, resumable fetch (caps are env-overridable) and
    every result labelled ``full`` or ``sampled``. A sample never implies full
    coverage.
5.  **Thresholds are the documented ones** (``api/services/pipeline_health.py``),
    cited verbatim and never loosened here.
6.  **Rating-event completeness is a numerator over a denominator, per window**,
    sentinel/representation churn is its own class, and unresolved events are
    excluded from customer-facing movement claims.
7.  **Refresh churn is never source change.** A rewritten row is refresh
    activity; a change is an event in ``trusted_event_ledger``.

Verdict vocabulary (both verdicts are reported independently):

* ``MATCHED`` - identifier-level reconciliation against the latest available
  validated snapshot found no unexplained differences within the stated scope.
* ``MISMATCHED`` - unexplained differences found.
* ``UNVERIFIED`` - reconciliation is stale, incomplete, failed, or has not
  covered the newest snapshot.

Read-only: every DB session is readonly + autocommit. No writes, no push.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNAL_POLL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "cqc-signal-poll.yml"
RECONCILIATION_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "cqc-reconciliation.yml"
PIPELINE_HEALTH_SOURCE = "api/services/pipeline_health.py"

REPORT_VERSION = 3
VERDICT_MATCHED = "MATCHED"
VERDICT_MISMATCHED = "MISMATCHED"
VERDICT_UNVERIFIED = "UNVERIFIED"
VERDICT_VOCABULARY = {
    VERDICT_MATCHED: "identifier-level reconciliation against the latest available validated snapshot "
    "found no unexplained differences within the stated scope",
    VERDICT_MISMATCHED: "unexplained differences found",
    VERDICT_UNVERIFIED: "reconciliation is stale, incomplete, failed, or has not covered the newest snapshot",
}

# ---------------------------------------------------------------------------
# Documented thresholds. These are the product promises; do NOT loosen them
# here. Sources are cited in the report next to every comparison.
# ---------------------------------------------------------------------------
FRESHNESS_SLA = timedelta(days=8)  # SOURCE_FRESHNESS_SLA in api/services/pipeline_health.py
FRESHNESS_SLA_CITATION = (
    f"SOURCE_FRESHNESS_SLA = timedelta(days=8) ({PIPELINE_HEALTH_SOURCE}) - "
    "CQC publishes the directory weekly; 8 days is the documented customer-facing promise"
)
SIGNAL_POLL_FRESHNESS_SLA = timedelta(hours=16)  # SIGNAL_POLL_FRESHNESS_SLA in api/services/pipeline_health.py
SIGNAL_POLL_FRESHNESS_CITATION = f"SIGNAL_POLL_FRESHNESS_SLA = timedelta(hours=16) ({PIPELINE_HEALTH_SOURCE})"

# ---------------------------------------------------------------------------
# Cadence single source of truth. These constants are only a fallback for the
# case where the workflow file cannot be read; a test asserts they agree with
# the workflow, and main() reports drift loudly when they stop agreeing.
# ---------------------------------------------------------------------------
WORKFLOW_CRON_FALLBACK = "7 18,21,0,3 * * *"
WORKFLOW_SWEEP_SIZE_FALLBACK = 1200
CADENCE_SOURCES = {
    "workflow": "parsed from .github/workflows/cqc-signal-poll.yml",
    "fallback": "named fallback constant (workflow file unreadable)",
}

COVERAGE_WINDOW = timedelta(days=7)
MISSED_GRACE = timedelta(minutes=90)
FIRE_MATCH_WINDOW = timedelta(hours=4)

SNAPSHOT_MAX_BYTES_DEFAULT = 64 * 1024 * 1024
SNAPSHOT_MAX_IDS_DEFAULT = 200_000
SNAPSHOT_CACHE_TTL = timedelta(hours=12)
API_CLASSIFY_MAX_DEFAULT = 250
API_CLASSIFY_TTL = timedelta(days=7)
API_CLASSIFY_SLEEP_DEFAULT = 0.1
API_ATTEST_MAX_BYTES = 8 * 1024 * 1024
GH_TIMEOUT_DEFAULT = 90

LOCATION_ID_COLUMN = "CQC Location ID (for office use only)"
RATING_SENTINEL_VALUES = (
    "Inspected but not rated",
    "No published rating",
    "Insufficient evidence to rate",
)
OLD_VALUE_SENTINELS = ("Not Yet Inspected",)

FAILED_CONCLUSIONS = frozenset({"failure", "timed_out", "startup_failure"})
NON_TERMINAL_CONCLUSIONS = frozenset(
    {"", "pending", "queued", "in_progress", "requested", "waiting", "stale", "startup_failure_pending"}
)
SUCCESSFUL_CONCLUSION = "success"
CANCELLED_CONCLUSION = "cancelled"

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "cqc-nightly"
UNRATED_CLASSIFICATION_GLOB = "*-unrated-classification.json"
UNRATED_CLASSIFICATION_FILE = "unrated-classification.json"
# Read-only secondary locations searched when ``--out-dir`` holds no evidence
# file. Kept as a module constant (not inlined) so tests can neutralise it and
# assert the honest "unknown" fallback without depending on ambient files.
UNRATED_CLASSIFICATION_FALLBACK_DIRS: tuple[Path, ...] = (DEFAULT_OUT_DIR,)

DEFECT_CLASSES = frozenset(
    {
        "confirmed_deregistered_still_active_in_db",
        "db_inactive_but_source_registered",
    }
)
LEGITIMATE_CLASSES = frozenset(
    {
        "registered_after_snapshot_publication",
        "registered_on_or_before_snapshot_but_absent",
        "db_inactive_matches_deregistration",
    }
)
UNEXPLAINED_CLASSES = frozenset({"not_found_in_cqc_api", "unclassified_status", "api_error"})

UNRATED_CLASS_NAMES = (
    "legitimate_unrated",
    "not_yet_inspected",
    "not_applicable",
    "ingestion_omission",
    "entity_mapping",
    "unknown",
)


UNRATED_RAW_CLASS_MAP = {
    # workstream raw class -> report class vocabulary
    "has_published_rating_now": "ingestion_omission",
    "sentinel_not_a_rating": "not_applicable",
    "no_current_ratings_but_historic_overall": "legitimate_unrated",
    "never_rated_no_historic_overall": "not_yet_inspected",
    "api_404_or_gone": "entity_mapping",
    "api_error": "unknown",
}


class CadenceDriftError(RuntimeError):
    """The workflow cron and the fallback constant disagree."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be positive, got {value}")
    return value


def env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _hours(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def _ratio(numerator: int, denominator: int, *, digits: int = 1) -> str:
    """Render an explicit numerator over denominator, never a bare percentage."""
    if not denominator:
        return f"{numerator:,} / 0 (n/a)"
    return f"{numerator:,} / {denominator:,} ({100.0 * numerator / denominator:.{digits}f}%)"


def _pct(numerator: int, denominator: int, *, digits: int = 1) -> float:
    if not denominator:
        return 0.0
    return round(100.0 * numerator / denominator, digits)


def wilson_interval(successes: int, total: int, *, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion, in percent."""
    if total <= 0:
        return (0.0, 0.0)
    phat = successes / total
    denominator = 1 + z * z / total
    centre = (phat + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(phat * (1 - phat) / total + z * z / (4 * total * total)) / denominator
    return (round(100 * max(0.0, centre - margin), 1), round(100 * min(1.0, centre + margin), 1))


def hours_between(earlier: datetime, later: datetime) -> float:
    return (later - earlier).total_seconds() / 3600.0


def _as_row_dict(cur) -> dict[str, Any]:
    columns = [desc[0] for desc in cur.description]
    return {columns[i]: value for i, value in enumerate(cur.fetchone())}


# ---------------------------------------------------------------------------
# cron parsing - the cadence single source of truth
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CronSchedule:
    expression: str
    minute: frozenset[int]
    hour: frozenset[int]
    day_of_month: frozenset[int]
    month: frozenset[int]
    day_of_week: frozenset[int]

    @property
    def unrestricted(self) -> bool:
        return (
            self.day_of_month == frozenset(range(1, 32))
            and self.month == frozenset(range(1, 13))
            and self.day_of_week == frozenset(range(0, 7))
        )

    def _day_matches(self, day: date) -> bool:
        dom_restricted = self.day_of_month != frozenset(range(1, 32))
        dow_restricted = self.day_of_week != frozenset(range(0, 7))
        dom_ok = day.day in self.day_of_month
        dow_ok = ((day.weekday() + 1) % 7) in self.day_of_week  # cron: 0 = Sunday
        if dom_restricted and dow_restricted:
            return dom_ok or dow_ok  # POSIX: either field may match
        return dom_ok and dow_ok

    def fires_between(self, start: datetime, end: datetime) -> list[datetime]:
        """Every fire time in [start, end), in UTC."""
        start = start.astimezone(UTC)
        end = end.astimezone(UTC)
        if end <= start:
            return []
        fires: list[datetime] = []
        day = start.date()
        while day <= end.date():
            if day.month in self.month and self._day_matches(day):
                for hour in sorted(self.hour):
                    for minute in sorted(self.minute):
                        moment = datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
                        if start <= moment < end:
                            fires.append(moment)
            day += timedelta(days=1)
        return sorted(fires)

    def runs_per_week(self, reference: datetime) -> int:
        """Fires in the UTC week containing ``reference`` (Monday 00:00 start)."""
        week_start = datetime(reference.year, reference.month, reference.day, tzinfo=UTC) - timedelta(
            days=reference.weekday()
        )
        return len(self.fires_between(week_start, week_start + timedelta(days=7)))


_CRON_BOUNDS = {"minute": (0, 59), "hour": (0, 23), "day_of_month": (1, 31), "month": (1, 12), "day_of_week": (0, 7)}


def parse_cron_field(field_value: str, *, name: str) -> frozenset[int]:
    lo, hi = _CRON_BOUNDS[name]
    values: set[int] = set()
    for raw_part in field_value.split(","):
        part = raw_part.strip()
        if not part:
            raise ValueError(f"cron {name} field has an empty component: {field_value!r}")
        step = 1
        if "/" in part:
            part, _, step_raw = part.partition("/")
            try:
                step = int(step_raw)
            except ValueError as exc:
                raise ValueError(f"cron {name} step is not an integer: {step_raw!r}") from exc
            if step < 1:
                raise ValueError(f"cron {name} step must be >= 1: {step_raw!r}")
        if part in {"*", ""}:
            start, stop = lo, hi
        elif "-" in part:
            first, _, second = part.partition("-")
            try:
                start, stop = int(first), int(second)
            except ValueError as exc:
                raise ValueError(f"cron {name} range is not numeric: {part!r}") from exc
        else:
            try:
                start = stop = int(part)
            except ValueError as exc:
                raise ValueError(f"cron {name} value is not numeric: {part!r}") from exc
        if not (lo <= start <= hi and lo <= stop <= hi) or stop < start:
            raise ValueError(f"cron {name} value out of range {lo}-{hi}: {part!r}")
        values.update(range(start, stop + 1, step))
    if not values:
        raise ValueError(f"cron {name} field selects no value: {field_value!r}")
    return frozenset(sorted(values))


def parse_cron(expression: str) -> CronSchedule:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"cron expression must have 5 fields, got {len(fields)}: {expression!r}")
    minute, hour, day_of_month, month, day_of_week = fields
    day_of_week_set = parse_cron_field(day_of_week, name="day_of_week")
    if 7 in day_of_week_set:  # cron allows 7 == Sunday
        day_of_week_set = frozenset(day_of_week_set - {7} | {0})
    return CronSchedule(
        expression=expression,
        minute=parse_cron_field(minute, name="minute"),
        hour=parse_cron_field(hour, name="hour"),
        day_of_month=parse_cron_field(day_of_month, name="day_of_month"),
        month=parse_cron_field(month, name="month"),
        day_of_week=day_of_week_set,
    )


def workflow_schedule(path: Path | str = SIGNAL_POLL_WORKFLOW) -> dict[str, Any]:
    """Read the cron schedule(s) and the sweep_size default out of the workflow."""
    workflow_path = Path(path)
    try:
        text = workflow_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read {workflow_path}: {exc}") from exc
    crons = re.findall(r"^\s*-\s*cron:\s*[\"']([^\"']+)[\"']\s*$", text, re.MULTILINE)
    sweep_size: int | None = None
    index = text.find("sweep_size:")
    if index != -1:
        match = re.search(r"default:\s*[\"']?(\d+)[\"']?", text[index : index + 600])
        if match:
            sweep_size = int(match.group(1))
    if not crons:
        raise ValueError(f"no cron schedule found in {workflow_path}")
    return {"path": str(workflow_path), "crons": crons, "sweep_size": sweep_size}


def cadence_drift_notes(path: Path | str = SIGNAL_POLL_WORKFLOW) -> list[str]:
    """Compare the workflow file with the fallback constants. Empty means in sync."""
    try:
        parsed = workflow_schedule(path)
    except ValueError as exc:
        return [f"workflow schedule unreadable: {exc}"]
    notes: list[str] = []
    if parsed["crons"] != [WORKFLOW_CRON_FALLBACK]:
        notes.append(
            f"cron drift: workflow has {parsed['crons']} but WORKFLOW_CRON_FALLBACK is {WORKFLOW_CRON_FALLBACK!r}"
        )
    if parsed["sweep_size"] is not None and parsed["sweep_size"] != WORKFLOW_SWEEP_SIZE_FALLBACK:
        notes.append(
            f"sweep size drift: workflow default is {parsed['sweep_size']} but "
            f"WORKFLOW_SWEEP_SIZE_FALLBACK is {WORKFLOW_SWEEP_SIZE_FALLBACK}"
        )
    return notes


def derive_cadence(*, path: Path | str = SIGNAL_POLL_WORKFLOW, now: datetime) -> dict[str, Any]:
    """Expected poll cadence, from the workflow file with a loud fallback."""
    drift = cadence_drift_notes(path)
    schedules: list[CronSchedule]
    source: str
    try:
        parsed = workflow_schedule(path)
        schedules = [parse_cron(expr) for expr in parsed["crons"]]
        source = CADENCE_SOURCES["workflow"]
        sweep_size = parsed["sweep_size"] if parsed["sweep_size"] is not None else WORKFLOW_SWEEP_SIZE_FALLBACK
    except ValueError as exc:
        schedules = [parse_cron(WORKFLOW_CRON_FALLBACK)]
        source = f"{CADENCE_SOURCES['fallback']}: {exc}"
        sweep_size = WORKFLOW_SWEEP_SIZE_FALLBACK
    weekly = 0
    for schedule in schedules:
        weekly += schedule.runs_per_week(now)
    runs_per_day = round(weekly / 7, 2)
    return {
        "expressions": [schedule.expression for schedule in schedules],
        "expression": schedules[0].expression if schedules else None,
        "runs_per_day": runs_per_day,
        "runs_per_week": weekly,
        "sweep_size": sweep_size,
        "source": source,
        "drift_notes": drift,
        "match_window_hours": FIRE_MATCH_WINDOW.total_seconds() / 3600,
        "grace_minutes": MISSED_GRACE.total_seconds() / 60,
    }


def cadence_change_at(path: Path | str = SIGNAL_POLL_WORKFLOW) -> str | None:
    """Commit time of the last change to the workflow's cron, from local git."""
    git = shutil.which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "log", "-1", "--format=%cI", "--", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return _iso(datetime.fromisoformat(proc.stdout.strip()))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# polling coverage - five buckets, two sources, reconciled
# ---------------------------------------------------------------------------
def parse_gh_runs(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, (str, bytes)):
        payload = json.loads(payload)
    if not isinstance(payload, list):
        raise ValueError("gh run list payload must be a JSON array")
    runs: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        created_raw = item.get("createdAt")
        if not created_raw:
            continue
        try:
            created = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        runs.append(
            {
                "event": str(item.get("event") or ""),
                "status": str(item.get("status") or ""),
                "conclusion": str(item.get("conclusion") or ""),
                "created_at": created.astimezone(UTC),
                "database_id": item.get("databaseId") or item.get("database_id"),
                "url": item.get("url"),
            }
        )
    return sorted(runs, key=lambda run: run["created_at"])


def _match_fires_to_runs(
    fires: list[datetime], runs: list[dict[str, Any]], *, window: timedelta
) -> tuple[list[datetime], list[datetime]]:
    """Greedy pairing of fires to runs within ``window``. Returns (matched, unmatched)."""
    unmatched_runs = sorted(runs, key=lambda run: run["created_at"])
    matched: list[datetime] = []
    unmatched: list[datetime] = []
    for fire in sorted(fires):
        hit = next(
            (
                index
                for index, run in enumerate(unmatched_runs)
                if fire <= run["created_at"] <= fire + window
            ),
            None,
        )
        if hit is None:
            unmatched.append(fire)
        else:
            matched.append(fire)
            unmatched_runs.pop(hit)
    return matched, unmatched


def poll_coverage(
    runs: list[dict[str, Any]],
    *,
    schedules: list[CronSchedule],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
    grace: timedelta = MISSED_GRACE,
    match_window: timedelta = FIRE_MATCH_WINDOW,
    cadence_change: datetime | None = None,
) -> dict[str, Any]:
    """Five buckets - expected, attempted, successful, failed, missed - per source."""
    fires = sorted({fire for schedule in schedules for fire in schedule.fires_between(window_start, window_end)})
    due = [fire for fire in fires if fire <= now - grace]
    not_yet_due = [fire for fire in fires if fire > now - grace]

    in_window = [run for run in runs if window_start <= run["created_at"] < window_end]
    scheduled = [run for run in in_window if run["event"] == "schedule"]
    other = [run for run in in_window if run["event"] != "schedule"]

    successful = [run for run in scheduled if run["conclusion"] == SUCCESSFUL_CONCLUSION]
    failed = [run for run in scheduled if run["conclusion"] in FAILED_CONCLUSIONS]
    cancelled = [run for run in scheduled if run["conclusion"] == CANCELLED_CONCLUSION]
    in_flight = [run for run in scheduled if run["conclusion"] not in FAILED_CONCLUSIONS and run["conclusion"] not in {SUCCESSFUL_CONCLUSION, CANCELLED_CONCLUSION}]

    attempted = len(scheduled)
    missed_count = max(0, len(due) - attempted)
    matched_fires, unmatched_fires = _match_fires_to_runs(due, scheduled, window=match_window)

    bucket_source = "gh run list --workflow=cqc-signal-poll.yml --json event,status,conclusion,createdAt,databaseId"
    coverage: dict[str, Any] = {
        "window": {"start": _iso(window_start), "end": _iso(window_end), "hours": round(hours_between(window_start, window_end), 1)},
        "grace_minutes": int(grace.total_seconds() // 60),
        "expected": {
            "runs": len(fires),
            "due": len(due),
            "not_yet_due": len(not_yet_due),
            "derivation": "cron fire times inside the window (UTC)",
            "source": "workflow cron, see cadence",
        },
        "attempted": {"runs": attempted, "source": bucket_source, "manual_or_other_event_runs": len(other)},
        "successful": {"runs": len(successful), "source": f"{bucket_source}; conclusion == success"},
        "failed": {
            "runs": len(failed),
            "source": f"{bucket_source}; conclusion in {sorted(FAILED_CONCLUSIONS)}",
            "by_conclusion": dict(Counter(run["conclusion"] for run in failed)),
        },
        "cancelled": {"runs": len(cancelled), "source": f"{bucket_source}; conclusion == cancelled (not counted as failed)"},
        "in_flight": {"runs": len(in_flight), "source": f"{bucket_source}; not yet concluded"},
        "missed": {
            "runs": missed_count,
            "definition": f"expected due fires ({len(due)}) minus attempted scheduled runs ({attempted}), floored at zero",
            "source": "derived from the two rows above",
            "fires": [_iso(fire) for fire in unmatched_fires] if missed_count else [],
        },
        "coverage_pct": _pct(attempted, len(due), digits=1),
        "delivered_pct": _pct(len(successful), len(due), digits=1),
        "fires_without_a_matching_run": {
            "runs": len(unmatched_fires),
            "definition": f"due fires with no scheduled run created within {match_window.total_seconds() / 3600:g}h after the fire",
            "source": "derived from the two rows above",
        },
        "consistency": {
            "successful_plus_failed_plus_cancelled_plus_in_flight": len(successful)
            + len(failed)
            + len(cancelled)
            + len(in_flight),
            "attempted": attempted,
            "due_plus_not_yet_due": len(due) + len(not_yet_due),
            "expected": len(fires),
        },
    }
    if attempted > len(due):
        coverage["unexpected_extra"] = {
            "runs": attempted - len(due),
            "note": "more scheduled runs than due fires, e.g. a manual dispatch recorded as schedule or a window spanning a cadence change",
        }
    if cadence_change is not None and window_start <= cadence_change < window_end:
        post_fires = [fire for fire in fires if fire >= cadence_change]
        post_due = [fire for fire in post_fires if fire <= now - grace]
        post_runs = [run for run in scheduled if run["created_at"] >= cadence_change]
        coverage["cadence_change"] = {
            "at": _iso(cadence_change),
            "source": "git log -1 --format=%cI -- .github/workflows/cqc-signal-poll.yml",
            "expected_runs": len(post_fires),
            "due": len(post_due),
            "attempted": len(post_runs),
            "missed": max(0, len(post_due) - len(post_runs)),
            "note": "this window spans a schedule change, so the window-wide expectation mixes two cadences",
        }
    return coverage


def coverage_unavailable(
    reason: str | None,
    *,
    schedules: list[CronSchedule],
    window_start: datetime,
    window_end: datetime,
    now: datetime,
    grace: timedelta = MISSED_GRACE,
) -> dict[str, Any]:
    """Placeholder for the no-run-history case.

    Expected fires are still derived from the cron (that never needs a network
    call); the four delivered buckets stay None rather than guessing zero, and
    the verdict for the pipeline becomes UNVERIFIED instead of MATCHED.
    """
    fires = sorted({fire for schedule in schedules for fire in schedule.fires_between(window_start, window_end)})
    due = [fire for fire in fires if fire <= now - grace]
    return {
        "available": False,
        "reason": reason or "run history unavailable",
        "window": {
            "start": _iso(window_start),
            "end": _iso(window_end),
            "hours": round(hours_between(window_start, window_end), 1),
        },
        "grace_minutes": grace.total_seconds() / 60,
        "expected": {
            "runs": len(fires),
            "due": len(due),
            "not_yet_due": len(fires) - len(due),
            "derivation": None,
            "source": "cron parsed from the workflow file (no network needed)",
        },
        "attempted": {"runs": None, "source": "unavailable"},
        "successful": {"runs": None, "source": "unavailable"},
        "failed": {"runs": None, "source": "unavailable", "by_conclusion": {}},
        "cancelled": {"runs": None, "source": "unavailable"},
        "in_flight": {"runs": None, "source": "unavailable"},
        "missed": {"runs": None, "definition": "not assertable without run history", "source": "unavailable", "fires": []},
        "coverage_pct": None,
        "delivered_pct": None,
        "fires_without_a_matching_run": {"runs": None, "definition": "not assertable", "source": "unavailable"},
        "consistency": None,
    }


def sweep_coverage(
    directory_size: int,
    *,
    runs_per_week: int,
    sweep_size: int,
    sla: timedelta = FRESHNESS_SLA,
) -> dict[str, Any]:
    """How long a full directory sweep takes at a given cadence, vs the SLA."""
    if sweep_size <= 0 or runs_per_week <= 0:
        return {"feasible": False, "reason": "runs_per_week and sweep_size must both be positive"}
    per_week = runs_per_week * sweep_size
    days = (directory_size / per_week) * 7 if per_week else None
    sla_days = sla.total_seconds() / 86400
    min_runs_per_week = math.ceil(directory_size * 7 / (sla_days * sweep_size)) if directory_size else 0
    interval_hours = 7 * 24 / runs_per_week
    meets = days is not None and days * 24 <= sla.total_seconds() / 3600
    return {
        "directory_size": directory_size,
        "runs_per_week": runs_per_week,
        "sweep_size": sweep_size,
        "locations_per_week": per_week,
        "full_sweep_days": round(days, 1) if days is not None else None,
        "sla_days": sla_days,
        "meets_sla": meets,
        "min_runs_per_week_for_sla": min_runs_per_week,
        "interval_hours": round(interval_hours, 1),
        "arithmetic": (
            f"{directory_size:,} locations / ({runs_per_week} runs/week x {sweep_size:,} per run) = "
            f"{days:.1f} days per full sweep"
            if days is not None
            else "not computable"
        ),
        "note": "requirement the schedule must meet to honour the documented 8-day freshness promise",
    }


# ---------------------------------------------------------------------------
# snapshot fetch - bounded, resumable, labelled full vs sampled
# ---------------------------------------------------------------------------
@dataclass
class DirectorySnapshot:
    uri: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    sha256: str | None = None
    ids: frozenset[str] = field(default_factory=frozenset)
    coverage: str = "unavailable"  # full | sampled | unavailable
    complete: bool = False
    identity_from_cache: bool = False
    checksum_verified: bool = False
    bytes_read: int = 0
    declared_bytes: int | None = None
    byte_cap: int = SNAPSHOT_MAX_BYTES_DEFAULT
    id_cap: int = SNAPSHOT_MAX_IDS_DEFAULT
    source: str = ""
    note: str = ""
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "published_at": self.published_at,
            "retrieved_at": self.retrieved_at,
            "sha256": self.sha256,
            "entity_count": len(self.ids),
            "coverage": self.coverage,
            "complete": self.complete,
            "identity_from_cache": self.identity_from_cache,
            "checksum_verified": self.checksum_verified,
            "bytes_read": self.bytes_read,
            "declared_bytes": self.declared_bytes,
            "byte_cap": self.byte_cap,
            "id_cap": self.id_cap,
            "source": self.source,
            "note": self.note,
            "error": self.error,
        }


def _incremental_update():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import incremental_update  # noqa: PLC0415 - repo helper, imported lazily

    return incremental_update


def _snapshot_cache_path(cache_dir: Path) -> Path:
    return cache_dir / "directory-snapshot.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _decode_ids(text: str, *, id_cap: int, collected: set[str]) -> dict[str, Any]:
    """Pull location IDs out of directory CSV text (header line located first)."""
    lines = text.splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("Name,Also known as,Address,")), None)
    if header_index is None:
        return {"ids_found": 0, "complete_scan": False, "error": "directory CSV header was not recognised"}
    preamble = "\n".join(lines[:header_index])
    published = re.search(r"produced on\s+([^,\r\n]+)", preamble, flags=re.IGNORECASE)
    reader = csv.DictReader(lines[header_index:])
    if not reader.fieldnames or LOCATION_ID_COLUMN not in reader.fieldnames:
        return {"ids_found": 0, "complete_scan": False, "error": "directory CSV location ID column was missing"}
    found = 0
    capped = False
    for row in reader:
        location_id = (row.get(LOCATION_ID_COLUMN) or "").strip()
        if not location_id:
            continue
        collected.add(location_id)
        found += 1
        if len(collected) >= id_cap:
            capped = True
            break
    return {
        "ids_found": found,
        "complete_scan": not capped,
        "published_at": published.group(1).strip() if published else None,
        "error": None,
    }


def fetch_directory_snapshot(
    *,
    cache_dir: Path,
    max_bytes: int | None = None,
    max_ids: int | None = None,
    ttl: timedelta = SNAPSHOT_CACHE_TTL,
    force: bool = False,
    now: datetime | None = None,
    timeout: int = GH_TIMEOUT_DEFAULT,
) -> DirectorySnapshot:
    """Bounded, resumable fetch of the current CQC active-location directory.

    Caps come from the environment (``CQC_NIGHTLY_SNAPSHOT_MAX_BYTES``,
    ``CQC_NIGHTLY_SNAPSHOT_MAX_IDS``). When a cap truncates the work the result
    is ``sampled`` and never presented as full coverage.
    """
    now = now or datetime.now(UTC)
    byte_cap = max_bytes or env_int("CQC_NIGHTLY_SNAPSHOT_MAX_BYTES", SNAPSHOT_MAX_BYTES_DEFAULT)
    id_cap = max_ids or env_int("CQC_NIGHTLY_SNAPSHOT_MAX_IDS", SNAPSHOT_MAX_IDS_DEFAULT)
    cache_path = _snapshot_cache_path(cache_dir)
    cached = _load_json(cache_path)
    source = "GET CQC data page -> CQC_directory.csv link -> streamed body (hashlib.sha256)"

    try:
        import requests  # noqa: PLC0415 - optional dependency, degrade if missing
    except ImportError as exc:  # pragma: no cover - requests ships with the repo venv
        return DirectorySnapshot(
            coverage="unavailable",
            byte_cap=byte_cap,
            id_cap=id_cap,
            source=source,
            error=f"requests is unavailable: {exc}",
        )

    helper = _incremental_update()
    headers = {"Accept": "text/html,text/csv", "User-Agent": "CareGist-Reconciler/1.0"}
    try:
        page = helper._request_with_retries(helper.DEFAULT_DATA_PAGE_URL, headers=headers, timeout=timeout)
        match = re.search(
            r"href=[\"']([^\"']*CQC_directory\.csv(?:\?[^\"']*)?)[\"']",
            page.text,
            flags=re.IGNORECASE,
        )
        if not match:
            raise helper.ChangesFetchError("current CQC directory CSV link was not found on the data page")
        from urllib.parse import urljoin

        uri = urljoin(helper.DEFAULT_DATA_PAGE_URL, match.group(1))
        if not helper._is_cqc_https_url(uri):
            raise helper.ChangesFetchError("refusing a non-CQC or non-HTTPS directory source URI")
    except Exception as exc:  # noqa: BLE001 - a failed fetch is reported, never fatal
        return DirectorySnapshot(
            coverage="unavailable",
            byte_cap=byte_cap,
            id_cap=id_cap,
            source=source,
            error=f"{type(exc).__name__}: {str(exc)[:200]}",
        )

    cached_retrieved = None
    if cached.get("retrieved_at"):
        try:
            cached_retrieved = datetime.fromisoformat(str(cached["retrieved_at"]).replace("Z", "+00:00"))
        except ValueError:
            cached_retrieved = None

    # Resumable: reuse the cached ID set when it is complete, still fresh, and
    # the source URI has not moved. Identity is labelled as cached so a stale
    # retrieval time is never presented as today's fetch.
    if (
        not force
        and cached.get("complete")
        and str(cached.get("uri")) == uri
        and cached_retrieved is not None
        and now - cached_retrieved < ttl
        and cached.get("ids")
    ):
        return DirectorySnapshot(
            uri=uri,
            published_at=cached.get("published_at"),
            retrieved_at=_iso(cached_retrieved),
            sha256=cached.get("sha256"),
            ids=frozenset(str(value) for value in cached["ids"]),
            coverage="full",
            complete=True,
            identity_from_cache=True,
            checksum_verified=bool(cached.get("sha256")),
            bytes_read=int(cached.get("bytes_read") or 0),
            declared_bytes=cached.get("declared_bytes"),
            byte_cap=byte_cap,
            id_cap=id_cap,
            source=source,
            note=f"resumed from cache (fetched {_iso(cached_retrieved)}); re-fetches after {ttl.total_seconds() / 3600:g}h or with --refresh-snapshot",
        )

    offset = 0
    collected: set[str] = set()
    published_at = cached.get("published_at") if str(cached.get("uri")) == uri else None
    resumed = False
    if not force and str(cached.get("uri")) == uri and not cached.get("complete"):
        offset = int(cached.get("bytes_read") or 0)
        collected = {str(value) for value in cached.get("ids") or []}
        resumed = offset > 0 and bool(collected)

    chunks: list[bytes] = []
    hasher = hashlib.sha256()
    total = 0
    declared: int | None = None
    hit_cap = False
    try:
        stream_headers = dict(headers)
        if resumed:
            stream_headers["Range"] = f"bytes={offset}-"
        with requests.get(uri, headers=stream_headers, stream=True, timeout=timeout) as response:
            if response.status_code not in (200, 206):
                raise helper.ChangesFetchError(f"directory CSV returned {response.status_code}")
            if response.status_code == 200 and resumed:
                # Server ignored the Range request: start over so the hash covers the whole file.
                resumed = False
                offset = 0
                collected = set()
                published_at = None
            raw_length = response.headers.get("Content-Length")
            if raw_length and raw_length.isdigit():
                declared = int(raw_length) + offset
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if not chunk:
                    continue
                room = byte_cap - (total + len(chunk))
                if room < 0:
                    chunk = chunk[: len(chunk) + room]
                    hit_cap = True
                chunks.append(chunk)
                if not resumed:
                    hasher.update(chunk)
                total += len(chunk)
                if hit_cap:
                    break
    except Exception as exc:  # noqa: BLE001
        return DirectorySnapshot(
            uri=uri,
            published_at=published_at,
            retrieved_at=_iso(now),
            coverage="unavailable",
            byte_cap=byte_cap,
            id_cap=id_cap,
            source=source,
            error=f"{type(exc).__name__}: {str(exc)[:200]}",
            complete=False,
        )

    text = b"".join(chunks).decode("utf-8", errors="replace").lstrip("\ufeff")
    parsed = _decode_ids(text, id_cap=id_cap, collected=collected)
    if parsed.get("published_at"):
        published_at = parsed["published_at"]
    if len(collected) >= id_cap:
        parsed["complete_scan"] = False
    complete = bool(parsed["complete_scan"]) and not hit_cap and not resumed_partial(offset, hit_cap)
    if complete and not resumed:
        checksum = hasher.hexdigest()
    elif complete:
        checksum = cached.get("sha256") if str(cached.get("uri")) == uri else None
    else:
        checksum = None
    coverage = "full" if complete else "sampled"
    snapshot = DirectorySnapshot(
        uri=uri,
        published_at=published_at,
        retrieved_at=_iso(now),
        sha256=checksum,
        ids=frozenset(collected),
        coverage=coverage,
        complete=complete,
        identity_from_cache=False,
        checksum_verified=bool(checksum) and not resumed,
        bytes_read=total + offset,
        declared_bytes=declared,
        byte_cap=byte_cap,
        id_cap=id_cap,
        source=source,
        note=(
            "full stream read"
            if coverage == "full" and not resumed
            else "pooled fetch was resumed mid-stream: the checksum covers only the resumed part, so it is withheld"
            if resumed
            else f"caps truncated the read (bytes <= {byte_cap:,}, ids <= {id_cap:,})"
        ),
        error=parsed.get("error"),
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        if complete and snapshot.checksum_verified:
            payload = {
                "uri": uri,
                "published_at": published_at,
                "retrieved_at": snapshot.retrieved_at,
                "sha256": checksum,
                "ids": sorted(collected),
                "complete": True,
                "bytes_read": snapshot.bytes_read,
                "declared_bytes": declared,
            }
        else:
            # Keep the partial state so the next run resumes instead of restarting.
            payload = {
                "uri": uri,
                "published_at": published_at,
                "retrieved_at": _iso(now),
                "sha256": None,
                "ids": sorted(collected),
                "complete": False,
                "bytes_read": snapshot.bytes_read,
                "declared_bytes": declared,
            }
        _write_json(_snapshot_cache_path(cache_dir), payload)
    except OSError:
        pass
    return snapshot


def resumed_partial(offset: int, hit_cap: bool) -> bool:
    """True when the body we parsed was only the tail of the source."""
    return offset > 0 or hit_cap


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    tmp.chmod(0o600)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# identifier-level reconciliation
# ---------------------------------------------------------------------------
def identifier_diff(db_ids_by_status: dict[str, frozenset[str]], snapshot_ids: frozenset[str]) -> dict[str, Any]:
    active = db_ids_by_status.get("ACTIVE", frozenset())
    inactive = db_ids_by_status.get("INACTIVE", frozenset())
    all_db = active | inactive
    return {
        "db_active": len(active),
        "db_inactive": len(inactive),
        "snapshot_ids": len(snapshot_ids),
        "overlap": len(all_db & snapshot_ids),
        "overlap_active": len(active & snapshot_ids),
        "overlap_inactive": len(inactive & snapshot_ids),
        "only_in_db_active": sorted(active - snapshot_ids),
        "only_in_db_inactive": sorted(inactive - snapshot_ids),
        "only_in_source": sorted(snapshot_ids - all_db),
        "source_but_db_inactive": sorted(snapshot_ids & inactive),
        "definitions": {
            "only_in_db_active": "ACTIVE in CareGist, absent from the snapshot",
            "only_in_source": "present in the snapshot, absent from CareGist entirely",
            "source_but_db_inactive": "present in the snapshot, INACTIVE in CareGist",
            "only_in_db_inactive": "INACTIVE in CareGist, absent from the snapshot (expected: the snapshot lists active locations only)",
        },
    }


def classify_id(
    *,
    side: str,
    status: str | None,
    registration_date: str | None,
    deregistration_date: str | None,
    snapshot_published_at: str | None,
) -> str:
    """Map one live CQC API record onto an alignment class. Source: CQC API detail."""
    status = (status or "").strip() or None
    if side == "db_active_absent_from_source":
        if status == "Deregistered":
            return "confirmed_deregistered_still_active_in_db"
        if status == "Registered":
            if registration_date and snapshot_published_at and registration_date > snapshot_published_at:
                return "registered_after_snapshot_publication"
            return "registered_on_or_before_snapshot_but_absent"
        return "unclassified_status"
    if side == "source_present_db_inactive":
        if status == "Registered":
            return "db_inactive_but_source_registered"
        if status == "Deregistered":
            return "db_inactive_matches_deregistration"
        return "unclassified_status"
    if side == "source_absent_from_db":
        # A snapshot ID with no CareGist row at all: either the reconciliation
        # has not ingested it yet (timing) or it was dropped (defect) - the
        # report cannot tell them apart from these inputs, so it is unexplained
        # rather than silently assumed benign.
        return "unexplained_source_id_absent_from_db"
    raise ValueError(f"unknown classification side: {side!r}")


def classification_unavailable(
    ids: list[str] | tuple[str, ...],
    *,
    side: str | None = None,
    snapshot_published_at: str | None = None,
    fetch_detail: Callable[[str], dict[str, Any]] | None = None,
    cache_path: Path | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Stand-in classification used when the live CQC API cannot be reached.

    Nothing is classified, so the split reports 0 of N classified (with the
    "not classified" note) and the alignment verdict becomes UNVERIFIED rather
    than a false MATCHED/MISMATCHED.
    """
    population = list(ids)
    return {
        "side": side,
        "coverage": "unverified",
        "population": len(population),
        "selected": 0,
        "classified": 0,
        "fetched": 0,
        "reused": 0,
        "errors": 0,
        "failures": 0,
        "classes": {},
        "per_id": {},
        "cap": None,
        "source": "live CQC API unavailable: nothing classified",
        "note": (
            f"none of the {len(population)} ID(s) in this population were classified; per-ID classes are unknown "
            "and must not be read as 'no defect'"
        ),
        "cache_path": str(cache_path) if cache_path else None,
    }


def classify_divergent(
    ids: list[str] | tuple[str, ...],
    *,
    side: str,
    snapshot_published_at: str | None,
    fetch_detail: Callable[[str], dict[str, Any]],
    cap: int = API_CLASSIFY_MAX_DEFAULT,
    cache_path: Path | None = None,
    ttl: timedelta = API_CLASSIFY_TTL,
    sleep_seconds: float = API_CLASSIFY_SLEEP_DEFAULT,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Classify divergent IDs against live CQC, bounded by a cap, resumable via cache."""
    now = now or datetime.now(UTC)
    ordered = sorted(ids)
    selected = ordered[:cap] if cap and len(ordered) > cap else ordered
    coverage = "full" if len(selected) == len(ordered) else "sampled"
    cache = _load_json(cache_path) if cache_path else {}
    entries: dict[str, dict[str, Any]] = cache.get("classes") if isinstance(cache.get("classes"), dict) else {}
    per_id: dict[str, dict[str, Any]] = {}
    fetched = 0
    reused = 0
    failures = 0
    for location_id in selected:
        entry = entries.get(location_id) if isinstance(entries, dict) else None
        if entry and entry.get("class") != "api_error":
            try:
                fetched_at = datetime.fromisoformat(str(entry.get("fetched_at")).replace("Z", "+00:00"))
                fresh = now - fetched_at < ttl
            except (TypeError, ValueError):
                fresh = False
            if fresh:
                per_id[location_id] = entry
                reused += 1
                continue
        try:
            detail = fetch_detail(location_id)
        except Exception as exc:  # noqa: BLE001 - one bad ID must not sink the report
            per_id[location_id] = {
                "class": "api_error",
                "error": f"{type(exc).__name__}: {str(exc)[:140]}",
                "fetched_at": _iso(now),
            }
            failures += 1
            continue
        entry = {
            "class": classify_id(
                side=side,
                status=detail.get("registrationStatus"),
                registration_date=detail.get("registrationDate"),
                deregistration_date=detail.get("deregistrationDate"),
                snapshot_published_at=snapshot_published_at,
            ),
            "registration_status": detail.get("registrationStatus"),
            "registration_date": detail.get("registrationDate"),
            "deregistration_date": detail.get("deregistrationDate"),
            "fetched_at": _iso(now),
        }
        per_id[location_id] = entry
        fetched += 1
        if sleep_seconds:
            time.sleep(sleep_seconds)

    if cache_path:
        merged = dict(entries) if isinstance(entries, dict) else {}
        merged.update(per_id)
        if len(merged) > 5000:  # bounded cache: keep the newest entries only
            newest = sorted(
                merged.items(), key=lambda item: str(item[1].get("fetched_at") or ""), reverse=True
            )[:5000]
            merged = dict(newest)
        try:
            _write_json(cache_path, {"classes": merged, "updated_at": _iso(now)})
        except OSError:
            pass

    classes = Counter(entry["class"] for entry in per_id.values())
    return {
        "side": side,
        "coverage": coverage,
        "population": len(ordered),
        "selected": len(selected),
        "cap": cap,
        "classified": len(per_id),
        "fetched": fetched,
        "reused_from_cache": reused,
        "failures": failures,
        "classes": dict(sorted(classes.items())),
        "per_id": per_id,
        "source": "live CQC API location detail (registrationStatus, registrationDate, deregistrationDate)",
        "cache_path": str(cache_path) if cache_path else None,
        "cache_ttl_hours": ttl.total_seconds() / 3600,
        "note": "resumable: cached classifications are reused until the TTL expires",
    }


def summarize_classification(classification: dict[str, Any]) -> dict[str, Any]:
    classes = classification.get("classes") or {}
    defects = {name: count for name, count in classes.items() if name in DEFECT_CLASSES}
    legitimate = {name: count for name, count in classes.items() if name in LEGITIMATE_CLASSES}
    unexplained = {name: count for name, count in classes.items() if name in UNEXPLAINED_CLASSES}
    other = {
        name: count
        for name, count in classes.items()
        if name not in DEFECT_CLASSES and name not in LEGITIMATE_CLASSES and name not in UNEXPLAINED_CLASSES
    }
    return {
        "confirmed_defect": sum(defects.values()),
        "legitimate_timing_or_scope": sum(legitimate.values()),
        "unexplained": sum(unexplained.values()) + sum(other.values()),
        "defect_classes": defects,
        "legitimate_classes": legitimate,
        "unexplained_classes": {**unexplained, **other},
        "coverage": classification.get("coverage"),
        "source": classification.get("source"),
    }


def split_counts(classification: dict[str, Any], population: list[str], *, side: str) -> dict[str, Any]:
    """confirmed defect vs legitimate difference for one divergent population.

    ``population`` is the identifier population being split; the per-ID classes
    come from ``classification`` (bounded/labelled) so the same split can never
    mix a sampled verdict with a full population.
    """
    per_id = classification.get("per_id") or {}
    relevant = [per_id[location_id] for location_id in population if location_id in per_id]
    defects = sum(1 for entry in relevant if entry.get("class") in DEFECT_CLASSES)
    legitimate = sum(1 for entry in relevant if entry.get("class") in LEGITIMATE_CLASSES)
    unexplained = len(relevant) - defects - legitimate
    result = {
        "side": side,
        "coverage": classification.get("coverage"),
        "classified": len(relevant),
        "population": len(population),
        "confirmed_defect": defects,
        "legitimate_timing_or_scope": legitimate,
        "unexplained": unexplained,
        "source": classification.get("source"),
        "cache_path": classification.get("cache_path"),
    }
    if len(relevant) != len(population):
        result["note"] = (
            f"{len(population) - len(relevant)} of {len(population)} IDs in this population were not classified; "
            "counts above cover the classified subset only and the verdict treats the remainder as unexplained"
        )
    return result


def merge_summaries(per_side: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Combine the per-population class summaries the verdict reads."""
    merged: dict[str, Any] = {
        "confirmed_defect": 0,
        "legitimate_timing_or_scope": 0,
        "unexplained": 0,
        "defect_classes": {},
        "legitimate_classes": {},
        "unexplained_classes": {},
        "coverage": "full",
        "source": "live CQC API location detail, per divergent population (see per_side)",
        "per_side": per_side,
    }
    for side, summary in per_side.items():
        if not summary:
            continue
        for key in ("confirmed_defect", "legitimate_timing_or_scope", "unexplained"):
            merged[key] += int(summary.get(key) or 0)
        for key in ("defect_classes", "legitimate_classes", "unexplained_classes"):
            for name, count in (summary.get(key) or {}).items():
                merged[key][f"{side}:{name}"] = count
    coverage_rank = {"full": 0, "sampled": 1, "unverified": 2, "unavailable": 3}
    worst = max(
        [0] + [coverage_rank.get(str(summary.get("coverage")), 3) for summary in per_side.values() if summary]
    )
    merged["coverage"] = {rank: name for name, rank in coverage_rank.items()}[worst]
    return merged


def reconciliation_inputs_are_complete(diff: dict[str, Any], classification: dict[str, Any]) -> list[str]:
    """Reasons the identifier-level reconciliation cannot be called complete."""
    problems: list[str] = []
    if classification.get("coverage") != "full":
        problems.append(
            f"classification sampled: {classification.get('selected')} of {classification.get('population')} divergent IDs "
            f"(cap {classification.get('cap')})"
        )
    if classification.get("failures"):
        problems.append(f"{classification['failures']} divergent IDs could not be classified (CQC API errors)")
    if diff.get("only_in_source") and not classification:
        problems.append("source-only IDs were not classified")
    return problems


# ---------------------------------------------------------------------------
# verdicts
# ---------------------------------------------------------------------------
def data_alignment_verdict(
    *,
    snapshot: dict[str, Any],
    diff: dict[str, Any] | None,
    summary: dict[str, Any] | None,
    ingested: dict[str, Any] | None,
) -> dict[str, Any]:
    """Identifier-level verdict. Reasons are always printed, verdict or not."""
    reasons: list[str] = []
    if not diff or snapshot.get("coverage") == "unavailable":
        return {
            "verdict": VERDICT_UNVERIFIED,
            "reasons": [
                "the newest available directory snapshot could not be fetched, so identifiers were not reconciled",
                snapshot.get("error") or "snapshot unavailable",
            ],
            "scope": "identifier-level reconciliation against the newest available validated snapshot",
        }
    if snapshot.get("coverage") != "full":
        reasons.append(
            f"snapshot read was {snapshot.get('coverage')}: {snapshot.get('entity_count', 0):,} IDs from a bounded fetch "
            f"(cap {snapshot.get('byte_cap', 0):,} bytes / {snapshot.get('id_cap', 0):,} IDs)"
        )
    if snapshot.get("sha256") is None:
        reasons.append("snapshot checksum is withheld (pooled/resumed fetch), so the snapshot identity is not verified")
    scope = (
        f"snapshot {snapshot.get('published_at')} sha256 {str(snapshot.get('sha256'))[:12]}... "
        f"({snapshot.get('entity_count', 0):,} IDs, {snapshot.get('coverage')})"
    )

    defects = int((summary or {}).get("confirmed_defect") or 0)
    unexplained = int((summary or {}).get("unexplained") or 0)
    if defects or unexplained:
        if defects:
            reasons.append(f"{defects} confirmed defect(s): {summary.get('defect_classes')}")
        if unexplained:
            reasons.append(f"{unexplained} unexplained difference(s): {summary.get('unexplained_classes')}")
        return {"verdict": VERDICT_MISMATCHED, "reasons": reasons, "scope": scope}

    if ingested is not None and not ingested.get("newest_snapshot_covered", True):
        reasons.append(
            "the ingested database state is one publication behind: no reconciliation batch has covered the "
            f"{snapshot.get('published_at')} snapshot (latest covered {ingested.get('latest_covered_published_at')})"
        )
    if reasons:
        return {"verdict": VERDICT_UNVERIFIED, "reasons": reasons, "scope": scope}
    return {
        "verdict": VERDICT_MATCHED,
        "reasons": [
            f"no unexplained differences in scope: {scope}; "
            f"{snapshot.get('entity_count', 0) - diff['overlap']:,} source-only IDs, 0 unexplained only-in-DB IDs"
        ],
        "scope": scope,
    }


def pipeline_health_verdict(
    *,
    coverage: dict[str, Any] | None,
    sweep: dict[str, Any] | None,
    freshness: dict[str, Any] | None,
    observed_sweep: dict[str, Any] | None,
    run_history_status: str,
    drift_notes: list[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    unverified: list[str] = []
    if drift_notes:
        unverified.append(f"cadence constants disagree with the workflow: {drift_notes}")
    if run_history_status != "ok":
        unverified.append("GitHub Actions run history is unavailable, so expected-vs-attempted cannot be established")
    if coverage and coverage.get("available", True):
        if coverage["missed"]["runs"]:
            reasons.append(
                f"{coverage['missed']['runs']} missed tick(s): {coverage['missed']['definition']}; "
                f"{coverage['attempted']['runs']} attempted, {coverage['expected']['due']} due"
            )
        if coverage["failed"]["runs"]:
            reasons.append(f"{coverage['failed']['runs']} failed scheduled run(s): {coverage['failed']['by_conclusion']}")
        if coverage["in_flight"]["runs"]:
            reasons.append(f"{coverage['in_flight']['runs']} scheduled run(s) still in flight at report time")
    if sweep and sweep.get("meets_sla") is False:
        reasons.append(
            f"full directory sweep takes {sweep['full_sweep_days']} days at the configured cadence "
            f"({sweep['arithmetic']}), beyond the documented {sweep['sla_days']:g}-day promise; "
            f"needs >= {sweep['min_runs_per_week_for_sla']} runs/week at sweep size {sweep['sweep_size']:,}"
        )
    if observed_sweep and observed_sweep.get("meets_sla") is False and not (sweep and sweep.get("meets_sla") is False):
        reasons.append(
            f"full directory sweep takes {observed_sweep['full_sweep_days']} days at the measured cadence "
            f"({observed_sweep['arithmetic']})"
        )
    if freshness:
        signal = freshness.get("signal") or {}
        if signal and not signal.get("within_sla", True):
            reasons.append(
                f"newest CQC signal is {signal.get('age_hours')}h old, beyond the documented "
                f"{signal.get('sla_hours')}h poll promise"
            )
        ingested = freshness.get("ingested_source") or {}
        if ingested and not ingested.get("within_sla", True):
            reasons.append(
                f"the validated source snapshot is {ingested.get('age_hours')}h old "
                f"({ingested.get('published_at')}), beyond the documented {ingested.get('sla_hours')}h promise"
            )
    if reasons:
        return {"verdict": VERDICT_MISMATCHED, "reasons": reasons, "unverified_reasons": unverified}
    if unverified:
        return {"verdict": VERDICT_UNVERIFIED, "reasons": unverified, "unverified_reasons": unverified}
    return {
        "verdict": VERDICT_MATCHED,
        "reasons": [
            "expected cadence met: no missed, failed, or in-flight ticks in the window; "
            "full-sweep interval within the documented promise; signal and source freshness within SLA"
        ],
        "unverified_reasons": [],
    }


def build_verdicts(
    *,
    snapshot: dict[str, Any],
    diff: dict[str, Any] | None,
    summary: dict[str, Any] | None,
    ingested: dict[str, Any] | None,
    coverage: dict[str, Any] | None,
    sweep: dict[str, Any] | None,
    observed_sweep: dict[str, Any] | None,
    freshness: dict[str, Any] | None,
    run_history_status: str,
    drift_notes: list[str],
) -> dict[str, Any]:
    return {
        "vocabulary": VERDICT_VOCABULARY,
        "data_alignment": data_alignment_verdict(
            snapshot=snapshot, diff=diff, summary=summary, ingested=ingested
        ),
        "pipeline_health": pipeline_health_verdict(
            coverage=coverage,
            sweep=sweep,
            freshness=freshness,
            observed_sweep=observed_sweep,
            run_history_status=run_history_status,
            drift_notes=drift_notes,
        ),
    }


# ---------------------------------------------------------------------------
# run history (GitHub Actions) and DB cross-check
# ---------------------------------------------------------------------------
def gh_run_list(workflow: str, *, limit: int = 100, timeout: int = GH_TIMEOUT_DEFAULT) -> dict[str, Any]:
    gh = shutil.which("gh")
    if gh is None:
        return {"status": "unavailable", "reason": "gh CLI is not on PATH"}
    command = [
        gh,
        "run",
        "list",
        "--workflow",
        workflow,
        "--limit",
        str(limit),
        "--json",
        "event,status,conclusion,createdAt,databaseId,url",
    ]
    try:
        proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}
    if proc.returncode != 0:
        return {
            "status": "unavailable",
            "reason": f"gh exited {proc.returncode}: {(proc.stderr or '').strip()[:200]}",
            "command": " ".join(command),
        }
    try:
        runs = parse_gh_runs(proc.stdout)
    except ValueError as exc:
        return {"status": "unavailable", "reason": str(exc), "command": " ".join(command)}
    return {"status": "ok", "runs": runs, "command": " ".join(command)}


def gh_run_log(run_id: Any, *, timeout: int = GH_TIMEOUT_DEFAULT, max_bytes: int = API_ATTEST_MAX_BYTES) -> dict[str, Any]:
    gh = shutil.which("gh")
    if gh is None or run_id in (None, ""):
        return {"status": "unavailable", "reason": "gh CLI is not on PATH" if gh is None else "no run id"}
    command = [gh, "run", "view", str(run_id), "--log"]
    try:
        proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}
    if proc.returncode != 0:
        return {"status": "unavailable", "reason": f"gh exited {proc.returncode}: {(proc.stderr or '').strip()[:160]}"}
    return {
        "status": "ok",
        "text": (proc.stdout or "")[:max_bytes],
        "command": " ".join(command),
        "truncated": len(proc.stdout or "") > max_bytes,
    }


def attested_failure_cause(
    *,
    batch: dict[str, Any] | None,
    run_history: dict[str, Any],
    log_fetcher: Callable[[Any], dict[str, Any]] = gh_run_log,
    cache_path: Path | None = None,
    max_candidates: int = 3,
    window_hours: float = 6.0,
) -> dict[str, Any]:
    """Attest the real abort line for a failed batch from the workflow log.

    The DB records a generic wrapper ("Workflow ended before every shard
    completed") even when every shard succeeded, so the specific refusal reason
    only exists in the run log. This lookup is bounded, attributed, and cached;
    when it cannot run, the report says so instead of guessing a cause.
    """
    if not batch:
        return {"status": "not_applicable", "reason": "no failed reconciliation batch in scope"}
    if not env_flag("CQC_NIGHTLY_GH_ATTEST", True):
        return {"status": "skipped", "reason": "CQC_NIGHTLY_GH_ATTEST is disabled"}
    cache = _load_json(cache_path) if cache_path else {}
    cache_key = str(batch.get("id"))
    cached_entry = (cache.get("batches") or {}).get(cache_key) if isinstance(cache.get("batches"), dict) else None
    if cached_entry:
        return {**cached_entry, "from_cache": True}
    if run_history.get("status") != "ok":
        return {"status": "unavailable", "reason": f"run history unavailable: {run_history.get('reason')}"}
    try:
        created = datetime.fromisoformat(str(batch.get("created_at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return {"status": "unavailable", "reason": "batch created_at is not parseable"}
    candidates = [
        run
        for run in run_history.get("runs", [])
        if run["conclusion"] in FAILED_CONCLUSIONS
        and abs((run["created_at"] - created).total_seconds()) <= window_hours * 3600
    ]
    candidates.sort(key=lambda run: abs((run["created_at"] - created).total_seconds()))
    checked = 0
    for run in candidates[:max_candidates]:
        checked += 1
        log = log_fetcher(run["database_id"])
        if log.get("status") != "ok":
            continue
        for line in str(log.get("text", "")).splitlines():
            lowered = line.lower()
            if "refused" in lowered or "finalization failed" in lowered:
                result = {
                    "status": "attested",
                    "run_id": run["database_id"],
                    "at": _iso(run["created_at"]),
                    "line": line.strip()[-300:],
                    "source": f"gh run view {run['database_id']} --log",
                    "candidates_checked": checked,
                }
                if cache_path:
                    payload = cache if isinstance(cache, dict) else {}
                    batches = payload.get("batches") if isinstance(payload.get("batches"), dict) else {}
                    batches[cache_key] = result
                    payload["batches"] = batches
                    try:
                        _write_json(cache_path, payload)
                    except OSError:
                        pass
                return result
    return {
        "status": "unavailable",
        "reason": f"no refusal line found in {checked} candidate run log(s) within {window_hours:g}h of the batch",
    }


# ---------------------------------------------------------------------------
# database gathering
# ---------------------------------------------------------------------------
def scalar(cur, sql: str, params: tuple[Any, ...] = ()) -> Any:
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def db_ids_by_status(conn) -> dict[str, frozenset[str]]:
    """CareGist location IDs grouped by status.

    The identifier compared with the CQC directory is the location ID
    (``care_providers.id``), NOT ``provider_id``: a CQC provider runs many
    locations, so counting ``provider_id`` understates the row population
    (37,116 vs 57,193 distinct ACTIVE locations).
    """
    cur = conn.cursor()
    cur.execute("SELECT status, id FROM care_providers WHERE id IS NOT NULL")
    buckets: dict[str, set[str]] = {}
    for status, provider_id in cur.fetchall():
        buckets.setdefault(str(status or "").upper(), set()).add(str(provider_id))
    cur.close()
    return {status: frozenset(values) for status, values in buckets.items()}


def rating_event_completeness(conn, window_start: datetime) -> dict[str, Any]:
    sentinel_list = ", ".join("'%s'" % value.replace("'", "''") for value in RATING_SENTINEL_VALUES)
    old_sentinel_list = ", ".join("'%s'" % value.replace("'", "''") for value in OLD_VALUE_SENTINELS)
    destination_expr = "btrim(coalesce(new_value::text, ''), '\"')"

    def block(predicate: str, params: tuple[Any, ...]) -> dict[str, Any]:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE new_value::text = 'null') AS null_destination,
                   count(*) FILTER (WHERE {destination_expr} IN ({sentinel_list})) AS sentinel_destination,
                   count(*) FILTER (WHERE {destination_expr} IN ({sentinel_list}) = false
                                      AND new_value::text IS NOT NULL
                                      AND new_value::text <> 'null') AS real_destination,
                   count(*) FILTER (WHERE btrim(coalesce(old_value::text, ''), '"') IN ({old_sentinel_list})) AS old_value_sentinel
            FROM trusted_event_ledger
            WHERE event_type = 'rating_changed' {predicate}
            """,
            params,
        )
        row = _as_row_dict(cur)
        cur.close()
        total = int(row["total"] or 0)
        return {
            "total": total,
            "no_destination_value": int(row["null_destination"] or 0),
            "sentinel_destination": int(row["sentinel_destination"] or 0),
            "real_destination": int(row["real_destination"] or 0),
            "old_value_sentinel": int(row["old_value_sentinel"] or 0),
            "rendered": {
                "no_destination_value": _ratio(int(row["null_destination"] or 0), total),
                "sentinel_destination": _ratio(int(row["sentinel_destination"] or 0), total),
                "real_destination": _ratio(int(row["real_destination"] or 0), total),
                "old_value_sentinel": _ratio(int(row["old_value_sentinel"] or 0), total),
            },
        }

    window = block("AND observed_at > %s", (window_start,))
    all_time = block("", ())
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT {destination_expr} AS destination, count(*) AS events
        FROM trusted_event_ledger
        WHERE event_type = 'rating_changed'
          AND new_value::text <> 'null'
          AND {destination_expr} NOT IN ({sentinel_list})
        GROUP BY 1 ORDER BY 2 DESC
        """,
    )
    destinations = {str(name): int(count) for name, count in cur.fetchall()}
    cur.execute("SELECT min(observed_at), max(observed_at) FROM trusted_event_ledger WHERE event_type = 'rating_changed'")
    span = cur.fetchone() or (None, None)
    cur.execute(
        f"""
        SELECT count(*) AS unresolved,
               count(*) FILTER (WHERE btrim(coalesce(old_value::text, ''), '"') IN ({old_sentinel_list}))
                   AS unresolved_with_sentinel_prior
        FROM trusted_event_ledger
        WHERE event_type = 'rating_changed' AND new_value::text = 'null'
        """
    )
    unresolved_row = _as_row_dict(cur)
    unresolved = int(unresolved_row["unresolved"] or 0)
    unresolved_sentinel = int(unresolved_row["unresolved_with_sentinel_prior"] or 0)
    cur.close()
    return {
        "window": {**window, "start": _iso(window_start)},
        "all_time": {**all_time, "start": _iso(span[0]) if span[0] else None, "end": _iso(span[1]) if span[1] else None},
        "real_destination_values": destinations,
        "unresolved_detail": {
            "definition": "rating_changed events whose destination (new_value) is JSON null - all time",
            "unresolved": unresolved,
            "unresolved_with_sentinel_prior_value": unresolved_sentinel,
            "rendered": _ratio(unresolved_sentinel, unresolved),
            "sentinel_values": list(OLD_VALUE_SENTINELS),
            "source": "trusted_event_ledger (event_type = 'rating_changed', new_value::text = 'null')",
            "note": (
                "a sentinel prior value such as 'Not Yet Inspected' is a representation placeholder, not a rating, "
                "so these events cannot be presented as rating movements"
            ),
        },
        "representation_classes": {
            "no_destination_value": "new_value is JSON null: the event records that a rating moved but not what it moved to",
            "sentinel_destination": f"new_value is a sentinel string, not a rating: {list(RATING_SENTINEL_VALUES)}",
            "old_value_sentinel": f"old_value is a sentinel string, not a rating: {list(OLD_VALUE_SENTINELS)}",
        },
        "customer_facing_scope": (
            "only events with a real published destination rating are eligible for rating-movement claims; "
            "unresolved (null destination) and sentinel-destination events are excluded"
        ),
        "predicate": {
            "no_destination_value": "new_value::text = 'null'",
            "sentinel_destination": f"trim(new_value::text,'\"') in {list(RATING_SENTINEL_VALUES)}",
            "real_destination": "neither of the above and new_value is not null",
            "source": "trusted_event_ledger (event_type = 'rating_changed')",
        },
    }


def unrated_classification_search_dirs(out_dir: Path) -> list[Path]:
    """Directories searched for the workstream's unrated-classification file.

    ``out_dir`` first (the spec's ``artifacts/cqc-nightly/unrated-classification.json``),
    then the module fallback dirs (unioned, order preserved, de-duplicated).
    ``CQC_UNRATED_CLASSIFICATION_DIR`` (colon-separated) overrides the fallback
    list entirely, which is how a test or a dry run neutralises ambient files.
    """
    directories: list[Path] = [out_dir]
    override = os.environ.get("CQC_UNRATED_CLASSIFICATION_DIR")
    if override is not None:
        extra = [Path(part).expanduser() for part in override.split(os.pathsep) if part.strip()]
    else:
        extra = list(UNRATED_CLASSIFICATION_FALLBACK_DIRS)
    for directory in extra:
        if directory not in directories:
            directories.append(directory)
    return directories


def load_unrated_classification(out_dir: Path, *, count: int) -> dict[str, Any]:
    """Consume the sibling workstream's classification file, else report unknown.

    The workstream emits ``unrated.classes`` (counts with Wilson intervals) and
    ``unrated.sample_member_evidence`` (per-member raw class). Its raw class
    names are mapped onto the report's class vocabulary via
    ``UNRATED_RAW_CLASS_MAP``; an unrecognised raw class stays ``unknown`` and
    the raw name is preserved in the output.
    """
    candidates: list[Path] = []
    search_dirs: list[Path] = [out_dir]
    for directory in unrated_classification_search_dirs(out_dir):
        if directory != out_dir:
            search_dirs.append(directory)
    for directory in search_dirs:
        for pattern in (UNRATED_CLASSIFICATION_FILE, UNRATED_CLASSIFICATION_GLOB):
            candidates.extend(sorted(directory.glob(pattern)))
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        payload = _load_json(path)
        if not payload:
            continue
        sample = payload.get("unrated") if isinstance(payload.get("unrated"), dict) else payload
        evidence = sample.get("sample_member_evidence")
        sample_size = sample.get("sample_size") or (len(evidence) if isinstance(evidence, list) else 0)
        tallies: Counter[str] = Counter()
        if isinstance(evidence, list):
            for member in evidence:
                if isinstance(member, dict):
                    tallies[str(member.get("class") or "unknown")] += 1
        elif isinstance(sample.get("class_counts"), dict):
            tallies.update({str(k): int(v) for k, v in sample["class_counts"].items()})
        if not tallies and not (isinstance(sample.get("classes"), list) and sample["classes"]):
            continue
        total_sample = sum(tallies.values()) or int(sample.get("sample_size") or 0)
        reported = sample.get("classes")
        if isinstance(reported, list) and reported:
            classes = []
            for item in reported:
                if not isinstance(item, dict):
                    continue
                raw = str(item.get("name") or "unknown")
                classes.append(
                    {
                        "class": UNRATED_RAW_CLASS_MAP.get(raw, "unknown"),
                        "raw_class": raw,
                        "estimate": int(item.get("population_estimate") or 0),
                        "observed_in_sample": int(item.get("count") or 0),
                        "estimator": "sample share applied to the measured population (workstream estimate)",
                        "sample_size": int(sample.get("sample_size") or 0),
                        "confidence_95_pct": [
                            float(item.get("ci95_low_pct") or 0.0),
                            float(item.get("ci95_high_pct") or 0.0),
                        ],
                        "source": f"{path} (unrated-classification workstream)",
                    }
                )
            if not classes:
                continue
            return {
                "source": str(path),
                "sample_size": int(sample.get("sample_size") or 0),
                "population_measured": bool(sample.get("total_is_measured_full_population")),
                "class_map": UNRATED_RAW_CLASS_MAP,
                "cross_check": sample.get("ledger_full_population_cross_check"),
                "classes": classes,
                "basis": (
                    "classes estimated from the workstream's sample and cross-checked against its "
                    "measured full-population figures; counts are not measured per class"
                ),
                "generated_at": payload.get("generated_at"),
            }
        return {
            "source": str(path),
            "sample_size": int(sample_size or 0),
            "population_measured": bool(sample.get("total_is_measured_full_population")),
            "class_map": UNRATED_RAW_CLASS_MAP,
            "classes": [
                {
                    "class": UNRATED_RAW_CLASS_MAP.get(name, "unknown"),
                    "raw_class": name,
                    "estimate": int(round((observed / total_sample) * count)) if total_sample else 0,
                    "observed_in_sample": observed,
                    "estimator": "sample share applied to the measured population",
                    "sample_size": total_sample,
                    "confidence_95_pct": list(wilson_interval(observed, total_sample)),
                    "source": f"{path} (per-member evidence)",
                }
                for name, observed in sorted(tallies.items(), key=lambda item: -item[1])
            ],
            "basis": "classes tallied from the workstream's per-member evidence",
            "generated_at": payload.get("generated_at"),
        }
    return {
        "source": None,
        "sample_size": 0,
        "classes": [
            {
                "class": "unknown",
                "estimate": count,
                "observed_in_sample": None,
                "estimator": None,
                "sample_size": 0,
                "confidence_95_pct": None,
                "source": f"no classification evidence file found in {out_dir}",
            }
        ],
        "basis": "no classification evidence file present; classes are reported as unknown rather than guessed",
    }


# ---------------------------------------------------------------------------
# gathering everything into one report payload
# ---------------------------------------------------------------------------
def gather(
    conn,
    *,
    now: datetime,
    window_hours: int,
    out_dir: Path,
    cache_dir: Path,
    run_history: dict[str, Any],
    snapshot: DirectorySnapshot,
    classify: Callable[..., dict[str, Any]],
    detail_fetcher: Callable[[str], dict[str, Any]],
    attest: dict[str, Any],
    cadence: dict[str, Any],
    cadence_change: datetime | None,
    previous: dict[str, Any],
) -> dict[str, Any]:
    window_start = now - timedelta(hours=window_hours)
    coverage_window_end = now
    coverage_window_start = now - COVERAGE_WINDOW
    cur = conn.cursor()

    status_rows: dict[str, int] = {}
    cur.execute("SELECT status, count(*) FROM care_providers GROUP BY 1")
    for status, count in cur.fetchall():
        status_rows[str(status or "UNKNOWN")] = int(count)
    providers_total = sum(status_rows.values())

    cur.execute(
        """
        SELECT count(*) FILTER (WHERE region IS NULL OR btrim(region) = '') AS no_region,
               count(*) FILTER (WHERE local_authority IS NULL OR btrim(local_authority) = '') AS no_local_authority,
               count(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) AS no_geocode,
               count(*) FILTER (WHERE postcode IS NULL OR btrim(postcode) = '') AS no_postcode,
               count(*) FILTER (WHERE overall_rating IS NULL OR btrim(overall_rating) = '') AS no_overall_rating
        FROM care_providers WHERE status = 'ACTIVE'
        """
    )
    gaps = {key: int(value or 0) for key, value in _as_row_dict(cur).items()}

    ids = db_ids_by_status(conn)
    active_ids = ids.get("ACTIVE", frozenset())
    unrated_count = gaps.get("no_overall_rating", 0)
    unrated = {
        "count": unrated_count,
        "active": len(active_ids),
        "pct_of_active": _pct(unrated_count, len(active_ids)),
        "rendered": _ratio(unrated_count, len(active_ids)),
        "predicate": "care_providers.status = 'ACTIVE' AND (overall_rating IS NULL OR btrim(overall_rating) = '')",
        "source": "care_providers (direct count over the whole active population, not a sample)",
        "classification": load_unrated_classification(out_dir, count=unrated_count),
    }

    newest_signal = scalar(cur, "SELECT max(observed_at) FROM trusted_event_ledger")
    cur.execute(
        """
        SELECT event_type, count(*) AS events FROM trusted_event_ledger
        WHERE observed_at > %s GROUP BY 1 ORDER BY 2 DESC
        """,
        (window_start,),
    )
    changes_by_type = {str(name): int(count) for name, count in cur.fetchall()}
    changes_total = sum(changes_by_type.values())
    cur.execute(
        """
        SELECT coalesce(old_value::text, '(none)') AS old_value, coalesce(new_value::text, '(none)') AS new_value, count(*) AS events
        FROM trusted_event_ledger
        WHERE event_type = 'status_changed' AND observed_at > %s
        GROUP BY 1, 2 ORDER BY 3 DESC
        """,
        (window_start,),
    )
    transitions = {
        f"{str(old).strip(chr(34))}->{str(new).strip(chr(34))}": int(count) for old, new, count in cur.fetchall()
    }

    cur.execute(
        """
        SELECT count(*) AS rewritten,
               count(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM trusted_event_ledger e
                   WHERE e.location_id = care_providers.id
                     AND e.observed_at > %s
               )) AS rewritten_with_location_event,
               count(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM trusted_event_ledger e
                   WHERE e.provider_id = care_providers.provider_id
                     AND e.observed_at > %s
               )) AS rewritten_with_provider_event
        FROM care_providers
        WHERE updated_at > %s
        """,
        (window_start, window_start, window_start),
    )
    churn_row = _as_row_dict(cur)
    cur.execute("SELECT count(*) FROM trusted_event_ledger WHERE observed_at > %s", (window_start,))
    ledger_events_window = int(scalar(cur, "SELECT count(*) FROM trusted_event_ledger WHERE observed_at > %s", (window_start,)) or 0)
    rows_rewritten = int(churn_row["rewritten"] or 0)
    with_location_event = int(churn_row["rewritten_with_location_event"] or 0)
    churn = {
        "rows_rewritten": rows_rewritten,
        "rows_rewritten_with_location_event": with_location_event,
        "rows_rewritten_without_location_event": rows_rewritten - with_location_event,
        "rows_rewritten_with_provider_scope_event": int(churn_row["rewritten_with_provider_event"] or 0),
        "ledger_events_in_window": ledger_events_window,
        "window_start": _iso(window_start),
        "source": (
            "care_providers.updated_at (rewrites) vs trusted_event_ledger.observed_at / .location_id "
            "(recorded changes)"
        ),
        "note": (
            "a rewritten row is refresh activity, not evidence that CQC published anything; "
            "the ledger is the only change evidence this pipeline records, so a rewrite with no "
            "location-level event is labelled 'no recorded change' rather than 'no change'"
        ),
    }

    cur.execute(
        """
        SELECT run_type, status, count(*) AS runs FROM pipeline_runs
        WHERE started_at > %s GROUP BY 1, 2 ORDER BY 3 DESC
        """,
        (window_start,),
    )
    runs_by_type: dict[str, dict[str, int]] = {}
    for run_type, status, count in cur.fetchall():
        runs_by_type.setdefault(str(run_type), {})[str(status)] = int(count)

    cur.execute(
        """
        SELECT run_type, started_at, left(coalesce(error_message, ''), 160) AS error
        FROM pipeline_runs
        WHERE started_at > %s AND status NOT IN ('completed', 'running')
        ORDER BY started_at DESC LIMIT 10
        """,
        (window_start,),
    )
    failures_in_window = [
        {"run_type": str(run_type), "started_at": _iso(started_at), "error": str(error or "")}
        for run_type, started_at, error in cur.fetchall()
    ]

    cur.execute(
        """
        SELECT count(*) FILTER (WHERE status = 'completed') AS completed, count(*) AS total
        FROM pipeline_runs WHERE run_type = 'signal_poll' AND started_at > %s
        """,
        (coverage_window_start,),
    )
    db_poll_row = _as_row_dict(cur)
    cur.execute(
        """
        SELECT count(*) AS total,
               count(*) FILTER (WHERE run_type = 'reconciliation') AS reconciliation
        FROM pipeline_runs WHERE started_at > %s
        """,
        (coverage_window_start,),
    )
    db_all_row = _as_row_dict(cur)

    cur.execute(
        """
        SELECT id, source_uri, source_published_at, source_checksum_sha256, location_count,
               created_at, completed_at, active_records_before, active_records_after, records_deactivated
        FROM reconciliation_batches WHERE status = 'completed'
        ORDER BY completed_at DESC NULLS LAST LIMIT 1
        """
    )
    batch = cur.fetchone()
    last_run: dict[str, Any] | None = None
    if batch:
        (
            batch_id,
            source_uri,
            source_published_at,
            source_checksum,
            location_count,
            created_at,
            completed_at,
            active_before,
            active_after,
            deactivated,
        ) = batch
        last_run = {
            "batch_id": str(batch_id),
            "source_uri": source_uri,
            "source_published_at": str(source_published_at) if source_published_at else None,
            "source_checksum_sha256": source_checksum,
            "location_count": int(location_count or 0),
            "created_at": _iso(created_at),
            "completed_at": _iso(completed_at),
            "active_records_before": active_before,
            "active_records_after": active_after,
            "records_deactivated": deactivated,
            "age_hours": _hours(hours_between(completed_at, now)) if completed_at else None,
            "source": "reconciliation_batches WHERE status = 'completed' ORDER BY completed_at DESC",
        }

    cur.execute(
        """
        SELECT id, source_published_at, status, created_at, completed_at,
               left(coalesce(error_message, ''), 200) AS error
        FROM reconciliation_batches WHERE status <> 'completed'
        ORDER BY created_at DESC LIMIT 1
        """
    )
    failed_batch_row = cur.fetchone()
    failed_batch: dict[str, Any] | None = None
    shard_evidence: dict[str, Any] | None = None
    if failed_batch_row:
        f_id, f_published, f_status, f_created, f_completed, f_error = failed_batch_row
        failed_batch = {
            "batch_id": str(f_id),
            "source_published_at": str(f_published) if f_published else None,
            "status": str(f_status),
            "created_at": _iso(f_created),
            "completed_at": _iso(f_completed),
            "recorded_error": f_error,
            "source": "reconciliation_batches (newest non-completed batch)",
        }
        cur.execute(
            "SELECT status, count(*) FROM reconciliation_shards WHERE batch_id = %s GROUP BY 1",
            (f_id,),
        )
        shard_evidence = {
            "shards_by_status": {str(status): int(count) for status, count in cur.fetchall()},
            "source": "reconciliation_shards grouped by status",
            "note": (
                "the DB error_message is a generic wrapper written when the workflow ends; it is not the reason "
                "the batch was refused (see attested_cause)"
            ),
        }
    cur.close()

    # ---- polling coverage -------------------------------------------------
    schedules = [parse_cron(expr) for expr in cadence["expressions"]]
    if run_history.get("status") == "ok":
        coverage = poll_coverage(
            run_history["runs"],
            schedules=schedules,
            window_start=coverage_window_start,
            window_end=coverage_window_end,
            now=now,
            cadence_change=cadence_change,
        )
        coverage["available"] = True
        coverage["source"] = run_history.get("command")
    else:
        coverage = coverage_unavailable(
            run_history.get("reason"),
            schedules=schedules,
            window_start=coverage_window_start,
            window_end=coverage_window_end,
            now=now,
        )
        coverage["source"] = "unavailable"
    coverage["db_cross_check"] = {
        "window": {"start": _iso(coverage_window_start), "end": _iso(coverage_window_end)},
        "db_signal_poll_completed": int(db_poll_row["completed"] or 0),
        "db_signal_poll_total_rows": int(db_poll_row["total"] or 0),
        "db_all_run_types_rows": int(db_all_row["total"] or 0),
        "db_reconciliation_rows": int(db_all_row["reconciliation"] or 0),
        "source": "pipeline_runs WHERE run_type = 'signal_poll' (started_at window)",
        "reconciliation": None,
    }
    gh_attempted = coverage["attempted"]["runs"]
    db_total = coverage["db_cross_check"]["db_signal_poll_total_rows"]
    if gh_attempted is None:
        coverage["db_cross_check"]["reconciliation"] = (
            f"GitHub Actions history is unavailable ({coverage.get('reason')}), so no expected-vs-attempted comparison "
            f"is made; the DB holds {db_total} signal_poll row(s) in this window, and DB rows cannot distinguish "
            "scheduled from manual runs or report a conclusion for polls"
        )
    else:
        coverage["db_cross_check"]["reconciliation"] = (
            f"GitHub Actions attempted {gh_attempted}, DB pipeline_runs holds {db_total} row(s) in the same window "
            f"({db_total - gh_attempted:+d}); the DB cannot distinguish scheduled from manual runs and records no "
            "conclusion for polls, so GitHub Actions is the authority for the buckets above"
        )

    # ---- alignment --------------------------------------------------------
    diff = None
    summary: dict[str, Any] | None = None
    classifications: dict[str, dict[str, Any] | None] = {}
    splits: dict[str, dict[str, Any]] = {}
    per_side_summaries: dict[str, dict[str, Any]] = {}
    snapshot_dict = snapshot.as_dict()
    SIDES = (
        ("only_in_db_active", "db_active_absent_from_source", "divergent-db-active.json"),
        ("source_but_db_inactive", "source_present_db_inactive", "source-inactive-vs-db.json"),
        ("only_in_source", "source_absent_from_db", "source-only.json"),
    )
    if snapshot.coverage != "unavailable":
        diff = identifier_diff(ids, snapshot.ids)
        for key, side, filename in SIDES:
            population = sorted(diff[key])
            if not population:
                classifications[key] = None
                splits[key] = {
                    "coverage": "full",
                    "classified": 0,
                    "population": 0,
                    "confirmed_defect": 0,
                    "legitimate_timing_or_scope": 0,
                    "unexplained": 0,
                    "source": "empty population: nothing to classify",
                }
                per_side_summaries[key] = {
                    "confirmed_defect": 0,
                    "legitimate_timing_or_scope": 0,
                    "unexplained": 0,
                    "defect_classes": {},
                    "legitimate_classes": {},
                    "unexplained_classes": {},
                    "coverage": "full",
                    "source": "empty population: nothing to classify",
                }
                continue
            classification = classify(
                population,
                side=side,
                snapshot_published_at=snapshot.published_at,
                fetch_detail=detail_fetcher,
                cache_path=cache_dir / filename,
            )
            classifications[key] = classification
            splits[key] = split_counts(classification, population, side=side)
            per_side_summaries[key] = summarize_classification(classification)
        summary = merge_summaries(per_side_summaries)

    alignment = None
    if diff is not None:
        alignment = {
            "snapshot": snapshot_dict,
            "diff": {key: value for key, value in diff.items() if not isinstance(value, list)},
            "diff_sets": {
                "only_in_db_active": len(diff["only_in_db_active"]),
                "only_in_source": len(diff["only_in_source"]),
                "source_but_db_inactive": len(diff["source_but_db_inactive"]),
                "only_in_db_inactive": len(diff["only_in_db_inactive"]),
            },
            "only_in_db_active_split": splits["only_in_db_active"],
            "source_but_db_inactive_split": splits["source_but_db_inactive"],
            "only_in_source_split": splits["only_in_source"],
            "definitions": diff["definitions"],
            "count_vs_count_context": {
                "db_active": len(active_ids),
                "last_validated_snapshot_count": (last_run or {}).get("location_count"),
                "delta": (
                    len(active_ids) - int((last_run or {}).get("location_count") or 0)
                    if last_run and last_run.get("location_count")
                    else None
                ),
                "note": (
                    "counts across different publications are not a match signal: a count difference disappears "
                    "against the newer snapshot and says nothing about identifiers. The identifier diff above is "
                    "the authority."
                ),
            },
            "coverage": snapshot.coverage,
            "scope": (
                f"snapshot {snapshot.published_at or 'unknown date'} ({snapshot.coverage}), "
                f"{len(snapshot.ids):,} source IDs vs {len(active_ids):,} DB ACTIVE IDs"
            ),
        }
        alignment["classification_summary"] = summary
        alignment["classifications"] = {
            key: (
                {name: value for name, value in classification.items() if name != "per_id"}
                if classification
                else {"coverage": "not_applicable", "source": "empty population"}
            )
            for key, classification in classifications.items()
        }
        problems: list[str] = []
        for key, classification in classifications.items():
            if classification is not None:
                problems.extend(
                    f"{key}: {problem}" for problem in reconciliation_inputs_are_complete(diff, classification)
                )
        alignment["incompleteness"] = problems

    ingested = None
    if last_run:
        newest_snapshot_covered = bool(
            snapshot.published_at and last_run.get("source_published_at") == snapshot.published_at
        )
        ingested = {
            "latest_covered_batch_id": last_run["batch_id"],
            "latest_covered_published_at": last_run["source_published_at"],
            "latest_covered_checksum": last_run["source_checksum_sha256"],
            "latest_covered_completed_at": last_run["completed_at"],
            "latest_covered_age_hours": last_run["age_hours"],
            "newest_available_published_at": snapshot.published_at,
            "newest_snapshot_covered": newest_snapshot_covered,
            "source": "reconciliation_batches (completed) vs the snapshot fetched above",
        }

    # ---- freshness --------------------------------------------------------
    def source_age(published_at: str | None) -> dict[str, Any] | None:
        if not published_at:
            return None
        try:
            published = datetime.fromisoformat(published_at).replace(tzinfo=UTC)
        except ValueError:
            return None
        age = hours_between(published, now)
        return {
            "published_at": published_at,
            "age_hours": _hours(age),
            "sla_hours": FRESHNESS_SLA.total_seconds() / 3600,
            "sla_citation": FRESHNESS_SLA_CITATION,
            "within_sla": age <= FRESHNESS_SLA.total_seconds() / 3600,
            "age_convention": "measured from 00:00 UTC on the publication date",
            "source": "CQC directory publication date (from the CSV preamble) / reconciliation_batches.source_published_at",
        }

    signal_age_hours = _hours(hours_between(newest_signal, now)) if newest_signal else None
    freshness = {
        "signal": {
            "observed_at": _iso(newest_signal),
            "age_hours": signal_age_hours,
            "sla_hours": SIGNAL_POLL_FRESHNESS_SLA.total_seconds() / 3600,
            "sla_citation": SIGNAL_POLL_FRESHNESS_CITATION,
            "within_sla": (
                signal_age_hours is not None
                and signal_age_hours <= SIGNAL_POLL_FRESHNESS_SLA.total_seconds() / 3600
            ),
            "source": "trusted_event_ledger.max(observed_at)",
        },
        "newest_available_source": source_age(snapshot.published_at),
        "ingested_source": source_age((last_run or {}).get("source_published_at")),
    }

    sweep = None
    observed_sweep = None
    if snapshot.ids:
        sweep = sweep_coverage(len(snapshot.ids), runs_per_week=cadence["runs_per_week"], sweep_size=cadence["sweep_size"])
        if coverage:
            observed_runs = coverage["attempted"]["runs"]
            observed_sweep = sweep_coverage(
                len(snapshot.ids),
                runs_per_week=max(1, observed_runs),
                sweep_size=cadence["sweep_size"],
            )

    verdicts = build_verdicts(
        snapshot=snapshot_dict,
        diff=None if diff is None else {key: value for key, value in diff.items() if not isinstance(value, list)},
        summary=summary,
        ingested=ingested,
        coverage=coverage,
        sweep=sweep,
        observed_sweep=observed_sweep,
        freshness=freshness,
        run_history_status=run_history.get("status", "unavailable"),
        drift_notes=cadence.get("drift_notes") or [],
    )

    directory_snapshot_changed = bool(
        snapshot.sha256 and previous.get("directory_snapshot_sha256") and snapshot.sha256 != previous["directory_snapshot_sha256"]
    )

    return {
        "report_version": REPORT_VERSION,
        "generated_at": _iso(now),
        "window_hours": window_hours,
        "window_start": _iso(window_start),
        "coverage_window": {
            "start": _iso(coverage_window_start),
            "end": _iso(coverage_window_end),
            "hours": round(hours_between(coverage_window_start, coverage_window_end), 1),
        },
        "cadence": cadence,
        "providers_total": providers_total,
        "provider_status": status_rows,
        "quality_gaps": gaps,
        "ledger_newest": _iso(newest_signal),
        "ledger_newest_age_hours": signal_age_hours,
        "changes_total": changes_total,
        "changes_by_type": changes_by_type,
        "status_transitions": transitions,
        "rating_events": rating_event_completeness(conn, window_start),
        "unrated": unrated,
        "churn": churn,
        "polls": {
            "coverage": coverage,
            "source": "GitHub Actions (gh run list) with a DB cross-check on pipeline_runs",
        },
        "runs_by_type": runs_by_type,
        "failures_in_window": failures_in_window,
        "last_reconciliation_run": last_run,
        "last_failed_batch": failed_batch,
        "failed_batch_shard_evidence": shard_evidence,
        "attested_failure_cause": attest,
        "ingested": ingested,
        "alignment": alignment,
        "freshness": freshness,
        "sweep": sweep,
        "observed_sweep": observed_sweep,
        "directory_snapshot_changed": directory_snapshot_changed,
        "directory_snapshot_sha256": snapshot.sha256,
        "verdicts": verdicts,
    }


# ---------------------------------------------------------------------------
# findings and rendering
# ---------------------------------------------------------------------------
def findings(data: dict[str, Any]) -> list[str]:
    """Reasons this night deserves attention. Each names its class."""
    out: list[str] = []
    verdicts = data.get("verdicts") or {}
    align = verdicts.get("data_alignment") or {}
    health = verdicts.get("pipeline_health") or {}
    if align.get("verdict") != VERDICT_MATCHED:
        out.append(f"[data alignment] {align.get('verdict')}: " + "; ".join(align.get("reasons") or []))
    if health.get("verdict") != VERDICT_MATCHED:
        out.append(f"[pipeline health] {health.get('verdict')}: " + "; ".join(health.get("reasons") or []))
    rating = (data.get("rating_events") or {}).get("all_time") or {}
    if rating.get("no_destination_value"):
        out.append(
            "[representation gap] rating_changed events with no destination value: "
            + rating["rendered"]["no_destination_value"]
            + " all time, "
            + ((data["rating_events"]["window"] or {}).get("rendered", {}).get("no_destination_value") or "n/a")
            + " in this window - excluded from customer-facing movement claims"
        )
    unrated = data.get("unrated") or {}
    classes = (unrated.get("classification") or {}).get("classes") or []
    unknown = sum(int(item.get("estimate") or 0) for item in classes if item.get("class") == "unknown")
    if unknown:
        out.append(
            f"[unrated population] {int(unrated.get('count') or 0):,} ACTIVE rows without a published overall rating; "
            f"{unknown:,} unclassified (unknown) - classification evidence missing"
        )
    if data.get("directory_snapshot_changed"):
        out.append("[source movement] CQC published a new directory snapshot since the previous run (checksum changed)")
    return out


def render(data: dict[str, Any]) -> str:
    verdicts = data["verdicts"]
    align = verdicts["data_alignment"]
    health = verdicts["pipeline_health"]
    coverage = data["polls"]["coverage"]
    cadence = data["cadence"]
    lines: list[str] = [
        f"# CareGist nightly CQC check - {data['generated_at'][:16].replace('T', ' ')} UTC",
        "",
        "Read-only. Data alignment and pipeline health are reported as separate verdicts.",
        "",
        "## Verdicts",
        "",
        f"- **DATA ALIGNMENT: {align['verdict']}** - " + "; ".join(align.get("reasons") or []),
        f"- **PIPELINE HEALTH: {health['verdict']}** - " + "; ".join(health.get("reasons") or []),
        "",
        "Verdict vocabulary: "
        + "; ".join(f"`{name}` = {text}" for name, text in verdicts["vocabulary"].items())
        + ".",
        "",
        "## Polling coverage",
        "",
        f"- Window: {coverage['window']['start']} -> {coverage['window']['end']} "
        f"({coverage['window']['hours']}h), grace {coverage['grace_minutes']}m",
        f"- Expected: **{coverage['expected']['runs']}** - derived from cron "
        + ", ".join(f"`{expr}`" for expr in cadence["expressions"])
        + f" = {cadence['runs_per_day']}/day x 7 = {cadence['runs_per_week']}/week "
        f"({cadence['source']}); {coverage['expected']['due']} due, "
        f"{coverage['expected']['not_yet_due']} not yet due",
    ]
    if coverage.get("available", True):
        lines += [
            f"- Attempted: **{coverage['attempted']['runs']}** scheduled runs - {coverage['attempted']['source']}",
            f"- Successful: **{coverage['successful']['runs']}** - {coverage['successful']['source']}",
            f"- Failed: **{coverage['failed']['runs']}** - {coverage['failed']['source']}"
            + (f" {coverage['failed']['by_conclusion']}" if coverage["failed"]["by_conclusion"] else ""),
            f"- Missed: **{coverage['missed']['runs']}** - {coverage['missed']['definition']} "
            f"(source: {coverage['missed']['source']}); no coverage is claimed for a period that has not elapsed",
            f"- Cancelled {coverage['cancelled']['runs']} (not counted as failed); "
            f"in flight {coverage['in_flight']['runs']}; "
            f"manual or other-event runs {coverage['attempted']['manual_or_other_event_runs']}",
        ]
    else:
        lines += [
            f"- Attempted / Successful / Failed / Missed: **not assertable** - "
            f"{coverage.get('reason')}. The four delivered buckets are reported as unknown, not as zero.",
        ]
    lines += [
        f"- DB cross-check ({coverage['db_cross_check']['source']}, same window): "
        f"{coverage['db_cross_check']['db_signal_poll_completed']} completed / "
        f"{coverage['db_cross_check']['db_signal_poll_total_rows']} rows. {coverage['db_cross_check']['reconciliation']}",
    ]
    if coverage.get("available", True):
        lines += [
            f"- Delivered: {_ratio(coverage['attempted']['runs'], coverage['expected']['due'])} of due fires attempted, "
            f"{_ratio(coverage['successful']['runs'], coverage['expected']['due'])} succeeded",
            f"- Diagnostic: {coverage['fires_without_a_matching_run']['runs']} due fire(s) had no run created within "
            f"{cadence['match_window_hours']:g}h - {coverage['fires_without_a_matching_run']['definition']}",
        ]
    if coverage.get("cadence_change"):
        change = coverage["cadence_change"]
        lines.append(
            f"- Cadence change at {change['at']} ({change['source']}): this window spans two schedules - "
            f"post-change expected {change['expected_runs']} fire(s), {change['due']} due, "
            f"{change['attempted']} attempted, {change['missed']} missed. {change['note']}"
        )
    if data.get("unexpected_extra"):
        lines.append(f"- {data['unexpected_extra']}")
    if cadence.get("drift_notes"):
        lines.append(f"- **Cadence drift**: {'; '.join(cadence['drift_notes'])}")
    if data.get("sweep"):
        sweep = data["sweep"]
        lines.append(
            f"- Sweep arithmetic: {sweep['arithmetic']}; documented promise {sweep['sla_days']:g} day(s) -> "
            f"**{'met' if sweep['meets_sla'] else 'BREACH'}**; needs >= {sweep['min_runs_per_week_for_sla']} runs/week "
            f"at sweep size {sweep['sweep_size']:,}"
        )
    if data.get("observed_sweep"):
        observed = data["observed_sweep"]
        lines.append(
            f"- Sweep at the measured cadence: {observed['arithmetic']} -> "
            f"{'met' if observed['meets_sla'] else 'BREACH'}"
        )

    freshness = data["freshness"]
    lines += [
        "",
        "## Freshness (documented thresholds, cited)",
        "",
        f"- Newest CQC signal observed: {data.get('ledger_newest') or 'never'} "
        f"({freshness['signal']['age_hours']}h ago) against {freshness['signal']['sla_citation']} -> "
        f"{'within' if freshness['signal']['within_sla'] else '**BREACH**'}",
    ]
    if freshness.get("newest_available_source"):
        item = freshness["newest_available_source"]
        lines.append(
            f"- Newest available source snapshot: published {item['published_at']} "
            f"({item['age_hours']}h ago, {item['age_convention']}) against {item['sla_citation']} -> "
            f"{'within' if item['within_sla'] else '**BREACH**'}"
        )
    if freshness.get("ingested_source"):
        item = freshness["ingested_source"]
        lines.append(
            f"- Validated (ingested) source snapshot: published {item['published_at']} "
            f"({item['age_hours']}h ago) against the same {item['sla_hours']:g}h promise -> "
            f"{'within' if item['within_sla'] else '**BREACH**'}"
        )

    alignment = data.get("alignment")
    lines += ["", "## Data alignment: identifier-level reconciliation", ""]
    if not alignment:
        lines.append("- Not reconciled: the newest available directory snapshot could not be fetched "
                     f"({(data['alignment'] or {}).get('error', 'no snapshot')}).")
    else:
        snap = alignment["snapshot"]
        lines += [
            f"- Snapshot: {snap['uri']}",
            f"  published {snap['published_at']}, retrieved {snap['retrieved_at']}, sha256 "
            f"{snap['sha256'] or 'withheld'}, {snap['entity_count']:,} IDs, coverage **{snap['coverage']}**"
            + (f" - {snap['note']}" if snap.get("note") else ""),
            f"- Latest successful reconciliation run: batch {data['last_reconciliation_run']['batch_id']} "
            f"source {data['last_reconciliation_run']['source_published_at']} "
            f"checksum {str(data['last_reconciliation_run']['source_checksum_sha256'])[:12]}... "
            f"completed {data['last_reconciliation_run']['completed_at']} "
            f"({data['last_reconciliation_run']['age_hours']}h ago, "
            f"{data['last_reconciliation_run']['source']})"
            if data.get("last_reconciliation_run")
            else "- Latest successful reconciliation run: none",
        ]
        if data.get("ingested"):
            ingested = data["ingested"]
            lines.append(
                f"- Newest available snapshot covered by a reconciliation batch: "
                f"**{'yes' if ingested['newest_snapshot_covered'] else 'no'}** "
                f"(latest covered publication {ingested['latest_covered_published_at']})"
            )
        lines += [
            f"- Database identifiers: {alignment['diff']['db_active']:,} ACTIVE / "
            f"{alignment['diff']['db_inactive']:,} INACTIVE",
            f"- Overlap: {_ratio(alignment['diff']['overlap'], alignment['diff']['db_active'] + alignment['diff']['db_inactive'])} "
            f"of CareGist rows ({alignment['diff']['overlap_active']:,} ACTIVE, {alignment['diff']['overlap_inactive']:,} INACTIVE)",
            f"- Only in DB and ACTIVE: **{alignment['diff_sets']['only_in_db_active']:,}**",
            f"  confirmed defect "
            f"{(alignment['only_in_db_active_split'] or {}).get('confirmed_defect')} vs legitimate timing/scope "
            f"{(alignment['only_in_db_active_split'] or {}).get('legitimate_timing_or_scope')} "
            f"(source: {alignment['only_in_db_active_split']['source'] if alignment.get('only_in_db_active_split') else 'unavailable'})",
            f"- Only in source: **{alignment['diff_sets']['only_in_source']:,}**",
            f"- Source present but DB INACTIVE: **{alignment['diff_sets']['source_but_db_inactive']:,}**",
            f"  confirmed defect "
            f"{(alignment['source_but_db_inactive_split'] or {}).get('confirmed_defect')} vs legitimate "
            f"{(alignment['source_but_db_inactive_split'] or {}).get('legitimate_timing_or_scope')}",
            f"- DB INACTIVE and absent from the snapshot (expected, informational): "
            f"{alignment['diff_sets']['only_in_db_inactive']:,}",
        ]
        for side_key, label in (
            ("only_in_db_active", "only-in-DB-ACTIVE"),
            ("source_but_db_inactive", "source-present-DB-INACTIVE"),
        ):
            info = (alignment.get("classifications") or {}).get(side_key) or {}
            lines.append(
                f"- {label} classification: coverage {info.get('coverage', 'not run')} "
                f"({info.get('classified', 0):,} of {info.get('population', 0):,} IDs, cap {info.get('cap')}, "
                f"source: {info.get('source', 'n/a')})"
            )
        for problem in alignment.get("incompleteness") or []:
            lines.append(f"  - completeness caveat: {problem}")
        context = alignment["count_vs_count_context"]
        delta = context.get("delta")
        if delta is not None:
            lines.append(
                f"- Count-vs-count context (not a match signal): {context['db_active']:,} DB ACTIVE vs "
                f"{context['last_validated_snapshot_count']:,} in the last validated snapshot "
                f"({delta:+,} in that comparison). {context['note']}"
            )
        else:
            lines.append(f"- Count-vs-count context: not computable. {context['note']}")
        if alignment.get("classification_summary"):
            summary = alignment["classification_summary"]
            lines.append(
                f"- Class split: {summary['confirmed_defect']} confirmed defect, "
                f"{summary['legitimate_timing_or_scope']} legitimate timing/scope, "
                f"{summary['unexplained']} unexplained"
            )

    rating = data["rating_events"]
    lines += [
        "",
        "## Rating-event completeness (numerator over denominator, per window)",
        "",
        f"- Window ({rating['window']['start']} -> report time): no destination value "
        f"{rating['window']['rendered']['no_destination_value']}; sentinel destination "
        f"{rating['window']['rendered']['sentinel_destination']}; real published destination "
        f"{rating['window']['rendered']['real_destination']}",
        f"- All time ({rating['all_time']['start']} -> {rating['all_time']['end']}): no destination value "
        f"{rating['all_time']['rendered']['no_destination_value']}; sentinel destination "
        f"{rating['all_time']['rendered']['sentinel_destination']}; real published destination "
        f"{rating['all_time']['rendered']['real_destination']}",
        f"- Prior-value sentinel: {rating['all_time']['rendered']['old_value_sentinel']} of rating_changed events "
        "carry a sentinel old_value (not a rating)",
        f"- Unresolved events with a sentinel prior value ({rating['unresolved_detail']['definition']}): "
        f"{rating['unresolved_detail']['rendered']} = "
        f"{rating['unresolved_detail']['unresolved_with_sentinel_prior_value']:,} of "
        f"{rating['unresolved_detail']['unresolved']:,} "
        f"(sentinel values: {rating['unresolved_detail']['sentinel_values']}). "
        f"{rating['unresolved_detail']['note']}",
        f"- Customer-facing scope: {rating['customer_facing_scope']}",
        f"- Predicate: {rating['predicate']}",
        "- Representation classes:",
    ]
    for name, description in rating["representation_classes"].items():
        lines.append(f"  - `{name}`: {description}")
    lines.append(
        "- Real published destination values (all time): "
        + (", ".join(f"{name} {count:,}" for name, count in rating["real_destination_values"].items()) or "none")
    )

    unrated = data["unrated"]
    classification = unrated["classification"]
    lines += [
        "",
        "## Unrated population",
        "",
        f"- ACTIVE rows without a published overall rating: **{unrated['rendered']}** of active "
        f"({unrated['source']})",
        f"- Predicate: `{unrated['predicate']}`",
        f"- Classification basis: {classification['basis']} (source: {classification['source']})",
    ]
    for item in classification["classes"]:
        confidence = (
            f", 95% interval {item['confidence_95_pct'][0]}-{item['confidence_95_pct'][1]}%"
            if item.get("confidence_95_pct")
            else ""
        )
        sample = f", sample {item.get('sample_size')}" if item.get("sample_size") else ""
        observed = (
            f"observed {item['observed_in_sample']} in the sample" if item.get("observed_in_sample") is not None else "not sampled"
        )
        # "~" only where the figure is an estimate; a measured class is stated exactly.
        marker = "~" if item.get("estimator") else ""
        raw = item.get("raw_class")
        raw_note = f" [workstream class `{raw}`]" if raw and raw != item["class"] else ""
        lines.append(
            f"  - {item['class']}: {marker}{int(item.get('estimate') or 0):,} "
            f"({observed}{sample}{confidence}; {item.get('source')}){raw_note}"
        )

    lines += [
        "",
        "## Refresh churn - reported separately from genuine source change",
        "",
        f"- Rows rewritten in the window: {data['churn']['rows_rewritten']:,} "
        f"({data['churn']['source']})",
        f"- Of those, rows with a location-level recorded change in the same window: "
        f"{data['churn']['rows_rewritten_with_location_event']:,}; "
        f"rows with no recorded change (churn): "
        f"**{data['churn']['rows_rewritten_without_location_event']:,}**",
        f"- Wider, provider-scope attribution (for contrast only - a provider holds many locations): "
        f"{data['churn']['rows_rewritten_with_provider_scope_event']:,}",
        f"- Recorded changes (ledger events) in the same window: {data['churn']['ledger_events_in_window']:,}",
        f"- {data['churn']['note']}",
    ]

    lines += ["", f"## Changes observed in the window ({data['changes_total']:,} events)", ""]
    if data["changes_by_type"]:
        for event_type, count in data["changes_by_type"].items():
            lines.append(f"- {event_type.replace('_', ' ')}: {count:,}")
    else:
        lines.append("- None.")
    if data["status_transitions"]:
        lines.append(
            "- Status transitions: " + ", ".join(f"{name} {count:,}" for name, count in data["status_transitions"].items())
        )

    lines += [
        "",
        f"## Pipeline runs in the change window ({data['window_hours']}h to {data['window_start']})",
        "",
        "- Window differs from the 7-day polling-coverage window above; the two are never added together",
    ]
    for run_type, statuses in data["runs_by_type"].items():
        lines.append(f"- {run_type}: " + ", ".join(f"{status} {count:,}" for status, count in statuses.items()))
    if data["failures_in_window"]:
        for failure in data["failures_in_window"]:
            lines.append(f"- failure: {failure['run_type']} at {failure['started_at']} - {failure['error']}")
    if data.get("last_failed_batch"):
        batch = data["last_failed_batch"]
        lines.append(
            f"- Failed reconciliation batch {batch['batch_id']} (source publication {batch['source_published_at']}, "
            f"created {batch['created_at']}, {batch['source']}): recorded error "
            f"{batch['recorded_error'] or '(none)'}"
        )
    if data.get("failed_batch_shard_evidence"):
        evidence = data["failed_batch_shard_evidence"]
        lines.append(
            f"  - shard evidence: {evidence['shards_by_status']} - {evidence['note']}"
        )
    if data.get("attested_failure_cause"):
        attest = data["attested_failure_cause"]
        if attest.get("status") == "attested":
            lines.append(
                f"  - attested cause ({attest['source']}): \"{attest['line']}\""
            )
        else:
            lines.append(f"  - attested cause: not available ({attest.get('status')}: {attest.get('reason')})")

    if data.get("quality_gaps"):
        lines += ["", "## Data quality gaps (ACTIVE rows)", ""]
        for name, count in data["quality_gaps"].items():
            if count and name != "no_overall_rating":
                lines.append(f"- {name.replace('_', ' ')}: {count:,} ({_pct(count, data['provider_status'].get('ACTIVE', 0))}%)")

    lines += [
        "",
        "## Sources",
        "",
        "- Poll buckets: GitHub Actions `gh run list --workflow=cqc-signal-poll.yml`; DB cross-check: `pipeline_runs`",
        f"- Expected cadence: {cadence['source']}",
        "- Snapshot identity and identifier diff: CQC directory CSV (streamed, sha256) vs `care_providers`",
        "- Divergent-ID classes: live CQC API location detail",
        "- Change counts: `trusted_event_ledger`; rewrites: `care_providers.updated_at`",
        f"- Thresholds: {PIPELINE_HEALTH_SOURCE} (never loosened here)",
        "",
    ]
    return "\n".join(lines)


def state_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_version": REPORT_VERSION,
        "generated_at": data["generated_at"],
        "providers_total": data["providers_total"],
        "changes_total": data["changes_total"],
        "directory_snapshot_sha256": data.get("directory_snapshot_sha256"),
        "verdicts": {
            "data_alignment": (data["verdicts"]["data_alignment"] or {}).get("verdict"),
            "pipeline_health": (data["verdicts"]["pipeline_health"] or {}).get("verdict"),
        },
        "ingested_source_published_at": (data.get("ingested") or {}).get("latest_covered_published_at"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--window-hours", type=int, default=24, help="change-event window (default 24)")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--no-remote", action="store_true", help="skip snapshot, API, and GitHub lookups")
    parser.add_argument("--live-index", action="store_true", help="accepted for compatibility; informational only")
    parser.add_argument("--refresh-snapshot", action="store_true", help="ignore the snapshot cache")
    parser.add_argument("--force-report", action="store_true", help="print the report even with no findings")
    parser.add_argument("--json", action="store_true", help="print the JSON payload instead of markdown")
    args = parser.parse_args(argv)

    now = datetime.now(UTC)
    out_dir = Path(args.out_dir)
    cache_dir = Path(os.getenv("CQC_NIGHTLY_CACHE_DIR") or (out_dir / "cache"))
    out_dir.mkdir(parents=True, exist_ok=True)
    previous = _load_json(out_dir / "state.json")

    cadence = derive_cadence(now=now)
    change_at_raw = cadence_change_at()
    cadence_change = None
    if change_at_raw:
        try:
            cadence_change = datetime.fromisoformat(change_at_raw.replace("Z", "+00:00"))
        except ValueError:
            cadence_change = None

    run_history: dict[str, Any] = {"status": "unavailable", "reason": "skipped (--no-remote)"}
    recon_history: dict[str, Any] = {"status": "unavailable", "reason": "skipped (--no-remote)"}
    snapshot = DirectorySnapshot(coverage="unavailable", error="skipped (--no-remote)", source="skipped")
    classify: Callable[..., dict[str, Any]] = classification_unavailable
    detail_fetcher: Callable[[str], dict[str, Any]] = lambda _location_id: {}
    attest: dict[str, Any] = {"status": "skipped", "reason": "skipped (--no-remote)"}

    if not args.no_remote:
        run_history = gh_run_list("cqc-signal-poll.yml", limit=100)
        recon_history = gh_run_list("cqc-reconciliation.yml", limit=30)
        snapshot = fetch_directory_snapshot(cache_dir=cache_dir, force=args.refresh_snapshot, now=now)
        helper = _incremental_update()
        api_key = helper.get_api_key()
        base_url = helper.DEFAULT_BASE_URL

        def _fetch(location_id: str) -> dict[str, Any]:
            return helper.fetch_location_detail(base_url, api_key, location_id)

        if api_key:
            detail_fetcher = _fetch
            cap_holder = {"cap": env_int("CQC_NIGHTLY_API_MAX_IDS", API_CLASSIFY_MAX_DEFAULT)}

            def _classify(ids, *, side, snapshot_published_at, fetch_detail, cache_path=None, **kwargs):  # noqa: ANN001
                return classify_divergent(
                    ids,
                    side=side,
                    snapshot_published_at=snapshot_published_at,
                    fetch_detail=fetch_detail,
                    cache_path=cache_path,
                    cap=cap_holder["cap"],
                )

            classify = _classify

    conn = psycopg2.connect(_database_url())
    try:
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, source_published_at, status, created_at, completed_at,
                   left(coalesce(error_message, ''), 200) AS error
            FROM reconciliation_batches WHERE status <> 'completed'
            ORDER BY created_at DESC LIMIT 1
            """
        )
        failed_batch_row = cur.fetchone()
        cur.close()
        failed_batch = None
        if failed_batch_row:
            failed_batch = {
                "id": str(failed_batch_row[0]),
                "source_published_at": str(failed_batch_row[1]) if failed_batch_row[1] else None,
                "status": str(failed_batch_row[2]),
                "created_at": _iso(failed_batch_row[3]),
                "completed_at": _iso(failed_batch_row[4]),
                "recorded_error": failed_batch_row[5],
            }
        if not args.no_remote:
            attest = attested_failure_cause(
                batch=failed_batch,
                run_history=recon_history,
                cache_path=cache_dir / "attested-causes.json",
            )
        data = gather(
            conn,
            now=now,
            window_hours=args.window_hours,
            out_dir=out_dir,
            cache_dir=cache_dir,
            run_history=run_history,
            snapshot=snapshot,
            classify=classify,
            detail_fetcher=detail_fetcher,
            attest=attest,
            cadence=cadence,
            cadence_change=cadence_change,
            previous=previous,
        )
    finally:
        conn.close()

    stamp = now.strftime("%Y-%m-%d")
    report_md = out_dir / f"{stamp}-report.md"
    report_json = out_dir / f"{stamp}-report.json"
    report_md.write_text(render(data))
    _write_json(report_json, data)
    _write_json(out_dir / "state.json", state_payload(data))

    notices = findings(data)
    print(
        f"CQC nightly check {data['verdicts']['data_alignment']['verdict']}"
        f"/{data['verdicts']['pipeline_health']['verdict']} "
        f"(data alignment / pipeline health) - report {report_md}"
    )
    if notices and not args.json:
        print()
        for notice in notices:
            print(f"- {notice}")
    if args.json:
        print(json.dumps(data, indent=2, default=str))
    elif notices or args.force_report or data.get("directory_snapshot_changed"):
        print()
        print(render(data))
    return 0


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    helper = _incremental_update()
    url = helper.get_database_url()
    if not url:
        raise SystemExit("DATABASE_URL is not configured and .env does not provide one")
    return url


if __name__ == "__main__":
    raise SystemExit(main())
