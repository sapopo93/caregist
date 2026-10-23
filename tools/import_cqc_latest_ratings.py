#!/usr/bin/env python3
"""Record overall ratings from CQC's published "Latest ratings" ODS file.

Dry-run by default: prints how the file compares with care_providers and writes
nothing. `--apply` writes only the file_* columns (migration 068); it never
touches overall_rating, which keeps mirroring the CQC API.

    python3 -m tools.import_cqc_latest_ratings PATH.ods [--apply]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import zipfile
from collections import Counter
from datetime import datetime
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ods", type=Path)
    ap.add_argument("--apply", action="store_true", help="write file_* columns")
    ap.add_argument("--report", type=Path, help="write a per-location CSV of every API-vs-file disagreement")
    args = ap.parse_args(argv)

    sha = hashlib.sha256(args.ods.read_bytes()).hexdigest()
    ratings, ambiguous = overall_ratings(args.ods)
    print(f"file {args.ods.name} sha256 {sha}")
    print(f"locations with a published overall rating: {len(ratings)}; ambiguous skipped: {len(ambiguous)}")
    print("by rating:", dict(Counter(v[0] for v in ratings.values())))

    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn, conn.cursor() as cur:
        cur.execute("SELECT id, status, coalesce(overall_rating,'') FROM care_providers")
        db = {i: (s, r) for i, s, r in cur.fetchall()}
        outcome = Counter()
        report = []
        for lid, (rating, pub) in ratings.items():
            if lid not in db:
                outcome["not_in_db"] += 1
                continue
            status, api = db[lid]
            kind = "agrees" if api == rating else "api_blank" if not api else "api_differs"
            outcome[(status, kind)] += 1
            if kind != "agrees":
                report.append([lid, status, api, rating, pub, kind])
        if args.report:
            with args.report.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["location_id", "status", "api_rating", "file_rating", "file_publication_date", "difference"])
                w.writerows(sorted(report))
            print(f"wrote {len(report)} disagreements to {args.report}")
        for k, v in sorted(outcome.items(), key=lambda kv: str(kv[0])):
            print(" ", k, v)
        if not args.apply:
            print("dry run: nothing written (use --apply)")
            return 0
        n = 0
        for lid, (rating, pub) in ratings.items():
            if lid in db:
                cur.execute(
                    """UPDATE care_providers SET file_overall_rating=%s, file_overall_rating_date=%s,
                              site_check_rating = CASE WHEN file_rating_source_sha256 IS NOT DISTINCT FROM %s
                                                       THEN site_check_rating END,
                              site_check_at = CASE WHEN file_rating_source_sha256 IS NOT DISTINCT FROM %s
                                                   THEN site_check_at END,
                              file_rating_source=%s, file_rating_source_sha256=%s WHERE id=%s""",
                    (rating, parse_date(pub), sha, sha, args.ods.name, sha, lid),
                )
                n += cur.rowcount
        # Rows stamped by an earlier file but absent from this one lose the stale claim.
        cur.execute(
            """UPDATE care_providers SET file_overall_rating=NULL, file_overall_rating_date=NULL,
                      site_check_rating=NULL, site_check_at=NULL,
                      file_rating_source=NULL, file_rating_source_sha256=NULL
                WHERE file_rating_source_sha256 IS NOT NULL AND file_rating_source_sha256 <> %s""",
            (sha,),
        )
        print(f"applied: {n} rows updated, {cur.rowcount} stale cleared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
