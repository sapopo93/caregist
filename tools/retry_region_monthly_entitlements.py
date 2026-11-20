#!/usr/bin/env python3
"""Finish Region Monthly orders that were paid and have a missing entitlement.

A failure after payment leaves the order ``paid`` with its last error and fewer
entitlements than purchased months. Stripe redelivers the payment event, which
finishes the order; this command does the same by hand, or when Stripe has stopped
retrying. Entitlements are unique per order and month, so running it again creates
nothing twice, and a refunded order is skipped.

Dry run by default: it lists what would be granted and changes nothing. ``--apply``
grants. A production run needs the owner's go-ahead.

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

from api.services.region_monthly_orders import grant_outstanding  # noqa: E402


async def _run(database_url: str, *, apply: bool, limit: int) -> list[dict]:
    settings = None if apply else {"default_transaction_read_only": "on"}
    conn = await asyncpg.connect(database_url, server_settings=settings)
    try:
        return await grant_outstanding(conn, apply=apply, limit=limit)
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--apply", action="store_true", help="Grant. Without it, report only.")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 2
    report = asyncio.run(_run(url, apply=args.apply, limit=args.limit))
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "orders": report}, indent=2))
    return 1 if any(item.get("result") == "failed" for item in report) else 0


if __name__ == "__main__":
    sys.exit(main())
