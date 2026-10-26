#!/usr/bin/env python3
"""Find CQC's current "Latest ratings" ODS file and its edition date.

Reads CQC's public data page, picks the newest linked ratings ODS and prints
``url=`` and ``edition=`` lines (for $GITHUB_OUTPUT). The edition date is taken
from the filename (``2026-08-04_Latest_ratings.ods`` or
``01_October_2026_Latest_ratings.ods``). A link whose date cannot be read is
never guessed at: the script fails and lists what it saw. Read-only.

    python3 -m tools.find_cqc_ratings_file [--page URL]
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from datetime import date, datetime
from urllib.parse import unquote, urljoin

PAGE = "https://www.cqc.org.uk/about-us/transparency/using-cqc-data"
USER_AGENT = "CareGist-ratings-import/1.0 (+https://caregist.co.uk)"
LINK_RE = re.compile(r'href="([^"]+\.ods)"', re.IGNORECASE)
ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
LONG_RE = re.compile(r"(\d{1,2})[_ -]([A-Za-z]+)[_ -](\d{4})")


def edition_from_name(name: str) -> date | None:
    name = unquote(name.rsplit("/", 1)[-1])
    if m := ISO_RE.search(name):
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    if m := LONG_RE.search(name):
        try:
            return datetime.strptime(f"{m[1]} {m[2]} {m[3]}", "%d %B %Y").date()
        except ValueError:
            return None
    return None


def ratings_links(html: str, base: str) -> list[str]:
    return [urljoin(base, href) for href in LINK_RE.findall(html) if "rating" in href.lower()]


def newest(links: list[str]) -> tuple[str, date] | None:
    dated = [(edition_from_name(u), u) for u in links]
    dated = [(d, u) for d, u in dated if d]
    if not dated:
        return None
    d, u = max(dated)
    return u, d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--page", default=PAGE)
    args = ap.parse_args(argv)
    req = urllib.request.Request(args.page, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8", "replace")
    links = ratings_links(html, args.page)
    found = newest(links)
    if not found:
        print(f"no dated ratings ODS link on {args.page}; links seen: {links}", file=sys.stderr)
        return 1
    url, edition = found
    print(f"url={url}")
    print(f"edition={edition.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
