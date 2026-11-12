#!/usr/bin/env python3
"""Read-only: check a snapshot's ratings and beds against CQC before it is delivered.

Rule (Henry, 12 Nov 2026): nothing customer-facing goes out until it has been
checked against the live CQC website. CQC's own location page is the freshest
source for a rating, then the monthly ratings file, then the API, which lags. This
reads each snapshot location's public page (about one request a second, never
/search, which robots.txt disallows) and compares:

* the overall rating the page shows for the location's current registration;
* whether the page shows only ratings inherited from a previous provider, which
  are not the location's own rating (a re-registered home has none of its own);
* the registration status and the registered bed count from CQC's API, read live
  on the day. CQC's pages do not publish a bed count, and the API's bed figure is
  the registered capacity; a snapshot built from an older API pull can be stale.

It writes nothing and reports one line per location. Exit status: 0 every location
matches; 1 at least one mismatch; 2 the check itself is not trustworthy (too many
unreadable pages, or the page markup looks to have changed).

Snapshot input, one location per line, ``id|rating|beds`` (rating ``Not yet
rated`` or empty for none; beds optional), or a JSON list of objects with ``id``,
``rating`` and ``beds``:

    python3 -m tools.check_snapshot_against_cqc --file snapshot.txt [--report out.md] [--json out.json]

``CQC_API_KEY`` (the same key the reconciliation workflow uses) enables the bed and
registration-status checks; without it they are reported as unchecked, never as
matching.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field

from tools.verify_file_ratings_against_site import PUBLISHED, RATING_RE, USER_AGENT, implausible_none_share

PAGE = "https://www.cqc.org.uk/location/{id}"
API = "https://api.service.cqc.org.uk/public/v1/locations/{id}"
NOT_RATED = "Not yet rated"
INHERITED_RE = re.compile(r"Ratings inherited from last inspection with previous provider", re.I)
PUBLISHED_ON_RE = re.compile(r"Last report published on (\d{1,2} \w+ \d{4})", re.I)
REGISTERED_RE = re.compile(r"Registered (?:on|since)\D{0,10}(\d{1,2} \w+ \d{4})", re.I)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class PageReading:
    """What a CQC location page shows."""

    rating: str  # one of PUBLISHED, or "none"
    inherited: bool  # ratings shown are a previous provider's
    report_published: str | None
    registered_on: str | None


@dataclass
class Finding:
    id: str
    name: str
    snapshot_rating: str
    page_rating: str
    inherited_only: bool
    snapshot_beds: int | None
    api_beds: int | None
    registration_status: str | None
    verdict: str  # match | mismatch | unreadable
    reasons: list[str] = field(default_factory=list)


def normalise_rating(value: str | None) -> str:
    """A snapshot rating as one of PUBLISHED (title case) or NOT_RATED."""
    text = (value or "").strip()
    for published in PUBLISHED:
        if text.lower() == published.lower():
            return published
    return NOT_RATED


def parse_page(html: str) -> PageReading:
    """Read the rating, inherited flag and dates from a location page."""
    m = RATING_RE.search(html)
    value = m.group(1).strip() if m else ""
    rating = next((p for p in PUBLISHED if p.lower() == value.lower()), "none")
    text = re.sub(r"\s+", " ", TAG_RE.sub(" ", html))
    pub = PUBLISHED_ON_RE.search(text)
    reg = REGISTERED_RE.search(text)
    return PageReading(
        rating=rating,
        inherited=INHERITED_RE.search(text) is not None,
        report_published=pub.group(1) if pub else None,
        registered_on=reg.group(1) if reg else None,
    )


def compare(
    snapshot_id: str,
    name: str,
    snapshot_rating: str | None,
    snapshot_beds: int | None,
    page: PageReading | None,
    api_beds: int | None,
    registration_status: str | None,
    api_checked: bool,
) -> Finding:
    """One location's verdict. Pure, so it can be tested without the network."""
    expected = normalise_rating(snapshot_rating)
    if page is None:
        return Finding(snapshot_id, name, expected, "unreadable", False, snapshot_beds, api_beds,
                       registration_status, "unreadable", ["CQC page could not be read"])
    reasons: list[str] = []
    page_rating = NOT_RATED if page.rating == "none" else page.rating
    if expected != page_rating:
        reasons.append(f"rating: snapshot {expected}, CQC page {page_rating}")
    inherited_only = page.rating == "none" and page.inherited
    if inherited_only and expected != NOT_RATED:
        reasons.append("CQC page shows only ratings inherited from a previous provider, not the location's own")
    if api_checked:
        if registration_status and registration_status.lower() != "registered":
            reasons.append(f"CQC API registration status is {registration_status}")
        if snapshot_beds is not None and api_beds is not None and snapshot_beds != api_beds:
            reasons.append(f"beds: snapshot {snapshot_beds}, CQC API {api_beds}")
        if snapshot_beds is not None and api_beds is None:
            reasons.append("beds: CQC API gave no bed count to compare")
    return Finding(snapshot_id, name, expected, page_rating, inherited_only, snapshot_beds, api_beds,
                   registration_status, "mismatch" if reasons else "match", reasons)


