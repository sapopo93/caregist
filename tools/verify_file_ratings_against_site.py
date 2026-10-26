#!/usr/bin/env python3
"""Weekly check of CQC's own location pages between ratings files (rule 2).

CQC's monthly ratings file is the main rating source; between files, CQC
publishes new reports on its website. This reads the public cqc.org.uk page
(about one request a second) for the locations where the file may be out of
date and records what the page shows in site_check_rating / site_check_at
(migration 069). The serving queries then let a page check made on or after the
file's edition win where it differs; the next file import supersedes it.

Targets (``--targets``):
  newer-reports (default)  locations where CQC's API reports a rating published
                           after the file's edition, or where the file and the
                           API disagree -- the cases a new report explains.
  file-rating              every active file-sourced location with ``--rating``
                           (the original 069 audit of file-only ratings).

Dry-run by default: prints the comparison and writes nothing. ``--apply`` writes
only site_check_rating / site_check_at.

    python3 -m tools.verify_file_ratings_against_site [--targets newer-reports] [--limit N] [--apply]
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


# A newer CQC report is likely where the API's published-rating date is after the
# file's edition, or where the file and a published API rating disagree. Already
# checked since the file edition (and since that API date) is skipped.
NEWER_REPORT_TARGETS = """
SELECT id, file_overall_rating FROM care_providers
 WHERE status = 'ACTIVE'
   AND (
        (rating_state = 'rated' AND last_published_rating_date IS NOT NULL
         AND last_published_rating_date > coalesce(file_rating_edition_date, file_overall_rating_date, DATE '1900-01-01'))
     OR (rating_state = 'rated' AND file_overall_rating IS NOT NULL
         AND overall_rating IS DISTINCT FROM file_overall_rating)
   )
   AND (site_check_at IS NULL
        OR site_check_at::date < greatest(coalesce(file_rating_edition_date, DATE '1900-01-01'),
                                          coalesce(last_published_rating_date, DATE '1900-01-01')))
 ORDER BY last_published_rating_date DESC NULLS LAST, id
 LIMIT %s
"""


def implausible_none_share(seen: list[tuple[str, str]], max_share: float = 0.5, min_pages: int = 20) -> str | None:
    """Why the page reads look like a markup change rather than real results.

    A page whose rating cannot be found parses as 'none', and 'none' withholds a
    rating. If CQC changes its page markup every page reads as 'none', so a run
    where most readable pages show no rating is refused rather than written.
    """
    if len(seen) < min_pages:
        return None
    none = sum(1 for _, site in seen if site == "none")
    if none / len(seen) > max_share:
        return f"{none} of {len(seen)} pages showed no rating; check the page markup (RATING_RE)"
    return None


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
    ap.add_argument("--targets", choices=("newer-reports", "file-rating"), default="newer-reports")
    ap.add_argument("--rating", default="Inadequate", choices=sorted(PUBLISHED),
                    help="with --targets file-rating: the file rating to check")
    ap.add_argument("--limit", type=int, default=2000, help="most pages to read in one run")
    ap.add_argument("--delay", type=float, default=1.1, help="seconds between requests")
    ap.add_argument("--apply", action="store_true", help="write site_check_* columns")
    args = ap.parse_args(argv)

    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn, conn.cursor() as cur:
        if args.targets == "file-rating":
            cur.execute(
                """SELECT id, file_overall_rating FROM care_providers
                    WHERE file_overall_rating = %s AND status = 'ACTIVE'
                      AND lower(btrim(coalesce(overall_rating, ''))) NOT IN
                          ('outstanding','good','requires improvement','inadequate')
                    ORDER BY id LIMIT %s""",
                (args.rating, args.limit),
            )
        else:
            cur.execute(NEWER_REPORT_TARGETS, (args.limit,))
        targets = cur.fetchall()
        outcome: Counter = Counter()
        seen: list[tuple[str, str]] = []
        for lid, file_rating in targets:
            site = fetch_site_rating(lid)
            if site is None:
                outcome["unreadable"] += 1
            else:
                outcome["agrees" if site == file_rating else f"differs:{site}"] += 1
                seen.append((lid, site))
            time.sleep(args.delay)
        label = f"file-sourced {args.rating}" if args.targets == "file-rating" else "newer-report"
        print(f"checked {len(targets)} {label} locations:", dict(outcome))
        problem = implausible_none_share(seen)
        if problem:
            print(f"refusing to write: {problem}", file=sys.stderr)
            return 2
        if args.apply:
            for lid, site in seen:
                cur.execute(
                    "UPDATE care_providers SET site_check_rating=%s, site_check_at=now() WHERE id=%s",
                    (site, lid),
                )
        print(f"applied {len(seen)} page checks" if args.apply else "dry run: nothing written (use --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
