#!/usr/bin/env python3
"""Build Region Monthly records (stage 1; see docs/region-monthly-v1.md).

One record is one UK calendar month for one England region and one service type
(or all services). A month may be built only from 00:00 UK time on the 7th day
of the following month. Exactly one of --dry-run or --write is required:

  --dry-run  reads and counts inside a read-only transaction, prints what a
             write would do, and changes nothing;
  --write    stores each record as an immutable build. A month with no build
             gets version 1. A month whose content already matches its latest
             build is left alone. A month whose content differs is stored as a
             new version only with --correction-reason; otherwise it is reported
             and exits with status 3.

The database URL is read from --database-url or, normally, the DATABASE_URL
environment variable. It is never printed.

    python -m tools.build_region_monthly --dry-run --period-month 2026-10
    python -m tools.build_region_monthly --write --from-month 2026-04 --period-month 2026-10 \\
        --regions "London,East" --services all-services,home-care
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence

from api.queries import region_monthly as q
from api.services import region_monthly as svc

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_CHANGED_NOT_STORED = 3

ALL_SERVICES = "all-services"


@dataclass(frozen=True)
class Outcome:
    target: svc.BuildTarget
    action: str  # inserted, unchanged, changed_not_stored, would_insert, would_differ
    build_version: int | None
    content_sha256: str


def _service_label(slug: str | None) -> str:
    return slug or ALL_SERVICES


def parse_regions(value: str | None) -> list[str] | None:
    if not value or not value.strip():
        return None
    return [svc.normalise_region(part) for part in value.split(",")]


def parse_services(value: str | None) -> list[str | None] | None:
    if not value or not value.strip():
        return None
    out: list[str | None] = []
    for part in value.split(","):
        part = part.strip()
        out.append(None if part == ALL_SERVICES else svc.normalise_service(part))
    return out


async def run_builds(
    conn,
    targets: Sequence[svc.BuildTarget],
    *,
    write: bool,
    now: datetime,
    correction_reason: str | None = None,
) -> list[Outcome]:
    """Build every target. In dry-run mode the caller holds a read-only transaction."""
    table_present = bool(await conn.fetchval(q.BUILDS_TABLE_PRESENT))
    if write and not table_present:
        raise svc.RegionMonthlyError("source_unavailable")
    outcomes: list[Outcome] = []
    for target in targets:
        built = await svc.build_month(conn, target.period_month, target.region, target.service_slug, now)
        if write:
            stored = await svc.store_build(conn, built, correction_reason=correction_reason)
            outcomes.append(Outcome(target, stored.action, stored.build_version, built.content_sha256))
            continue
        latest = (
            await conn.fetchrow(q.LATEST_BUILD, target.period_month, target.region, target.service_slug)
            if table_present
            else None
        )
        if latest is None:
            outcomes.append(Outcome(target, "would_insert", 1, built.content_sha256))
        elif latest["content_sha256"] == built.content_sha256:
            outcomes.append(Outcome(target, "unchanged", latest["build_version"], built.content_sha256))
        else:
            outcomes.append(Outcome(target, "would_differ", latest["build_version"] + 1, built.content_sha256))
    return outcomes


def format_outcome(outcome: Outcome) -> str:
    t = outcome.target
    version = f"v{outcome.build_version}" if outcome.build_version else "-"
    return (
        f"{t.period_month.isoformat()} | {t.region} | {_service_label(t.service_slug)} | "
        f"{outcome.action} | {version} | {outcome.content_sha256[:12]}"
    )


def summarise(outcomes: Iterable[Outcome]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.action] = counts.get(outcome.action, 0) + 1
    return counts


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="count and report; write nothing")
    mode.add_argument("--write", action="store_true", help="store immutable builds")
    parser.add_argument("--period-month", help="YYYY-MM; default is the latest month that can be built")
    parser.add_argument("--from-month", help="YYYY-MM; builds the range from this month to --period-month")
    parser.add_argument("--regions", help="comma-separated England regions; default is all nine")
    parser.add_argument("--services", help=f"comma-separated service slugs or {ALL_SERVICES}; default is all")
    parser.add_argument("--correction-reason", help="allows a new version when a built month's content differs")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"), help="defaults to $DATABASE_URL")
    return parser.parse_args(argv)


def plan_from_args(args: argparse.Namespace, now: datetime) -> list[svc.BuildTarget]:
    last = svc.parse_month(args.period_month) if args.period_month else svc.latest_buildable_month(now)
    first = svc.parse_month(args.from_month) if args.from_month else last
    return svc.plan_backfill(first, last, now, regions=parse_regions(args.regions), services=parse_services(args.services))


async def _run(args: argparse.Namespace, now: datetime) -> int:
    import asyncpg

    targets = plan_from_args(args, now)
    print(f"{'write' if args.write else 'dry-run'}: {len(targets)} record(s) to build")
    conn = await asyncpg.connect(args.database_url)
    try:
        if args.write:
            outcomes = await run_builds(conn, targets, write=True, now=now, correction_reason=args.correction_reason)
        else:
            async with conn.transaction(readonly=True):
                outcomes = await run_builds(conn, targets, write=False, now=now)
    finally:
        await conn.close()
    for outcome in outcomes:
        print(format_outcome(outcome))
    counts = summarise(outcomes)
    print("summary: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if counts.get("changed_not_stored"):
        print(
            "Some months differ from their stored build and were not stored. "
            "Review them, then re-run with --correction-reason.",
            file=sys.stderr,
        )
        return EXIT_CHANGED_NOT_STORED
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.database_url:
        print("A database URL is required: set DATABASE_URL or pass --database-url.", file=sys.stderr)
        return EXIT_REFUSED
    now = datetime.now(timezone.utc)
    try:
        return asyncio.run(_run(args, now))
    except svc.RegionMonthlyError as error:
        print(f"Refused ({error.code}): {error.message}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
