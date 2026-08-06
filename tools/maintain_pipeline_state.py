#!/usr/bin/env python3
"""Preview or apply stale-run closure and legacy alert compaction."""

from __future__ import annotations

import argparse
import os
import re

import psycopg2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--stale-hours", type=int, default=7)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--recovery-point-id", help="Verified Neon restore point or branch identifier")
    parser.add_argument("--recovery-evidence-sha256", help="SHA-256 of the approved restore-point evidence")
    parser.add_argument("--confirm-stale-count", type=int)
    parser.add_argument("--confirm-alert-count", type=int)
    parser.add_argument("--confirm-alert-max-id", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")
    if args.stale_hours < 1:
        raise SystemExit("--stale-hours must be positive")

    with psycopg2.connect(args.database_url) as conn, conn.cursor() as cur:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cur.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE status = 'running' AND started_at < NOW() - (%s * INTERVAL '1 hour')",
            (args.stale_hours,),
        )
        stale_count = int(cur.fetchone()[0])
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM pipeline_alert_log")
        alert_max_id = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM pipeline_alert_log WHERE id <= %s", (alert_max_id,))
        alert_count = int(cur.fetchone()[0])
        print(
            f"preview stale_running={stale_count} legacy_alert_rows={alert_count} "
            f"legacy_alert_max_id={alert_max_id}"
        )

        if not args.apply:
            conn.rollback()
            print(
                "Re-run with --apply, --recovery-point-id, --confirm-stale-count "
                "--confirm-alert-count and --confirm-alert-max-id using the previewed values."
            )
            return 0
        if not args.recovery_point_id:
            raise SystemExit("--recovery-point-id is required for --apply")
        if not args.recovery_evidence_sha256 or not re.fullmatch(r"[0-9a-f]{64}", args.recovery_evidence_sha256):
            raise SystemExit("--recovery-evidence-sha256 must be a lowercase SHA-256 value")
        if (
            args.confirm_stale_count != stale_count
            or args.confirm_alert_count != alert_count
            or args.confirm_alert_max_id != alert_max_id
        ):
            raise SystemExit("database counts changed since preview; refusing maintenance")

        cur.execute(
            """
            SELECT b.id, s.shard_index
            FROM reconciliation_batches b
            JOIN reconciliation_shards s ON s.batch_id = b.id
            JOIN pipeline_runs p ON p.id = b.pipeline_run_id
            WHERE p.status = 'running'
              AND p.started_at < NOW() - (%s * INTERVAL '1 hour')
              AND s.status = 'running'
            ORDER BY b.id, s.shard_index
            """,
            (args.stale_hours,),
        )
        for batch_id, shard_index in cur.fetchall():
            lock_key = f"cqc-reconciliation:{batch_id}:{shard_index}"
            cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
            if not cur.fetchone()[0]:
                raise SystemExit(f"shard {batch_id}/{shard_index} still owns its advisory lock; refusing maintenance")

        cur.execute(
            """
            UPDATE reconciliation_shards
            SET status = 'failed', updated_at = NOW(), error_message = %s
            WHERE status = 'running' AND batch_id IN (
              SELECT id FROM reconciliation_batches
              WHERE pipeline_run_id IN (
                SELECT id FROM pipeline_runs
                WHERE status = 'running' AND started_at < NOW() - (%s * INTERVAL '1 hour')
              )
            )
            """,
            (f"Closed after verified Neon recovery point {args.recovery_point_id}", args.stale_hours),
        )
        cur.execute(
            """
            UPDATE reconciliation_batches
            SET status = 'failed', completed_at = NOW(), error_message = %s
            WHERE status IN ('prepared', 'running') AND pipeline_run_id IN (
              SELECT id FROM pipeline_runs
              WHERE status = 'running' AND started_at < NOW() - (%s * INTERVAL '1 hour')
            )
            """,
            (f"Closed after verified Neon recovery point {args.recovery_point_id}", args.stale_hours),
        )
        cur.execute(
            """
            UPDATE pipeline_runs
            SET status = 'failed', completed_at = NOW(),
                error_message = %s
            WHERE status = 'running' AND started_at < NOW() - (%s * INTERVAL '1 hour')
            """,
            (f"Closed by audited maintenance after Neon recovery point {args.recovery_point_id}", args.stale_hours),
        )
        cur.execute(
            """
            INSERT INTO pipeline_alert_state (
              alert_key, severity, details, first_seen_at, last_seen_at, occurrence_count
            )
            SELECT alert_key,
                   CASE MAX(CASE severity WHEN 'critical' THEN 4 WHEN 'error' THEN 3 WHEN 'warning' THEN 2 ELSE 1 END)
                     WHEN 4 THEN 'critical' WHEN 3 THEN 'error' WHEN 2 THEN 'warning' ELSE 'info' END,
                   jsonb_build_object(
                     'compactedFrom', 'pipeline_alert_log',
                     'recoveryPointId', %s,
                     'recoveryEvidenceSha256', %s
                   ),
                   MIN(created_at), MAX(created_at), COUNT(*)
            FROM pipeline_alert_log WHERE id <= %s GROUP BY alert_key
            ON CONFLICT (alert_key) DO UPDATE
            SET last_seen_at = GREATEST(pipeline_alert_state.last_seen_at, EXCLUDED.last_seen_at),
                first_seen_at = LEAST(pipeline_alert_state.first_seen_at, EXCLUDED.first_seen_at),
                occurrence_count = pipeline_alert_state.occurrence_count + EXCLUDED.occurrence_count,
                details = EXCLUDED.details
            """,
            (args.recovery_point_id, args.recovery_evidence_sha256, alert_max_id),
        )
        cur.execute("DELETE FROM pipeline_alert_log WHERE id <= %s", (alert_max_id,))
        conn.commit()
        print(f"applied recovery_point={args.recovery_point_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
