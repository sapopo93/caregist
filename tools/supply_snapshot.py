#!/usr/bin/env python3
"""Read-only: the older-people care home supply around a postcode, checked against live CQC.

Builds the data table for a CareGist supply snapshot. CareGist's database gives the
candidate list (active care home locations registered for adults over 65 within a
radius). Every candidate is then read from CQC itself, per the rule of 12 Nov 2026
(nothing customer-facing goes out until checked against the live CQC website):

* the overall rating, and whether only an earlier provider's ratings are shown, from
  the location's public CQC page (about one request a second; never /search);
* registration status and bed count from CQC's API (CQC's pages do not publish beds);
* the registration date from the page.

A home that CQC's API no longer shows as registered is dropped and listed. The output
is one line per home (rating, beds and dates from CQC, not from our database) plus a
checksum, so the table can be copied out of a CI log and verified. Writes nothing.

    python3 -m tools.supply_snapshot --postcode "CA11 8TZ" --radius 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request

from tools.check_snapshot_against_cqc import NOT_RATED, read_api, read_page
from tools.verify_file_ratings_against_site import USER_AGENT, implausible_none_share

CANDIDATES = """
SELECT id, name, town, postcode, number_of_beds, service_types, last_inspection_date,
       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography) / 1609.34 AS miles
  FROM care_providers
 WHERE geom IS NOT NULL
   AND UPPER(status) = 'ACTIVE'
   AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, %(radius)s * 1609.34)
   AND service_types ILIKE '%%Care home service%%'
   AND coalesce(specialisms, '') ILIKE '%%Over 65%%'
 ORDER BY miles, id
"""


def geocode(postcode: str) -> tuple[float, float]:
    url = "https://api.postcodes.io/postcodes/" + urllib.request.quote(postcode.strip())
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)["result"]
    return float(data["latitude"]), float(data["longitude"])


def line(row: dict) -> str:
    return "|".join(str(row[k]) for k in
                    ("miles", "name", "town", "beds", "nursing", "rating", "last_inspection", "registered_on", "id"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--postcode", required=True)
    ap.add_argument("--radius", type=float, default=5.0, help="miles")
    ap.add_argument("--delay", type=float, default=1.1)
    args = ap.parse_args(argv)

    import psycopg2

    key = os.environ.get("CQC_API_KEY")
    if not key:
        print("CQC_API_KEY is required: beds and registration status must come from CQC", file=sys.stderr)
        return 2
    lat, lon = geocode(args.postcode)
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute(CANDIDATES, {"lat": lat, "lon": lon, "radius": args.radius})
        candidates = cur.fetchall()

    rows: list[dict] = []
    dropped: list[str] = []
    unreadable: list[str] = []
    seen: list[tuple[str, str]] = []
    for lid, name, town, postcode, db_beds, service_types, db_last, miles in candidates:
        page = read_page(lid)
        api_beds, status = read_api(lid, key)
        time.sleep(args.delay)
        if page is None or status is None:
            unreadable.append(f"{lid} {name}")
            continue
        seen.append((lid, page.rating))
        if status.lower() != "registered":
            dropped.append(f"{lid} {name} ({status})")
            continue
        rating = NOT_RATED if page.rating == "none" else page.rating
        if page.rating == "none" and page.inherited:
            rating = "No own rating (inherited)"
        rows.append({
            "miles": f"{float(miles):.1f}", "name": name, "town": town, "postcode": postcode,
            "beds": api_beds if api_beds is not None else "?",
            "nursing": "Yes" if "with nursing" in (service_types or "") else "No",
            "rating": rating,
            "last_inspection": str(db_last) if db_last else "Not held",
            "registered_on": page.registered_on or "?", "id": lid,
        })

    print(f"# Supply within {args.radius:g} miles of {args.postcode} (lat {lat:.5f}, lon {lon:.5f}), "
          f"read from CQC {time.strftime('%d %B %Y %H:%M UTC', time.gmtime())}")
    print("# miles|name|town|beds|nursing|rating|last_inspection|registered_on|id")
    body = [line(r) for r in rows]
    for b in body:
        print(b)
    digest = hashlib.sha256("\n".join(body).encode()).hexdigest()
    print(f"# homes={len(rows)} beds={sum(r['beds'] for r in rows if isinstance(r['beds'], int))} sha256={digest}")
    for d in dropped:
        print(f"# dropped (not registered per CQC API): {d}")
    for u in unreadable:
        print(f"# UNREADABLE, check by hand: {u}")
    problem = implausible_none_share(seen)
    if problem:
        print(f"check is not trustworthy: {problem}", file=sys.stderr)
        return 2
    return 1 if unreadable else 0


if __name__ == "__main__":
    sys.exit(main())
