#!/usr/bin/env python3
"""Run read-only schema and row-count checks on an isolated Neon restore."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify an isolated CareGist database restore")
    parser.add_argument("--database-url", default=os.environ.get("RESTORE_DATABASE_URL"))
    parser.add_argument("--required-migration", required=True)
    parser.add_argument("--minimum-provider-rows", type=int, required=True)
    parser.add_argument("--minimum-active-provider-rows", type=int, required=True)
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if not args.database_url:
        raise ValueError("RESTORE_DATABASE_URL or --database-url is required")
    if not args.required_migration.endswith(".sql") or "/" in args.required_migration:
        raise ValueError("--required-migration must be a migration filename")
    if args.minimum_provider_rows < 1 or args.minimum_active_provider_rows < 1:
        raise ValueError("provider row baselines must be positive")
    if args.minimum_active_provider_rows > args.minimum_provider_rows:
        raise ValueError("active-provider baseline cannot exceed total-provider baseline")


async def verify(args: argparse.Namespace) -> dict:
    import asyncpg

    conn = await asyncpg.connect(args.database_url, command_timeout=30)
    try:
        async with conn.transaction(readonly=True):
            required_migration_present = bool(
                await conn.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE filename = $1)",
                    args.required_migration,
                )
            )
            provider_rows = int(await conn.fetchval("SELECT COUNT(*) FROM care_providers"))
            active_provider_rows = int(
                await conn.fetchval("SELECT COUNT(*) FROM care_providers WHERE status = 'ACTIVE'")
            )
            duplicate_location_ids = int(
                await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM (
                      SELECT location_id FROM care_providers
                      GROUP BY location_id HAVING COUNT(*) > 1
                    ) duplicates
                    """
                )
            )
            latest_migration = await conn.fetchval(
                "SELECT filename FROM schema_migrations ORDER BY applied_at DESC, filename DESC LIMIT 1"
            )
    finally:
        await conn.close()

    checks = {
        "required_migration_present": required_migration_present,
        "provider_rows_at_least_baseline": provider_rows >= args.minimum_provider_rows,
        "active_provider_rows_at_least_baseline": active_provider_rows >= args.minimum_active_provider_rows,
        "location_ids_unique": duplicate_location_ids == 0,
    }
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "required_migration": args.required_migration,
        "latest_migration": latest_migration,
        "counts": {
            "provider_rows": provider_rows,
            "active_provider_rows": active_provider_rows,
            "duplicate_location_ids": duplicate_location_ids,
        },
        "checks": checks,
        "ok": all(checks.values()),
    }


def main() -> int:
    args = parse_args()
    try:
        _validate_args(args)
        result = asyncio.run(verify(args))
    except Exception as exc:
        print(f"Restore invariant check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
