#!/usr/bin/env python3
"""Report monitor execution health and CQC source freshness as separate verdicts.

A monitor process that exits cleanly proves only that the monitor works. It is
not evidence that CQC source data is fresh. Conflating the two lets a healthy
monitor mask stale data, so this reporter always emits both verdicts and never
infers one from the other.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

MONITOR_OK = "OK"
MONITOR_FAILED = "FAILED"

FRESH = "FRESH"
STALE = "STALE"
UNKNOWN = "UNKNOWN"


def load_snapshot(path: Path) -> dict | None:
    """Return the parsed snapshot, or None when the monitor produced none."""
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def monitor_verdict(snapshot: dict | None) -> str:
    """Did the monitor itself execute correctly?

    The monitor is healthy when it ran to completion AND produced a parseable
    snapshot. A degraded pipeline makes the step fail while the monitor itself
    worked, so a snapshot is the authoritative signal.
    """
    if snapshot is not None:
        return MONITOR_OK
    return MONITOR_FAILED


def freshness_verdict(snapshot: dict | None) -> tuple[str, str]:
    """Is the CQC SOURCE DATA fresh? Never inferred from monitor health."""
    if snapshot is None:
        return UNKNOWN, "monitor produced no snapshot; source freshness was not measured"

    source_fresh = snapshot.get("source_fresh")
    if source_fresh is True:
        return FRESH, "reconciled CQC source watermark is inside its SLA"
    if source_fresh is False:
        return STALE, "reconciled CQC source watermark is outside its SLA"
    return UNKNOWN, "snapshot did not report source_fresh"


def build_report(outcome: str, snapshot: dict | None) -> dict:
    monitor = monitor_verdict(snapshot)
    freshness, reason = freshness_verdict(snapshot)
    return {
        "monitor_execution": {
            "verdict": monitor,
            "step_outcome": outcome,
            "snapshot_produced": snapshot is not None,
        },
        "source_data_freshness": {
            "verdict": freshness,
            "reason": reason,
            "source_detail": (snapshot or {}).get("source"),
        },
        "pipeline_status": (snapshot or {}).get("status", UNKNOWN.lower()),
        "readiness_ok": (snapshot or {}).get("readiness_ok"),
        "note": (
            "Monitor execution health and CQC source-data freshness are "
            "independent verdicts. A healthy monitor is not evidence of fresh data."
        ),
    }


def write_summary(report: dict) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    monitor = report["monitor_execution"]
    freshness = report["source_data_freshness"]
    lines = [
        "## Freshness watchdog verdicts",
        "",
        "| Verdict | Value | Detail |",
        "|---|---|---|",
        f"| Monitor execution | **{monitor['verdict']}** | step outcome `{monitor['step_outcome']}`, "
        f"snapshot produced: {monitor['snapshot_produced']} |",
        f"| CQC source-data freshness | **{freshness['verdict']}** | {freshness['reason']} |",
        "",
        "These are separate verdicts. A monitor that runs correctly is not evidence",
        "that CQC source data is fresh.",
        "",
    ]
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()

    outcome = os.environ.get("MONITOR_OUTCOME", "unknown")
    snapshot = load_snapshot(args.snapshot)
    report = build_report(outcome, snapshot)

    print(json.dumps(report, indent=2))
    write_summary(report)

    # Fail closed: this reporter only reports. It must never turn a failed
    # monitor run into a green result, so it exits non-zero when the monitor
    # itself did not execute correctly.
    return 0 if report["monitor_execution"]["verdict"] == MONITOR_OK else 1


if __name__ == "__main__":
    raise SystemExit(main())
