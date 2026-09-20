#!/usr/bin/env python3
"""Apply numbered SQL migrations to PostgreSQL."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

if TYPE_CHECKING:
    import asyncpg


async def ensure_migrations_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          filename TEXT PRIMARY KEY,
          applied_at TIMESTAMP DEFAULT NOW()
        )
        """
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply CareGist SQL migrations")
    parser.add_argument("--database-url", default=None, help="PostgreSQL connection URL")
    parser.add_argument(
        "--target",
        choices=("local", "staging", "production"),
        default="local",
        help="Migration target. staging and production require target-specific env vars.",
    )
    parser.add_argument(
        "--confirm-production-backup",
        action="store_true",
        help="Confirm a production backup/PITR point exists before production migrations.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Report migrations present in this checkout but not applied to the target, "
            "then exit non-zero if any are pending. Read-only: applies nothing and "
            "never creates the ledger table, so it needs no backup confirmation."
        ),
    )
    return parser.parse_args()


def _read_env_file_value(name: str) -> str | None:
    env_path = Path(".env")
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip("\"'")

    return None


def resolve_database_url(
    cli_value: str | None,
    *,
    target: str = "local",
    confirm_production_backup: bool = False,
    read_only: bool = False,
) -> str | None:
    if target == "staging":
        staging_url = os.getenv("STAGING_DATABASE_URL") or _read_env_file_value("STAGING_DATABASE_URL")
        if not staging_url:
            raise RuntimeError("STAGING_DATABASE_URL is required for --target staging.")
        return staging_url

    if target == "production":
        # A read-only check (--check) mutates nothing, so it needs no restore-point
        # assertion. Every write path still requires the explicit confirmation.
        if not confirm_production_backup and not read_only:
            raise RuntimeError("--confirm-production-backup is required before production migrations.")
        prod_url = os.getenv("PROD_DATABASE_URL") or _read_env_file_value("PROD_DATABASE_URL")
        if not prod_url:
            raise RuntimeError("PROD_DATABASE_URL is required for --target production.")
        return prod_url

    if cli_value:
        return cli_value

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    return _read_env_file_value("DATABASE_URL")


async def apply_migrations(database_url: str) -> int:
    import asyncpg

    migration_files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    if not migration_files:
        print("No migration files found.")
        return 0

    conn = await asyncpg.connect(database_url)
    applied_count = 0
    try:
        await ensure_migrations_table(conn)
        applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM schema_migrations ORDER BY filename")
        }

        for migration_path in migration_files:
            if migration_path.name in applied:
                continue

            sql = migration_path.read_text(encoding="utf-8").strip()
            if not sql:
                continue

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)",
                    migration_path.name,
                )
            applied_count += 1
            print(f"Applied migration {migration_path.name}")

    finally:
        await conn.close()

    if applied_count == 0:
        print("No pending migrations.")
    else:
        print(f"Applied {applied_count} migration(s).")
    return applied_count


async def pending_migrations(database_url: str) -> list[str]:
    """Return migrations in this checkout that the target database has not applied.

    Read-only by construction: it resolves the ledger with ``to_regclass`` (which
    returns NULL instead of raising when the table is absent) and issues only
    ``SELECT`` statements. It never creates ``schema_migrations`` and never applies
    anything, so a missing ledger is reported as "everything is pending" rather
    than silently materialising a table.
    """
    import asyncpg

    migration_files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    if not migration_files:
        return []

    conn = await asyncpg.connect(database_url)
    try:
        ledger = await conn.fetchval("SELECT to_regclass('schema_migrations')::text")
        if ledger is None:
            return [path.name for path in migration_files]

        applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM schema_migrations")
        }
    finally:
        await conn.close()

    return [path.name for path in migration_files if path.name not in applied]


def main() -> int:
    args = parse_args()
    try:
        database_url = resolve_database_url(
            args.database_url,
            target=args.target,
            confirm_production_backup=args.confirm_production_backup,
            read_only=args.check,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not database_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 1

    if args.check:
        try:
            pending = asyncio.run(pending_migrations(database_url))
        except Exception as exc:
            print(f"Schema check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        if not pending:
            print("Schema is current: no pending migrations.")
            return 0
        print(
            f"SCHEMA DRIFT: {len(pending)} migration(s) exist in this checkout but are not "
            f"applied to the {args.target} database:",
            file=sys.stderr,
        )
        for name in pending:
            print(f"  - {name}", file=sys.stderr)
        return 1

    try:
        asyncio.run(apply_migrations(database_url))
    except Exception as exc:
        print(f"Migration failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
