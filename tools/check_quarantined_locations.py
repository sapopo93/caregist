#!/usr/bin/env python3
"""Read-only: check each unresolved quarantined location against CQC's sources.

A quarantined location is ACTIVE in care_providers but absent from the latest
CQC directory snapshot, and its detail endpoint did not confirm it. This lists
every unresolved quarantine row and looks each id up in three places:

* the CQC API (GET /locations/{id});
* the CQC website page (https://www.cqc.org.uk/location/{id});
* optionally a monthly file, ``--directory-csv`` (the reconciliation source) or
  ``--ratings-file`` (CQC's latest-ratings ODS, which lists rated locations
  only, so absence from it is never evidence of anything).

It writes nothing: the database session is read-only and the proposed SQL is
printed, never run. A location found in a source is a candidate to resolve; one
absent from the API and the website stays quarantined; anything else is
inconclusive and is reported as such.

    python3 -m tools.check_quarantined_locations [--directory-csv PATH] [--ratings-file PATH.ods] [--out FILE]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.service.cqc.org.uk/public/v1"
PAGE = "https://www.cqc.org.uk/location/{id}"
DIRECTORY_ID_COLUMN = "CQC Location ID (for office use only)"
USER_AGENT = "CareGist-quarantine-check/1.0 (+https://caregist.co.uk)"
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)

FOUND, ABSENT, UNKNOWN, NOT_CHECKED = "found", "absent", "unknown", "not_checked"

UNRESOLVED_SQL = """
SELECT q.location_id, q.reason, q.last_error, p.status, p.name
  FROM reconciliation_quarantined_locations q
  LEFT JOIN care_providers p ON p.id::text = q.location_id
 WHERE q.resolved_at IS NULL
 ORDER BY q.location_id
"""


def classify_http(status: int | None) -> str:
    """200 is found, 404 is absent, anything else (or no answer) is unknown."""
    if status == 200:
        return FOUND
    if status == 404:
        return ABSENT
    return UNKNOWN


def verdict(api: str, site: str, files: dict[str, str]) -> str:
    """resolve_candidate when any source holds the id; keep_quarantined only when
    both live sources say it is absent; inconclusive otherwise."""
    if FOUND in (api, site, *files.values()):
        return "resolve_candidate"
    if api == ABSENT and site == ABSENT:
        return "keep_quarantined"
    return "inconclusive"


def fetch_status(url: str, headers: dict[str, str]) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception as exc:  # no answer is unknown, never absent
        print(f"  request failed {url}: {exc}", file=sys.stderr)
        return None, ""


def check_api(location_id: str, api_key: str | None) -> tuple[str, dict]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if api_key:
        headers["Ocp-Apim-Subscription-Key"] = api_key
    status, body = fetch_status(f"{API_BASE}/locations/{location_id}", headers)
    detail: dict = {"http": status}
    if status == 200:
        try:
            data = json.loads(body)
            detail.update(name=data.get("name"), registrationStatus=data.get("registrationStatus"))
        except ValueError:
            pass
    return classify_http(status), detail


def check_site(location_id: str) -> tuple[str, dict]:
    status, body = fetch_status(PAGE.format(id=location_id), {"User-Agent": USER_AGENT})
    detail: dict = {"http": status}
    if status == 200:
        m = TITLE_RE.search(body)
        detail["title"] = re.sub(r"\s+", " ", m.group(1)).strip() if m else None
        detail["mentionsDeregistered"] = "deregistered" in body.lower()
    return classify_http(status), detail


def directory_ids(path: str) -> set[str]:
    """Location ids in a CQC directory CSV, which opens with a few preamble lines."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    start = next((i for i, line in enumerate(lines) if DIRECTORY_ID_COLUMN in line), None)
    if start is None:
        raise SystemExit(f"{path}: no '{DIRECTORY_ID_COLUMN}' header found")
    return {
        row[DIRECTORY_ID_COLUMN].strip()
        for row in csv.DictReader(lines[start:])
        if row.get(DIRECTORY_ID_COLUMN)
    }


def ratings_file_ids(path: str) -> set[str]:
    from tools.import_cqc_latest_ratings import overall_ratings

    found, ambiguous = overall_ratings(Path(path))
    return set(found) | set(ambiguous)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory-csv")
    ap.add_argument("--ratings-file")
    ap.add_argument("--delay", type=float, default=1.1, help="seconds between website requests")
    ap.add_argument("--out", help="write the per-location evidence as JSON")
    args = ap.parse_args(argv)

    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=True)
    with conn.cursor() as cur:
        cur.execute(UNRESOLVED_SQL)
        rows = cur.fetchall()
    conn.close()

    file_sets = {}
    if args.directory_csv:
        file_sets["directory_csv"] = directory_ids(args.directory_csv)
    if args.ratings_file:
        file_sets["ratings_file"] = ratings_file_ids(args.ratings_file)
    api_key = os.environ.get("CQC_API_KEY")

    results = []
    for location_id, reason, last_error, status, name in rows:
        api, api_detail = check_api(location_id, api_key)
        site, site_detail = check_site(location_id)
        files = {k: (FOUND if location_id in ids else ABSENT) for k, ids in file_sets.items()}
        results.append({
            "locationId": location_id,
            "dbStatus": status,
            "dbName": name,
            "quarantineReason": reason,
            "lastError": last_error,
            "api": {"result": api, **api_detail},
            "website": {"result": site, **site_detail},
            "files": files,
            "verdict": verdict(api, site, files),
        })
        time.sleep(args.delay)

    resolve = [r["locationId"] for r in results if r["verdict"] == "resolve_candidate"]
    report = {
        "unresolved": len(results),
        "resolveCandidates": len(resolve),
        "keepQuarantined": sum(r["verdict"] == "keep_quarantined" for r in results),
        "inconclusive": sum(r["verdict"] == "inconclusive" for r in results),
        "results": results,
        "proposedSqlNotRun": (
            "UPDATE reconciliation_quarantined_locations SET resolved_at = NOW(), updated_at = NOW() "
            f"WHERE resolved_at IS NULL AND location_id = ANY(ARRAY{resolve!r});"
            if resolve else None
        ),
    }
    text = json.dumps(report, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
