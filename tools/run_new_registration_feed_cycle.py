#!/usr/bin/env python3
"""Sync the trusted event ledger and deliver the new registration feed cycle.

Designed for EC2 cron or systemd timers:
1. sync canonical new_registration events into trusted_event_ledger
2. deliver any newly inserted events to matching Business+ webhooks
3. queue the weekly digest off the same ledger-backed feed
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

from api.services.new_registration_feed import (
    deliver_new_registration_event,
    queue_weekly_new_registration_digests,
    sync_new_registration_event_payloads,
)

FEED_CYCLE_LOCK_ID = 802451202


def resolve_database_url(cli_value: str | None) -> str | None:
    if cli_value:
        return cli_value

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()

    return None


async def run_cycle(database_url: str, *, skip_digests: bool = False) -> dict[str, int]:
    conn = await asyncpg.connect(database_url)
    try:
        lock_acquired = await conn.fetchval("SELECT pg_try_advisory_lock($1)", FEED_CYCLE_LOCK_ID)
        if not lock_acquired:
            return {
                "inserted_events": 0,
                "webhook_deliveries": 0,
                "digests_queued": 0,
                "digests_skipped": 0,
                "skipped": 1,
            }

        run_id = await conn.fetchval(
            """
            INSERT INTO pipeline_runs (run_type, started_at, status)
            VALUES ('feed_cycle', NOW(), 'running')
            RETURNING id
            """
        )

        try:
            new_events = await sync_new_registration_event_payloads(conn, force=True)
            delivered = 0
            for event in new_events:
                delivered += await deliver_new_registration_event(conn, event)
            digest_result = {"queued": 0, "skipped": 0}
            if not skip_digests:
                digest_result = await queue_weekly_new_registration_digests(conn)

            await conn.execute(
                """
                UPDATE pipeline_runs
                SET completed_at = NOW(),
                    status = 'completed',
                    records_added = $1,
                    records_updated = $2,
                    error_message = NULL
                WHERE id = $3
                """,
                len(new_events),
                delivered,
                run_id,
            )
            return {
                "inserted_events": len(new_events),
                "webhook_deliveries": delivered,
                "digests_queued": digest_result["queued"],
                "digests_skipped": digest_result["skipped"],
                "skipped": 0,
            }
        except Exception as exc:
            await conn.execute(
                """
                UPDATE pipeline_runs
                SET completed_at = NOW(),
                    status = 'failed',
                    error_message = $1
                WHERE id = $2
                """,
                str(exc)[:4000],
                run_id,
            )
            raise
    finally:
        try:
            await conn.execute("SELECT pg_advisory_unlock($1)", FEED_CYCLE_LOCK_ID)
        except Exception:
            pass
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CareGist new-registration feed cycle")
    parser.add_argument("--database-url", default=None, help="PostgreSQL connection URL")
    parser.add_argument("--skip-digests", action="store_true", help="Only sync ledger events and webhooks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = resolve_database_url(args.database_url)
    if not database_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 1

    try:
        result = asyncio.run(run_cycle(database_url, skip_digests=args.skip_digests))
    except Exception as exc:
        print(f"Feed cycle failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(
        "Feed cycle complete:"
        f" inserted_events={result['inserted_events']}"
        f" webhook_deliveries={result['webhook_deliveries']}"
        f" digests_queued={result['digests_queued']}"
        f" digests_skipped={result['digests_skipped']}"
        f" skipped={result['skipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
