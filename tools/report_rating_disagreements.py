#!/usr/bin/env python3
"""Where every served rating came from, and every disagreement between sources.

Read-only (rule 4 of the CareGist rating rule). Uses the same SQL the API serves
with (api.queries.providers), so the counts are exactly what customers see:
ratings served from CQC's ratings file, from a newer check of CQC's website, or
from CQC's API, and every location where the sources disagree. ``--csv`` writes
one line per disagreement for follow-up.

    python -m tools.report_rating_disagreements [--csv PATH]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

from api.queries.providers import RATING_CONFLICT, RATING_SOURCE, SERVED_RATING

SUMMARY_SQL = f"""
SELECT {RATING_SOURCE} AS source, {RATING_CONFLICT} AS conflict, count(*) AS n
  FROM care_providers WHERE status = 'ACTIVE'
 GROUP BY 1, 2 ORDER BY 1 NULLS LAST, 2 NULLS FIRST
"""

DISAGREEMENTS_SQL = f"""
SELECT id, name, {RATING_CONFLICT} AS conflict, {SERVED_RATING} AS served, {RATING_SOURCE} AS source,
       file_overall_rating, file_rating_edition_date, site_check_rating, site_check_at,
       CASE WHEN rating_state = 'rated' THEN overall_rating END AS api_rating, last_published_rating_date
  FROM care_providers
 WHERE status = 'ACTIVE' AND {RATING_CONFLICT} IS NOT NULL
 ORDER BY 3, id
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path)
    args = ap.parse_args(argv)

    import psycopg2

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute(SUMMARY_SQL)
        rows = cur.fetchall()
        print("active locations by rating source and disagreement:")
        for source, conflict, n in rows:
            print(f"  {source or 'no rating':22} {conflict or '-':16} {n}")
        flagged = sum(n for _, conflict, n in rows if conflict)
        print(f"disagreements flagged: {flagged}")
        if args.csv:
            cur.execute(DISAGREEMENTS_SQL)
            with args.csv.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow([d[0] for d in cur.description])
                w.writerows(cur.fetchall())
            print(f"wrote disagreements to {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
