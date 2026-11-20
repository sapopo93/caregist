#!/usr/bin/env python3
"""Finish Operator History orders that were paid and not delivered.

A delivery that failed after payment leaves the order ``paid`` with its last error.
Stripe redelivers the payment event, which finishes the order; this command does the
same by hand, or when Stripe has stopped retrying. Delivery happens once: a delivered
order is never touched, and the delivered files are append-only.

Dry run by default: it lists what would be delivered and changes nothing. ``--apply``
delivers. ``--include-failed`` also tries orders that reached the attempt limit and
are marked ``failed``. A production run needs the owner's go-ahead.

The database URL comes from ``--database-url`` or the DATABASE_URL environment
variable. This command opens no environment file itself.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.operator_history_orders import deliver_outstanding  # noqa: E402


async def _run(database_url: str, *, apply: bool, include_failed: bool, limit: int) -> list[dict]:
    settings = None if apply else {"default_transaction_read_only": "on"}
    conn = await asyncpg.connect(database_url, server_settings=settings)
    try:
        return await deliver_outstanding(conn, apply=apply, include_failed=include_failed, limit=limit)
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--apply", action="store_true", help="Deliver. Without it, report only.")
    parser.add_argument("--include-failed", action="store_true", help="Also retry orders marked failed.")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 2
    report = asyncio.run(_run(url, apply=args.apply, include_failed=args.include_failed, limit=args.limit))
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "orders": report}, indent=2))
    return 1 if any(item.get("result") == "failed" for item in report) else 0


if __name__ == "__main__":
    sys.exit(main())
