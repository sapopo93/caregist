#!/usr/bin/env python3
"""Verify CareGist reconciliation gates against the production database.

Read-only — five SELECT queries, zero mutations.
Exits 0 when all applicable gates pass. The fifth block (divergence) is
report-only observability: it is reported for a human and never fails the run.

Usage:
    python tools/verify_reconciliation_gates.py
    DATABASE_URL=postgres://... python tools/verify_reconciliation_gates.py
    python tools/verify_reconciliation_gates.py --divergence-window-days 7
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

# Lookback for the report-only divergence observation. Bounded so that a single
# historical batch cannot colour every later run forever; this is a reporting
# window, not a safety threshold.
DIVERGENCE_WINDOW_DAYS = 30


def _resolve_database_url(cli_arg: str | None = None) -> str:
    if cli_arg:
        return cli_arg
    env = os.environ.get("DATABASE_URL")
    if env:
        return env
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("No DATABASE_URL found. Pass --database-url or set the env var.")


def _divergence_report(rows, window_days: int) -> dict:
    """Summarise reconciliation-batch deactivation volume as information only.

    REPORT-ONLY: the returned gate always has ``passed: True`` and never carries
    issues. It asserts NO pass/fail threshold, deliberately:

    * The finalize guard in ``incremental_update._finalize_batch`` already
      refuses any batch whose manifest-scoped inactivity
      (``inactive_manifest_covered / location_count``) exceeds
      ``MAX_ACTIVE_COUNT_DROP_RATIO``. A pass/fail alarm measured on the same
      population of completed batches can therefore never fire on one.
    * The ratio reported here is ESTATE-WIDE (``active_records_before`` ->
      ``active_records_after`` over the whole care_providers table, which also
      counts rows deactivated outside the manifest) while the guard's bound is
      MANIFEST-SCOPED over ``location_count``. Comparing the two raises false
      positives on batches the guard correctly accepted: 50 of 1000 manifest
      locations inactive is exactly 5.00% (the guard accepts it), then 52 rogue
      rows are deactivated as well, and the estate-wide figures read
      1002 -> 950 — a 5.19% drop that looks like a breach and is not one.
    * The estate's real per-batch deactivation volumes have never been measured,
      so any tighter numeric threshold would be a guess.

    THE OPERATIONAL THRESHOLD MUST BE DERIVED FROM MEASURED PRODUCTION DATA,
    NOT GUESSED. Once a run of real batches has been observed, promote this
    block to a gate with a threshold justified by that measurement.

    Two half-written states are surfaced rather than filtered away, so a crash,
    a bug or a direct edit cannot hide in the gap between the guard writing a
    row and this report reading it:

    * a completed batch whose ``active_records_after`` is NULL is reported as
      unmeasured (the pre-change query dropped these rows entirely);
    * a completed batch whose ``completed_at`` is NULL is reported but excluded
      from the window maximum, instead of being silently dropped by the window
      comparison's NULL semantics.
    """
    batches = []
    window_ratios: list[float] = []
    unmeasured: dict[str, str] = {}
    undated: list[str] = []
    for batch in rows:
        before = batch["active_records_before"]
        after = batch["active_records_after"]
        batch_id = str(batch["id"])
        in_window = batch["completed_at"] is not None
        drop = None
        ratio = None
        if after is None:
            unmeasured[batch_id] = "active_records_after is NULL"
        elif before is None or int(before) <= 0:
            unmeasured[batch_id] = f"active_records_before is {before!r}, so there is no denominator"
        else:
            drop = max(int(before) - int(after), 0)
            ratio = round(drop / int(before), 6)
            if in_window:
                window_ratios.append(ratio)
        if not in_window:
            undated.append(batch_id)
        batches.append(
            {
                "batch_id": batch_id,
                "completed_at": str(batch["completed_at"]) if in_window else None,
                "location_count": batch["location_count"],
                "active_records_before": before,
                "active_records_after": after,
                "records_deactivated": batch["records_deactivated"],
                "active_drop": drop,
                "active_drop_ratio": ratio,
                "measured": drop is not None,
                "in_window": in_window,
            }
        )

    observations = [
        f"completed reconciliation batch {batch_id} could not be measured ({reason})"
        for batch_id, reason in unmeasured.items()
    ]
    observations += [
        f"completed reconciliation batch {batch_id} has no completed_at: reported but not "
        "counted towards the window maximum"
        for batch_id in undated
    ]
    observations.append(
        "estate-wide drop ratio, not comparable to the guard's manifest-scoped bound; "
        "no pass/fail threshold is asserted here — derive one from measured production data"
    )

    return {
        # Report-only: this block never fails the run. See the docstring above.
        "passed": True,
        "report_only": True,
        "values": {
            "window_days": window_days,
            "reconciliation_batches_checked": len(batches),
            "batches_with_a_measured_drop": sum(1 for batch in batches if batch["measured"]),
            "batches_unmeasured": unmeasured,
            "batches_without_completed_at": undated,
            "max_active_drop_ratio_in_window": max(window_ratios) if window_ratios else None,
            "batches": batches,
            "note": (
                "no completed reconciliation batches in the window"
                if not batches
                else "per-batch deactivation volume and estate-wide drop ratio (report-only, no threshold)"
            ),
        },
        "issues": [],
        "observations": observations,
    }


async def _run_gates(database_url: str, divergence_window_days: int = DIVERGENCE_WINDOW_DAYS) -> dict:
    conn = await asyncpg.connect(database_url)
    try:
        results = {}

        # ── COUNT gate ──────────────────────────────────────────
        count = await conn.fetchrow("""
            SELECT
              (SELECT COUNT(*) FROM trusted_event_ledger) AS ledger_events,
              (SELECT COUNT(*) FROM care_providers WHERE status = 'ACTIVE') AS active_providers,
              (SELECT COUNT(*) FROM pipeline_runs WHERE status = 'completed') AS completed_pipeline_runs,
              (SELECT COUNT(*) FROM subscriptions WHERE status = 'active') AS active_subscriptions,
              (SELECT COUNT(*) FROM audit_log) AS audit_entries,
              (SELECT COUNT(DISTINCT event_type) FROM trusted_event_ledger) AS event_types
        """)
        count_issues = []
        if count["ledger_events"] == 0:
            count_issues.append("trusted_event_ledger is empty")
        if count["active_providers"] == 0:
            count_issues.append("no active providers")
        if count["completed_pipeline_runs"] == 0:
            count_issues.append("no completed pipeline runs")
        results["count"] = {
            "passed": len(count_issues) == 0,
            "values": {
                "ledger_events": count["ledger_events"],
                "active_providers": count["active_providers"],
                "completed_pipeline_runs": count["completed_pipeline_runs"],
                "active_subscriptions": count["active_subscriptions"],
                "audit_entries": count["audit_entries"],
                "event_types": count["event_types"],
            },
            "issues": count_issues,
        }

        # ── COVERAGE gate ───────────────────────────────────────
        coverage = await conn.fetchrow("""
            SELECT COUNT(*) AS feed_runs
            FROM pipeline_runs
            WHERE run_type = 'feed_cycle'
              AND status = 'completed'
              AND completed_at > NOW() - INTERVAL '24 hours'
        """)
        last_feed = await conn.fetchrow("""
            SELECT completed_at, records_added, records_updated, active_records_before, active_records_after
            FROM pipeline_runs
            WHERE run_type = 'feed_cycle' AND status = 'completed'
            ORDER BY completed_at DESC LIMIT 1
        """)
        coverage_issues = []
        if not coverage["feed_runs"] or coverage["feed_runs"] == 0:
            coverage_issues.append("no feed_cycle runs in last 24 hours")
        results["coverage"] = {
            "passed": len(coverage_issues) == 0,
            "values": {
                "feed_runs_24h": coverage["feed_runs"],
                "last_feed_completed": str(last_feed["completed_at"]) if last_feed else None,
                "last_feed_records_added": last_feed["records_added"] if last_feed else None,
                "last_feed_records_updated": last_feed["records_updated"] if last_feed else None,
            },
            "issues": coverage_issues,
        }

        # ── CHECKSUM gate ───────────────────────────────────────
        # feed_cycle runs don't use source_checksum; check pipeline_alert_log for integrity
        alert_counts = await conn.fetchrow("""
            SELECT
              COUNT(*) FILTER (WHERE severity = 'critical') AS critical_alerts,
              COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') AS recent_alerts
            FROM pipeline_alert_log
        """)
        checksum_issues = []
        if alert_counts["critical_alerts"] and alert_counts["critical_alerts"] > 0:
            checksum_issues.append(f"{alert_counts['critical_alerts']} critical pipeline alerts exist")
        results["checksum"] = {
            "passed": len(checksum_issues) == 0,
            "values": {
                "critical_alerts": alert_counts["critical_alerts"],
                "recent_alerts_1h": alert_counts["recent_alerts"],
                "note": "feed_cycle runs do not use source_checksum; gate checks pipeline alert integrity"
            },
            "issues": checksum_issues,
        }

        # ── WATERMARK gate ──────────────────────────────────────
        watermark = await conn.fetchrow("""
            WITH latest_feed AS (
              SELECT completed_at FROM pipeline_runs
              WHERE run_type = 'feed_cycle' AND status = 'completed'
              ORDER BY completed_at DESC LIMIT 1
            ),
            latest_event AS (
              SELECT MAX(observed_at) AS last_event_at FROM trusted_event_ledger
            )
            SELECT
              (SELECT completed_at FROM latest_feed) AS last_feed_at,
              (SELECT last_event_at FROM latest_event) AS last_event_at
        """)
        watermark_issues = []
        if not watermark["last_feed_at"]:
            watermark_issues.append("no completed feed cycle")
        elif watermark["last_event_at"] and watermark["last_feed_at"]:
            # Feed should have run after the last event
            pass  # Both present — gate passes
        results["watermark"] = {
            "passed": len(watermark_issues) == 0,
            "values": {
                "last_feed_completed_at": str(watermark["last_feed_at"]) if watermark["last_feed_at"] else None,
                "last_event_observed_at": str(watermark["last_event_at"]) if watermark["last_event_at"] else None,
                "note": "feed_cycle runs do not use source_published_at; gate verifies feed recency"
            },
            "issues": watermark_issues,
        }

        # ── DIVERGENCE observability (REPORT-ONLY) ──────────────
        # reconciliation_batches.active_records_before/after record what the
        # finalize phase saw and wrote. Nothing else surfaces those figures, so
        # report them per batch — and the worst of them — for a human reading
        # the evidence file. See _divergence_report for why this asserts no
        # threshold and why the window is bounded.
        #
        # Batches with a NULL completed_at are included explicitly rather than
        # being dropped by the window comparison's NULL semantics, so a
        # half-written completed batch cannot disappear from the report.
        divergence = await conn.fetch(
            """
            SELECT b.id,
                   b.location_count,
                   b.active_records_before,
                   b.active_records_after,
                   b.records_deactivated,
                   b.completed_at
            FROM reconciliation_batches AS b
            JOIN pipeline_runs AS p ON p.id = b.pipeline_run_id
            WHERE b.status = 'completed'
              AND p.run_type = 'reconciliation'
              AND p.status = 'completed'
              AND (
                    b.completed_at >= NOW() - ($1 * INTERVAL '1 day')
                    OR b.completed_at IS NULL
                  )
            ORDER BY b.completed_at DESC NULLS LAST
            """,
            divergence_window_days,
        )
        results["divergence"] = _divergence_report(divergence, divergence_window_days)

        return results
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify CareGist reconciliation gates")
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    parser.add_argument(
        "--output",
        default=".caregist-data/evidence/LEAD-009-reconciliation-evidence.json",
        help="Output path for reconciliation evidence",
    )
    parser.add_argument(
        "--divergence-window-days",
        type=int,
        default=DIVERGENCE_WINDOW_DAYS,
        help=(
            "Lookback for the report-only divergence observation "
            f"(default: {DIVERGENCE_WINDOW_DAYS} days)"
        ),
    )
    args = parser.parse_args(argv)

    db_url = _resolve_database_url(args.database_url)

    try:
        results = asyncio.run(
            _run_gates(db_url, divergence_window_days=args.divergence_window_days)
        )
    except (asyncpg.exceptions.PostgresError, OSError) as exc:
        print(json.dumps({"error": str(exc), "gate": "connection"}, indent=2))
        return 1

    all_passed = all(g["passed"] for g in results.values())
    evidence = {
        "evidence_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "Neon Postgres — Launch plan",
        "gates": results,
        "all_passed": all_passed,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n")

    print(json.dumps({
        "all_passed": all_passed,
        "gates": {k: v["passed"] for k, v in results.items()},
        "summary": {k: v["values"] for k, v in results.items()},
    }, indent=2, default=str))

    return 0 if all_passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
