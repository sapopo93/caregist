#!/usr/bin/env python3
"""Apply numbered SQL migrations to PostgreSQL."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


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
    return parser.parse_args()


def resolve_database_url(cli_value: str | None) -> str | None:
    if cli_value:
        return cli_value

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    env_path = Path(".env")
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()

    return None


async def apply_migrations(database_url: str) -> int:
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


def main() -> int:
    args = parse_args()
    database_url = resolve_database_url(args.database_url)
    if not database_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 1

    try:
        asyncio.run(apply_migrations(database_url))
    except Exception as exc:
        print(f"Migration failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
