#!/usr/bin/env python3
"""Process the pending_emails table and send any queued emails via Resend.

Run after run_new_registration_feed_cycle.py (or any job that queues emails)
to flush the queue and actually deliver.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


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


async def main() -> int:
    from api.utils.email_queue import process_email_queue

    sent = await process_email_queue(batch_size=50)
    print(f"flush_email_queue: sent={sent}")
    return 0


if __name__ == "__main__":
    _load_env_file()
    raise SystemExit(asyncio.run(main()))
