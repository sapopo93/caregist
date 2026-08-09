#!/usr/bin/env python3
"""Process a bounded batch of durable Radar webhook deliveries."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from api.services.delivery_outbox import process_delivery_outbox
from incremental_update import get_database_url, normalize_database_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process the CareGist Radar delivery outbox")
    parser.add_argument("--database-url")
    parser.add_argument("--batch-size", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = normalize_database_url(args.database_url) if args.database_url else get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL is required.", file=sys.stderr)
        return 1
    if not 1 <= args.batch_size <= 500:
        print("ERROR: --batch-size must be between 1 and 500.", file=sys.stderr)
        return 1
    result = asyncio.run(process_delivery_outbox(database_url, batch_size=args.batch_size))
    print(json_result(result))
    return 0 if result["failed"] == 0 else 2


def json_result(result: dict[str, int]) -> str:
    return " ".join(f"{key}={value}" for key, value in sorted(result.items()))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
