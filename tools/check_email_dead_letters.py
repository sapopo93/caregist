#!/usr/bin/env python3
"""Dead-letter alert for the email queue (F-44).

Counts permanently-failed emails older than a cutoff (default 24h) — these have
exhausted their retries and will never be sent without intervention. Exits 1
(and optionally emails an operator) when any are found, so it can gate a cron
job / surface in monitoring.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

from api.utils.email_queue import count_dead_letter_emails, get_dead_letter_emails


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key and key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip()


def _resolve_database_url(cli_value: str | None) -> str | None:
    if cli_value:
        return cli_value
    _load_env_file()
    return os.environ.get("DATABASE_URL")


async def _run(database_url: str, *, hours: int) -> int:
    conn = await asyncpg.connect(database_url)
    try:
        total = await count_dead_letter_emails(conn, older_than_hours=hours)
        if total:
            sample = await get_dead_letter_emails(conn, older_than_hours=hours, limit=10)
            print(f"ALERT: {total} dead-letter email(s) older than {hours}h", file=sys.stderr)
            for row in sample:
                print(f"  id={row['id']} to={row['to_email']} attempts={row['attempts']} created={row['created_at']}", file=sys.stderr)
        else:
            print(f"OK: no dead-letter emails older than {hours}h")
        return total
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Alert on dead-letter emails")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    database_url = _resolve_database_url(args.database_url)
    if not database_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 2

    total = asyncio.run(_run(database_url, hours=args.hours))
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