def parse_snapshot(text: str) -> list[dict]:
    """``id|rating|beds`` lines, or a JSON list of objects."""
    text = text.strip()
    if text.startswith("["):
        return [
            {"id": str(r["id"]), "name": r.get("name", ""), "rating": r.get("rating"), "beds": r.get("beds")}
            for r in json.loads(text)
        ]
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        beds = int(parts[2]) if len(parts) > 2 and parts[2] else None
        rows.append({"id": parts[0], "name": parts[3] if len(parts) > 3 else "",
                     "rating": parts[1] if len(parts) > 1 else None, "beds": beds})
    return rows


def _get(url: str, headers: dict[str, str]) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception as exc:  # no answer is unknown, never a match
        print(f"  request failed {url}: {exc}", file=sys.stderr)
        return None, ""


def read_page(location_id: str) -> PageReading | None:
    status, body = _get(PAGE.format(id=location_id), {"User-Agent": USER_AGENT})
    return parse_page(body) if status == 200 else None


def read_api(location_id: str, key: str) -> tuple[int | None, str | None]:
    status, body = _get(
        API.format(id=location_id),
        {"Accept": "application/json", "User-Agent": USER_AGENT, "Ocp-Apim-Subscription-Key": key},
    )
    if status != 200:
        return None, None
    try:
        data = json.loads(body)
    except ValueError:
        return None, None
    beds = data.get("numberOfBeds")
    if isinstance(beds, str) and beds.isdigit():
        beds = int(beds)
    return (beds if isinstance(beds, int) else None), data.get("registrationStatus")


def render_report(findings: list[Finding], checked_at: str, api_checked: bool) -> str:
    matched = sum(1 for f in findings if f.verdict == "match")
    lines = [
        f"# Snapshot check against CQC, {checked_at}",
        "",
        f"{matched} of {len(findings)} locations match. Ratings were read from each location's CQC page"
        + (", beds and registration status from the CQC API." if api_checked else
           "; beds and registration status were NOT checked (no CQC_API_KEY)."),
        "",
        "| Location | ID | Snapshot rating | CQC page | Beds (snapshot / API) | Verdict |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for f in findings:
        page = f.page_rating + (" (inherited only)" if f.inherited_only else "")
        beds = f"{f.snapshot_beds if f.snapshot_beds is not None else '-'} / {f.api_beds if f.api_beds is not None else '-'}"
        verdict = f.verdict if not f.reasons else f"{f.verdict}: " + "; ".join(f.reasons)
        lines.append(f"| {f.name or '-'} | {f.id} | {f.snapshot_rating} | {page} | {beds} | {verdict} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="snapshot: id|rating|beds lines, or a JSON list")
    ap.add_argument("--delay", type=float, default=1.1, help="seconds between locations")
    ap.add_argument("--report", help="write the markdown report here")
    ap.add_argument("--json", dest="json_out", help="write the findings as JSON here")
    args = ap.parse_args(argv)

    with open(args.file, encoding="utf-8") as fh:
        rows = parse_snapshot(fh.read())
    if not rows:
        print("snapshot is empty", file=sys.stderr)
        return 2
    key = os.environ.get("CQC_API_KEY")
    findings: list[Finding] = []
    seen: list[tuple[str, str]] = []
    for row in rows:
        page = read_page(row["id"])
        api_beds, status = read_api(row["id"], key) if key else (None, None)
        finding = compare(row["id"], row["name"], row["rating"], row["beds"], page, api_beds, status, bool(key))
        findings.append(finding)
        if page is not None:
            seen.append((row["id"], page.rating))
        time.sleep(args.delay)

    checked_at = time.strftime("%d %B %Y %H:%M UTC", time.gmtime())
    report = render_report(findings, checked_at, bool(key))
    print(report)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump([asdict(f) for f in findings], fh, indent=2)

    unreadable = sum(1 for f in findings if f.verdict == "unreadable")
    problem = implausible_none_share(seen)
    if problem or unreadable > len(findings) / 2:
        print(f"check is not trustworthy: {problem or f'{unreadable} of {len(findings)} pages unreadable'}", file=sys.stderr)
        return 2
    return 0 if all(f.verdict == "match" for f in findings) else 1


if __name__ == "__main__":
    sys.exit(main())
