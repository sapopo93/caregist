#!/usr/bin/env python3
"""Delete Territory Brief exclusion identifiers whose correction period has ended.

Dry run by default: it counts what is due and deletes nothing. ``--apply`` deletes
the identifiers and stamps the scope version as purged; the scope row, its hash and
the exclusion counts are kept as evidence. A production run needs the owner's go-ahead.
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

from api.services.territory_brief_scope_store import purge_expired_exclusions  # noqa: E402


async def _run(database_url: str, apply: bool) -> dict:
    settings = None if apply else {"default_transaction_read_only": "on"}
    conn = await asyncpg.connect(database_url, server_settings=settings)
    try:
        return await purge_expired_exclusions(conn, apply=apply)
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--apply", action="store_true", help="Delete. Without it, report only.")
    args = parser.parse_args()
    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 2
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", **asyncio.run(_run(url, args.apply))}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
