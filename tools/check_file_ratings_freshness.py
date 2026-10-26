#!/usr/bin/env python3
"""Read-only check that the CQC ratings-file overlay (migration 068) is not stale.

Ratings the CQC API omits are served from CQC's published latest-ratings file
(tools/import_cqc_latest_ratings.py). That file is published periodically and is
imported by hand, so this check fails once the edition it holds -- the date CQC
published the imported file, recorded by the importer (migration 070) -- is older
than --max-age-days, which is the cue to import the current file. A file-sourced
rating with no recorded edition also fails: its age cannot be known. It never
writes.

    python -m tools.check_file_ratings_freshness [--max-age-days 45]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date


def verdict(edition: date | None, filled: int, undated: int, today: date, max_age_days: int) -> tuple[bool, str]:
    if not filled:
        return False, "no file-sourced ratings are recorded; import CQC's latest ratings file"
    if undated:
        return False, (
            f"{undated} file-sourced ratings have no recorded file edition; re-import the "
            "current file with --edition-date"
        )
    age = (today - edition).days
    if age > max_age_days:
        return False, f"the imported ratings file is the {edition} edition ({age} days old, limit {max_age_days}); import the current file"
    return True, f"the imported ratings file is the {edition} edition ({age} days old)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-age-days", type=int, default=45)
    args = ap.parse_args(argv)

    import psycopg2

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT min(file_rating_edition_date), count(file_overall_rating),
                      count(*) FILTER (WHERE file_overall_rating IS NOT NULL AND file_rating_edition_date IS NULL)
                 FROM care_providers"""
        )
        edition, filled, undated = cur.fetchone()
        cur.execute(
            """SELECT count(*) FROM care_providers
                WHERE status = 'ACTIVE' AND file_overall_rating IS NULL
                  AND (rating_state IS DISTINCT FROM 'rated')"""
        )
        unrated = cur.fetchone()[0]
    ok, message = verdict(edition, filled, undated, date.today(), args.max_age_days)
    print(f"{'OK' if ok else 'STALE'}: {message}; {filled} locations served from the file; "
          f"{unrated} active locations have neither an API rating nor a file rating")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
