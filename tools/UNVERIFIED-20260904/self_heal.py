#!/usr/bin/env python3
"""Detect - and optionally repair - the failure modes that silently stop revenue.

Each check here exists because it actually happened, not because it might.

  reconciliation_stranded
      A reconciliation batch whose shards ALL completed, that was never
      finalized. Only `finalize` writes counts_reconciled/reconciled_at, and
      only that row can act as the CQC source-freshness watermark that
      `commercialReadiness.checkoutReady` depends on. Batches c6e7d7fa
      (2026-08-11) and 56a11f0f (2026-08-12) each checked every location with
      zero failures and were then closed by `abort`. Paid checkout stayed off
      for a month because successful work was never booked as finished.
      This is the one check that can repair itself - but only inside the
      freshness SLA. `finalize` recomputes the active set and deactivates every
      location absent from that batch's snapshot, so finalizing a stale batch
      would apply an old snapshot's deletions to current data and wrongly
      deactivate everything registered since. Older batches are reported, never
      healed; they need a fresh reconciliation run instead.

  checkout_gate
      Live commercialReadiness.checkoutReady. If this is false nobody can pay,
      whatever else is working.

  fulfilment_email_backlog
      Unsent rows in pending_emails. A customer who paid and received nothing
      is worse than a customer who could not pay.

  stuck_delivery
      Radar delivery outbox entries stuck or dead-lettered.

  stale_signal_poll
      The hourly feed cycle has not completed inside its SLA.

Exit code is 0 when everything is healthy or was healed, 1 when a problem
remains. Run it on a schedule and alert on non-zero.

Usage:
    python3 tools/self_heal.py                # detect only, safe
    python3 tools/self_heal.py --heal         # also finalize a stranded batch
    python3 tools/self_heal.py --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[1]
HEALTH_URL = "https://www.caregist.co.uk/api/v1/health"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return values


ENV = load_env(REPO_ROOT / ".env")


def resolve(name: str) -> str | None:
    return os.environ.get(name) or ENV.get(name)


def fetch_health(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"[:200]}


async def check_all(conn, health: dict, heal: bool, sla_days: int) -> list[dict]:
    findings: list[dict] = []

    # --- reconciliation_stranded (repairable) ---
    stranded = await conn.fetch(
        """
        SELECT b.id, b.pipeline_run_id, b.shard_count, b.status, b.source_published_at,
               COUNT(s.*) FILTER (WHERE s.status = 'completed') AS completed_shards,
               COUNT(s.*) AS total_shards
        FROM reconciliation_batches b
        JOIN reconciliation_shards s ON s.batch_id = b.id
        JOIN pipeline_runs r ON r.id = b.pipeline_run_id
        WHERE r.counts_reconciled IS NOT TRUE
          AND b.source_published_at >= (CURRENT_DATE - ($1)::int)
        GROUP BY b.id, b.pipeline_run_id, b.shard_count, b.status, b.source_published_at
        HAVING COUNT(s.*) FILTER (WHERE s.status = 'completed') = b.shard_count
        ORDER BY b.source_published_at DESC
        """, sla_days,
    )
    # Anything older is real, but unsafe to finalize; surface it separately.
    stale = await conn.fetch(
        """
        SELECT b.id, b.source_published_at, b.shard_count
        FROM reconciliation_batches b
        JOIN reconciliation_shards s ON s.batch_id = b.id
        JOIN pipeline_runs r ON r.id = b.pipeline_run_id
        WHERE r.counts_reconciled IS NOT TRUE
          AND b.source_published_at < (CURRENT_DATE - ($1)::int)
        GROUP BY b.id, b.source_published_at, b.shard_count
        HAVING COUNT(s.*) FILTER (WHERE s.status = 'completed') = b.shard_count
        ORDER BY b.source_published_at DESC
        """, sla_days,
    )
    for row in stale:
        findings.append({
            "check": "reconciliation_stranded_stale", "severity": "high", "healed": False,
            "batch_id": str(row["id"]), "published": str(row["source_published_at"]),
            "detail": (f"All shards completed but the snapshot is older than the {sla_days}-day "
                       "freshness SLA. NOT auto-finalized: that would apply a stale snapshot's "
                       "deactivations to current data. Run a fresh reconciliation instead."),
        })
    for row in stranded:
        finding = {
            "check": "reconciliation_stranded",
            "severity": "critical",
            "batch_id": str(row["id"]),
            "pipeline_run_id": row["pipeline_run_id"],
            "published": str(row["source_published_at"]),
            "detail": (f"All {row['shard_count']} shards completed but the batch was never "
                       f"finalized, so no freshness watermark exists and paid checkout stays off."),
            "healed": False,
        }
        if heal:
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "incremental_update.py"), "--phase", "finalize",
                 "--batch-id", str(row["id"]), "--shard-count", str(row["shard_count"])],
                cwd=REPO_ROOT, text=True, capture_output=True,
            )
            finding["healed"] = result.returncode == 0
            finding["heal_output"] = (result.stdout or result.stderr or "").strip()[:300]
        findings.append(finding)

    # --- checkout_gate ---
    readiness = (health.get("commercialReadiness") or {}) if "_error" not in health else {}
    if health.get("_error"):
        findings.append({"check": "checkout_gate", "severity": "critical",
                         "detail": f"health endpoint unreachable: {health['_error']}", "healed": False})
    elif not readiness.get("checkoutReady", False):
        findings.append({
            "check": "checkout_gate", "severity": "critical", "healed": False,
            "detail": "commercialReadiness.checkoutReady is false - nobody can pay.",
            "signals": {k: v for k, v in readiness.items()},
        })

    # --- fulfilment_email_backlog ---
    unsent = await conn.fetchval("SELECT COUNT(*) FROM pending_emails WHERE sent_at IS NULL")
    if unsent:
        findings.append({"check": "fulfilment_email_backlog", "severity": "high", "healed": False,
                         "detail": f"{unsent} fulfilment emails have not been sent."})

    # --- stuck_delivery ---
    delivery = health.get("delivery") or {}
    if delivery.get("stuck") or delivery.get("deadLetter"):
        findings.append({"check": "stuck_delivery", "severity": "high", "healed": False,
                         "detail": f"delivery outbox stuck={delivery.get('stuck')} "
                                   f"deadLetter={delivery.get('deadLetter')}"})

    # --- stale_signal_poll ---
    poll = next((c for c in health.get("checks", []) if c.get("name") == "signal_poll_execution"), None)
    if poll and not poll.get("ok", True):
        findings.append({"check": "stale_signal_poll", "severity": "medium", "healed": False,
                         "detail": f"signal poll outside SLA: {poll.get('details')}"})

    return findings


async def run(args: argparse.Namespace) -> int:
    url = resolve("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set.")
    health = fetch_health(args.health_url)
    conn = await asyncpg.connect(re.sub(r"\?.*$", "", url), ssl="require")
    try:
        findings = await check_all(conn, health, args.heal, args.sla_days)
    finally:
        await conn.close()

    unresolved = [f for f in findings if not f.get("healed")]
    if args.json:
        print(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                          "healed": [f for f in findings if f.get("healed")],
                          "unresolved": unresolved}, indent=1))
    else:
        stamp = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"
        if not findings:
            print(f"SELF-HEAL {stamp}: all checks healthy.")
        for finding in findings:
            mark = "HEALED " if finding.get("healed") else "PROBLEM"
            print(f"{mark} [{finding['severity']}] {finding['check']}: {finding['detail']}")
            if finding.get("heal_output"):
                print(f"        {finding['heal_output']}")
            if finding.get("signals"):
                print(f"        {finding['signals']}")
        if unresolved and not args.heal:
            print("\nRe-run with --heal to repair anything repairable "
                  "(currently: a stranded reconciliation batch).")
    return 1 if unresolved else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heal", action="store_true",
                        help="Repair what can be repaired. Without it this only reports.")
    parser.add_argument("--health-url", default=HEALTH_URL)
    parser.add_argument("--sla-days", type=int, default=8,
                        help="Freshness SLA. A batch older than this is reported, never healed.")
    parser.add_argument("--json", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
