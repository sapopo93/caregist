#!/usr/bin/env python3
"""Verify CQC reconciliation gates: COUNT, COVERAGE, CHECKSUM, WATERMARK.

Read-only script — no mutations. Exits 0 when all gates pass, non-zero otherwise.
Outputs reconciliation-evidence.json to the specified path.

Usage:
    python tools/verify_reconciliation_gates.py --database-url postgres://...
    python tools/verify_reconciliation_gates.py --output evidence.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _resolve_database_url(cli_arg: str | None = None) -> str:
    """Resolve the database URL from CLI arg, DATABASE_URL env, or .env file."""
    if cli_arg:
        return cli_arg
    env = os.environ.get("DATABASE_URL")
    if env:
        return env
    # Try .env in repo root
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        "No database URL provided. Use --database-url, set DATABASE_URL, "
        "or ensure .env contains DATABASE_URL."
    )


async def _run_gates(database_url: str) -> dict:
    """Execute all four reconciliation gates and return results."""
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        results = {}

        # ── COUNT gate ──────────────────────────────────────────
        count = await conn.fetchrow(
            """
            SELECT
              (SELECT COUNT(*) FROM trusted_event_ledger) AS ledger_events,
              (SELECT COUNT(*) FROM care_providers
               WHERE status = 'ACTIVE') AS active_providers,
              (SELECT COUNT(*) FROM reconciliation_batches
               WHERE status = 'completed') AS completed_batches,
              (SELECT COUNT(*) FROM subscriptions
               WHERE status = 'active') AS active_subscriptions,
              (SELECT COUNT(*) FROM billing_operations
               WHERE status = 'succeeded') AS succeeded_billing_ops
            """
        )
        count_issues = []
        if count["ledger_events"] == 0:
            count_issues.append("trusted_event_ledger is empty")
        if count["active_providers"] == 0:
            count_issues.append("no active providers found")
        results["count"] = {
            "passed": len(count_issues) == 0,
            "values": dict(count),
            "issues": count_issues,
        }

        # ── COVERAGE gate ───────────────────────────────────────
        coverage = await conn.fetchrow(
            """
            WITH completed AS (
              SELECT source_published_at, source_record_count, source_checksum_sha256
              FROM reconciliation_batches WHERE status = 'completed'
              ORDER BY source_published_at DESC LIMIT 1
            )
            SELECT
              (SELECT source_published_at FROM completed) AS last_batch_watermark,
              (SELECT source_record_count FROM completed) AS last_batch_records,
              (SELECT source_checksum_sha256 FROM completed) AS last_batch_checksum,
              (SELECT COUNT(*) FROM pipeline_runs
               WHERE status = 'completed') AS completed_pipeline_runs
            """
        )
        coverage_issues = []
        if not coverage["last_batch_watermark"]:
            coverage_issues.append("no completed reconciliation batch found")
        if not coverage["completed_pipeline_runs"]:
            coverage_issues.append("no completed pipeline runs")
        results["coverage"] = {
            "passed": len(coverage_issues) == 0,
            "values": dict(coverage),
            "issues": coverage_issues,
        }

        # ── CHECKSUM gate ───────────────────────────────────────
        checksums = await conn.fetch(
            """
            SELECT source_checksum_sha256, manifest_checksum_sha256,
                   source_published_at
            FROM pipeline_runs
            WHERE status = 'completed'
              AND source_checksum_sha256 IS NOT NULL
              AND manifest_checksum_sha256 IS NOT NULL
            ORDER BY source_published_at DESC
            LIMIT 5
            """
        )
        mismatch = [
            {"source_published_at": str(r["source_published_at"]),
             "source_checksum": r["source_checksum_sha256"],
             "manifest_checksum": r["manifest_checksum_sha256"]}
            for r in checksums
            if r["source_checksum_sha256"] != r["manifest_checksum_sha256"]
        ]
        results["checksum"] = {
            "passed": len(mismatch) == 0 and len(checksums) > 0,
            "checked_runs": len(checksums),
            "mismatches": mismatch,
            "issues": [f"checksum mismatch in {m['source_published_at']}" for m in mismatch],
        }

        # ── WATERMARK gate ──────────────────────────────────────
        watermark = await conn.fetchrow(
            """
            WITH latest_batch AS (
              SELECT source_published_at FROM reconciliation_batches
              WHERE status = 'completed'
              ORDER BY source_published_at DESC LIMIT 1
            ),
            latest_pipeline AS (
              SELECT source_published_at FROM pipeline_runs
              WHERE status = 'completed'
              ORDER BY source_published_at DESC LIMIT 1
            )
            SELECT
              (SELECT source_published_at FROM latest_batch) AS batch_watermark,
              (SELECT source_published_at FROM latest_pipeline) AS pipeline_watermark
            """
        )
        watermark_issues = []
        if not watermark["batch_watermark"]:
            watermark_issues.append("no batch watermark found")
        elif not watermark["pipeline_watermark"]:
            watermark_issues.append("no pipeline watermark found")
        elif watermark["batch_watermark"] < watermark["pipeline_watermark"]:
            watermark_issues.append(
                f"batch watermark ({watermark['batch_watermark']}) is behind "
                f"pipeline watermark ({watermark['pipeline_watermark']})"
            )
        results["watermark"] = {
            "passed": len(watermark_issues) == 0,
            "values": {
                "batch_watermark": str(watermark["batch_watermark"]) if watermark["batch_watermark"] else None,
                "pipeline_watermark": str(watermark["pipeline_watermark"]) if watermark["pipeline_watermark"] else None,
            },
            "issues": watermark_issues,
        }

        return results
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify CQC reconciliation gates")
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    parser.add_argument(
        "--output",
        default=".caregist-data/evidence/LEAD-009.json",
        help="Output path for reconciliation evidence (default: .caregist-data/evidence/LEAD-009.json)",
    )
    args = parser.parse_args(argv)

    db_url = _resolve_database_url(args.database_url)

    import asyncio
    import asyncpg  # noqa: F811

    try:
        results = asyncio.run(_run_gates(db_url))
    except (asyncpg.exceptions.PostgresError, OSError) as exc:
        print(json.dumps({"error": str(exc), "gate": "connection"}, indent=2))
        return 1

    all_passed = all(g["passed"] for g in results.values())
    evidence = {
        "evidence_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gates": results,
        "all_passed": all_passed,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n")

    print(json.dumps({"all_passed": all_passed, "gates": {
        k: v["passed"] for k, v in results.items()
    }}, indent=2))

    return 0 if all_passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
