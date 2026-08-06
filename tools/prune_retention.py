#!/usr/bin/env python3
"""Nightly data-retention pruning (F-28).

Bounds the unbounded-growth tables flagged in the production audit:

  * analytics_events  — 90 days
  * audit_log         — 2 years (compliance-driven; override with --audit-days)
  * admin_audit_log   — 2 years
  * pending_emails    — sent rows older than 30 days (failed rows are kept for
    the dead-letter workflow; see tools/check_email_dead_letters.py)
  * enquiries         — personal fields anonymised after 12 months
  * rejected reviews  — reviewer identity anonymised after 12 months
  * closed claims     — claimant identity and evidence fingerprint anonymised
    12 months after decision
  * leads             — deleted after 12 months (tokens cascade)
  * expired export tokens — deleted 90 days after expiry

Run from cron/systemd-timer nightly. Each table is pruned independently so one
missing table (older deployments) does not abort the rest. Use --dry-run to
report counts without deleting.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg

# (table, timestamp column, default retention days, optional extra WHERE)
RETENTION_RULES = [
    ("analytics_events", "created_at", 90, None),
    ("audit_log", "created_at", 730, None),
    ("admin_audit_log", "created_at", 730, None),
    ("pending_emails", "created_at", 30, "status = 'sent'"),
    ("leads", "created_at", 365, None),
    ("export_access_tokens", "expires_at", 90, None),
]

# (result key, table, age predicate, extra predicate, anonymising SET clause)
ANONYMISATION_RULES = [
    (
        "enquiries",
        "enquiries",
        "created_at < NOW() - INTERVAL '365 days'",
        "enquirer_email <> '[retention-anonymised]'",
        "enquirer_name = '[retention-anonymised]', enquirer_email = '[retention-anonymised]', "
        "enquirer_phone = NULL, relationship = NULL, care_type = NULL, message = '[retention-anonymised]'",
    ),
    (
        "reviews",
        "reviews",
        "created_at < NOW() - INTERVAL '365 days'",
        "status = 'rejected' AND reviewer_email <> '[retention-anonymised]'",
        "reviewer_name = '[retention-anonymised]', reviewer_email = '[retention-anonymised]', admin_notes = NULL",
    ),
    (
        "provider_claims",
        "provider_claims",
        "COALESCE(reviewed_at, suspended_at, created_at) < NOW() - INTERVAL '365 days'",
        "(status IN ('rejected', 'expired') OR suspended_at IS NOT NULL) "
        "AND claimant_email <> '[retention-anonymised]'",
        "claimant_name = '[retention-anonymised]', claimant_email = '[retention-anonymised]', "
        "claimant_phone = NULL, claimant_role = NULL, organisation_name = NULL, "
        "proof_of_association = '[retention-anonymised]', admin_notes = NULL, claimant_user_id = NULL",
    ),
]


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


async def _table_exists(conn, table: str) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass($1)", f"public.{table}"))


async def prune(conn, *, audit_days: int, dry_run: bool) -> dict[str, int]:
    results: dict[str, int] = {}
    for table, ts_col, default_days, extra_where in RETENTION_RULES:
        if not await _table_exists(conn, table):
            continue
        days = audit_days if table in ("audit_log", "admin_audit_log") else default_days
        where = f"{ts_col} < NOW() - make_interval(days => {days})"
        if extra_where:
            where += f" AND {extra_where}"

        if dry_run:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table} WHERE {where}")
            results[table] = int(count or 0)
        else:
            status = await conn.execute(f"DELETE FROM {table} WHERE {where}")
            # status looks like "DELETE <n>"
            results[table] = int(status.split()[-1]) if status.startswith("DELETE") else 0

    for result_key, table, age_where, extra_where, set_clause in ANONYMISATION_RULES:
        if not await _table_exists(conn, table):
            continue
        where = f"{age_where} AND {extra_where}"
        if dry_run:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table} WHERE {where}")
            results[result_key] = int(count or 0)
        else:
            status = await conn.execute(f"UPDATE {table} SET {set_clause} WHERE {where}")
            results[result_key] = int(status.split()[-1]) if status.startswith("UPDATE") else 0
    return results


async def _run(database_url: str, *, audit_days: int, dry_run: bool) -> dict[str, int]:
    conn = await asyncpg.connect(database_url)
    try:
        return await prune(conn, audit_days=audit_days, dry_run=dry_run)
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune retention-bound tables")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--audit-days", type=int, default=730, help="Retention for audit tables (default 730).")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without deleting.")
    args = parser.parse_args()

    database_url = _resolve_database_url(args.database_url)
    if not database_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 1

    results = asyncio.run(_run(database_url, audit_days=args.audit_days, dry_run=args.dry_run))
    verb = "would prune" if args.dry_run else "pruned"
    for table, count in results.items():
        print(f"{verb} {count} rows from {table}")
    if not results:
        print("No retention-bound tables found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
