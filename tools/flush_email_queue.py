#!/usr/bin/env python3
"""Process the pending_emails table and send any queued emails via Resend.

Run after run_new_registration_feed_cycle.py (or any job that queues emails)
to flush the queue and actually deliver.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("flush_email_queue")


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


async def flush(batch_size: int = 200, max_batches: int = 10) -> int:
    from api.utils.email_queue import process_email_queue

    sent = 0
    for _ in range(max_batches):
        batch_sent = await process_email_queue(batch_size=batch_size)
        if batch_sent <= 0:
            break
        sent += batch_sent
    return sent


def main() -> int:
    _load_env_file()

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL not set.", file=sys.stderr)
        return 1

    if not os.environ.get("RESEND_API_KEY", ""):
        print("ERROR: RESEND_API_KEY not set.", file=sys.stderr)
        return 1

    sent = asyncio.run(flush())
    print(f"flush_email_queue: sent={sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
