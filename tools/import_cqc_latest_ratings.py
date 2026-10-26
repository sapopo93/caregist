#!/usr/bin/env python3
"""Record overall ratings from CQC's published "Latest ratings" ODS file.

Dry-run by default: prints how the file compares with care_providers and writes
nothing. `--apply` writes only the file_* columns (migrations 068 and 070); it
never touches overall_rating, which keeps mirroring the CQC API.

`--edition-date` is the date CQC published this edition of the file, as shown on
CQC's download page. It is required with `--apply` because the filename does not
reliably carry it, and the staleness check measures it.

    python3 -m tools.import_cqc_latest_ratings PATH.ods --edition-date YYYY-MM-DD [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import zipfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
import xml.etree.ElementTree as ET

T = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
X = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
PUBLISHED = {"Outstanding", "Good", "Requires improvement", "Inadequate"}


def iter_sheet_rows(path: Path, sheet: str):
    """Stream rows of one ODS sheet without loading the workbook."""
    with zipfile.ZipFile(path) as z, z.open("content.xml") as f:
        current = None
        for ev, el in ET.iterparse(f, events=("start", "end")):
            if ev == "start" and el.tag == T + "table":
                current = el.get(T + "name")
            elif ev == "end" and el.tag == T + "table-row" and current == sheet:
                row = []
                for c in el.iter(T + "table-cell"):
                    rep = min(int(c.get(T + "number-columns-repeated", "1")), 50)
                    txt = "".join("".join(p.itertext()) for p in c.findall(X + "p"))
                    row.extend([txt] * rep)
                while row and row[-1] == "":
                    row.pop()
                if row:
                    yield row
                el.clear()


def overall_ratings(path: Path):
    """Return ({location_id: (rating, date)}, ambiguous_ids).

    Only Service/Population Group == Domain == "Overall" rows with a published
    rating are used. A location with two different overall rows is ambiguous
    (the file's README says to check CQC's site) and is skipped, never guessed.
    """
    rows = iter_sheet_rows(path, "Locations")
    header = next(rows)
    col = {name: i for i, name in enumerate(header)}
    found: dict[str, set[tuple[str, str]]] = {}
    for r in rows:
        r = r + [""] * (len(header) - len(r))
        if r[col["Domain"]] != "Overall" or r[col["Service / Population Group"]] != "Overall":
            continue
        rating = r[col["Latest Rating"]].strip()
        if rating not in PUBLISHED:
            continue
        found.setdefault(r[col["Location ID"]], set()).add((rating, r[col["Publication Date"]]))
    ambiguous = {k for k, v in found.items() if len(v) > 1}
    return {k: next(iter(v)) for k, v in found.items() if k not in ambiguous}, ambiguous


def parse_date(text: str):
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError:
        return None


APPLY_ATTEMPTS = 5


def apply_with_retry(conn, rows, edition, sha, source_name, attempts=APPLY_ATTEMPTS, sleep=time.sleep):
    """Apply the file in one transaction, retrying if Postgres aborts it as a deadlock.

    Other jobs (the CQC reconciliation) update care_providers too, so two bulk
    writers can deadlock; Postgres then aborts one transaction whole. Rows are
    locked in id order to make that rare, and an aborted attempt is rolled back
    and retried with backoff. Nothing partial is ever committed.
    """
    import psycopg2
    from psycopg2.extras import execute_values

    for attempt in range(1, attempts + 1):
        try:
            with conn, conn.cursor() as cur:
                cur.execute("CREATE TEMP TABLE incoming_ratings (id text PRIMARY KEY, rating text, published date) ON COMMIT DROP")
                execute_values(cur, "INSERT INTO incoming_ratings (id, rating, published) VALUES %s", rows, page_size=5000)
                cur.execute(
                    "SELECT 1 FROM care_providers WHERE id IN (SELECT id FROM incoming_ratings) "
                    "OR (file_rating_source_sha256 IS NOT NULL AND file_rating_source_sha256 <> %s) "
                    "ORDER BY id FOR UPDATE",
                    (sha,),
                )
                cur.execute(
                    """UPDATE care_providers cp SET file_overall_rating=i.rating, file_overall_rating_date=i.published,
                              file_rating_edition_date=%s,
                              site_check_rating = CASE WHEN cp.file_rating_source_sha256 IS NOT DISTINCT FROM %s
                                                       THEN cp.site_check_rating END,
                              site_check_at = CASE WHEN cp.file_rating_source_sha256 IS NOT DISTINCT FROM %s
                                                   THEN cp.site_check_at END,
                              file_rating_source=%s, file_rating_source_sha256=%s
                         FROM incoming_ratings i WHERE cp.id = i.id""",
                    (edition, sha, sha, source_name, sha),
                )
                n = cur.rowcount
                # Rows stamped by an earlier file but absent from this one lose the stale claim.
                cur.execute(
                    """UPDATE care_providers SET file_overall_rating=NULL, file_overall_rating_date=NULL,
                              file_rating_edition_date=NULL, site_check_rating=NULL, site_check_at=NULL,
                              file_rating_source=NULL, file_rating_source_sha256=NULL
                        WHERE file_rating_source_sha256 IS NOT NULL AND file_rating_source_sha256 <> %s""",
                    (sha,),
                )
                return n, cur.rowcount
        except psycopg2.errors.DeadlockDetected:
            if attempt == attempts:
                raise
            wait = 15 * attempt
            print(f"deadlock with another writer (attempt {attempt}/{attempts}); rolled back, retrying in {wait}s")
            sleep(wait)
    raise AssertionError("unreachable")


def edition_is_newer(edition: date | None, held: date | None) -> bool:
    """True when ``edition`` is later than the newest edition production holds."""
    return edition is not None and (held is None or edition > held)


def edition_problem(edition: date | None, newest_rating: date | None, today: date) -> str | None:
    """Why an edition date cannot be right for this file, or None when it can."""
    if edition is None:
        return "--edition-date YYYY-MM-DD is required with --apply (the date CQC published this file)"
    if edition > today:
        return f"edition date {edition} is in the future"
    if newest_rating is not None and edition < newest_rating:
        return f"edition date {edition} predates a rating the file says was published {newest_rating}"
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ods", type=Path)
    ap.add_argument("--apply", action="store_true", help="write file_* columns")
    ap.add_argument("--edition-date", type=date.fromisoformat,
                    help="date CQC published this edition of the file (YYYY-MM-DD); required with --apply")
    ap.add_argument("--only-if-newer", action="store_true",
                    help="do nothing when production already holds this edition or a later one")
    args = ap.parse_args(argv)

    sha = hashlib.sha256(args.ods.read_bytes()).hexdigest()
    ratings, ambiguous = overall_ratings(args.ods)
    print(f"file {args.ods.name} sha256 {sha}")
    print(f"locations with a published overall rating: {len(ratings)}; ambiguous skipped: {len(ambiguous)}")
    print("by rating:", dict(Counter(v[0] for v in ratings.values())))
    newest_rating = max((d for d in (parse_date(v[1]) for v in ratings.values()) if d), default=None)
    print(f"newest rating publication date in the file: {newest_rating}; edition date: {args.edition_date}")
    if args.apply:
        problem = edition_problem(args.edition_date, newest_rating, date.today())
        if problem:
            print(f"refusing to apply: {problem}", file=sys.stderr)
            return 2

    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn, conn.cursor() as cur:
        if args.only_if_newer:
            cur.execute("SELECT max(file_rating_edition_date) FROM care_providers")
            held = cur.fetchone()[0]
            if not edition_is_newer(args.edition_date, held):
                print(f"production already holds the {held} edition; nothing to import")
                return 0
        # The file is the main rating source, so the importer no longer reconciles
        # each rating against the API; disagreements between sources are reported
        # by tools/report_rating_disagreements.py from the served SQL itself.
        cur.execute("SELECT id, status FROM care_providers")
        db = dict(cur.fetchall())
        outcome = Counter(db[lid] if lid in db else "not_in_db" for lid in ratings)
        for k, v in sorted(outcome.items()):
            print(f"  {k}: {v}")
        if not args.apply:
            print("dry run: nothing written (use --apply)")
            return 0
    rows = [(lid, rating, parse_date(pub)) for lid, (rating, pub) in ratings.items() if lid in db]
    n, cleared = apply_with_retry(conn, rows, args.edition_date, sha, args.ods.name)
    print(f"applied: {n} rows updated, {cleared} stale cleared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
