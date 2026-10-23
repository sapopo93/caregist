#!/usr/bin/env python3
"""Read-only check that the CQC ratings-file overlay (migration 068) is not stale.

Ratings the CQC API omits are served from CQC's published latest-ratings file
(tools/import_cqc_latest_ratings.py). That file is published periodically and is
imported by hand, so this check fails once the newest publication date it holds is
older than --max-age-days, which is the cue to import the current file. It never
writes.

    python -m tools.check_file_ratings_freshness [--max-age-days 45]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date


def verdict(newest: date | None, today: date, max_age_days: int) -> tuple[bool, str]:
    if newest is None:
        return False, "no file-sourced ratings are recorded; import CQC's latest ratings file"
    age = (today - newest).days
    if age > max_age_days:
        return False, f"newest file-sourced rating was published {newest} ({age} days ago, limit {max_age_days}); import the current file"
    return True, f"newest file-sourced rating was published {newest} ({age} days ago)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-age-days", type=int, default=45)
    args = ap.parse_args(argv)

    import psycopg2

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SELECT max(file_overall_rating_date), count(file_overall_rating) FROM care_providers")
        newest, filled = cur.fetchone()
        cur.execute(
            """SELECT count(*) FROM care_providers
                WHERE status = 'ACTIVE' AND file_overall_rating IS NULL
                  AND (rating_state IS DISTINCT FROM 'rated')"""
        )
        unrated = cur.fetchone()[0]
    ok, message = verdict(newest, date.today(), args.max_age_days)
    print(f"{'OK' if ok else 'STALE'}: {message}; {filled} locations served from the file; "
          f"{unrated} active locations have neither an API rating nor a file rating")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
