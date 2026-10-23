#!/usr/bin/env python3
"""Check file-sourced ratings against CQC's own location pages (migration 069).

A rating copied from CQC's periodic ratings file can be out of date when it is
served. This reads each file-sourced location's public cqc.org.uk page (about one
request a second) and compares the page's overall rating with the file's.
Dry-run by default: prints the comparison and writes nothing. `--apply` records
what the page showed in site_check_rating / site_check_at, which makes the serving
queries withhold a rating the page no longer shows. Nothing else is touched.

    python3 -m tools.verify_file_ratings_against_site [--rating Inadequate] [--apply]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.request
from collections import Counter

PAGE = "https://www.cqc.org.uk/location/{id}"
RATING_RE = re.compile(r'overall-rating__value--value">([^<]+)<')
PUBLISHED = {"Outstanding", "Good", "Requires improvement", "Inadequate"}
USER_AGENT = "CareGist-ratings-check/1.0 (+https://caregist.co.uk)"


def parse_site_rating(html: str) -> str:
    """The overall rating shown on a location page, or 'none' when it shows none."""
    m = RATING_RE.search(html)
    value = m.group(1).strip() if m else ""
    return next((p for p in PUBLISHED if p.lower() == value.lower()), "none")


def fetch_site_rating(location_id: str) -> str | None:
    req = urllib.request.Request(PAGE.format(id=location_id), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return parse_site_rating(resp.read().decode("utf-8", "replace"))
    except Exception as exc:  # a failed fetch is unknown, never recorded as a rating
        print(f"  could not read {location_id}: {exc}", file=sys.stderr)
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rating", default="Inadequate", choices=sorted(PUBLISHED))
    ap.add_argument("--delay", type=float, default=1.1, help="seconds between requests")
    ap.add_argument("--apply", action="store_true", help="write site_check_* columns")
    args = ap.parse_args(argv)

    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, file_overall_rating FROM care_providers
                WHERE file_overall_rating = %s AND status = 'ACTIVE'
                  AND lower(btrim(coalesce(overall_rating, ''))) NOT IN
                      ('outstanding','good','requires improvement','inadequate')
                ORDER BY id""",
            (args.rating,),
        )
        targets = cur.fetchall()
        outcome: Counter = Counter()
        for lid, file_rating in targets:
            site = fetch_site_rating(lid)
            if site is None:
                outcome["unreadable"] += 1
            else:
                outcome["agrees" if site == file_rating else f"differs:{site}"] += 1
                if args.apply:
                    cur.execute(
                        "UPDATE care_providers SET site_check_rating=%s, site_check_at=now() WHERE id=%s",
                        (site, lid),
                    )
            time.sleep(args.delay)
        print(f"checked {len(targets)} file-sourced {args.rating} locations:", dict(outcome))
        print("applied" if args.apply else "dry run: nothing written (use --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
