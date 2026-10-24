"""Read-only loaders shared by the report-readiness tools.

* :func:`iter_export` streams a CQC location-detail NDJSON export
  (``extract_cqc.py`` output, e.g. ``.tmp/cqc-export-20261020-final``).
* :func:`load_ratings_file` reads CQC's "Latest ratings" ODS for chosen domains,
  keeping the Inherited Rating (Y/N) flag the database does not store.
* :func:`readonly_connection` opens ``DATABASE_URL`` in a READ ONLY session.

Nothing here writes to a database or calls the network.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from tools.import_cqc_latest_ratings import iter_sheet_rows


def parse_day(text: Any) -> date | None:
    if not text:
        return None
    if isinstance(text, date):
        return text
    s = str(text).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def iter_export(path: str | Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class FileRating:
    rating: str
    publication_date: date | None
    inherited: bool | None


def load_ratings_file(
    path: str | Path, domains: Iterable[str] = ("Overall",)
) -> tuple[dict[str, dict[str, FileRating]], set[tuple[str, str]]]:
    """Return ``({location_id: {domain: FileRating}}, ambiguous)``.

    Only location-level rows (Service / Population Group == "Overall") are read.
    A location/domain with two different rows is ambiguous and skipped, never
    guessed -- the same rule as ``tools/import_cqc_latest_ratings.py``.
    Non-published values ("Not rated", blanks) are skipped.
    """
    wanted = set(domains)
    rows = iter_sheet_rows(Path(path), "Locations")
    header = next(rows)
    col = {name: i for i, name in enumerate(header)}
    found: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    for r in rows:
        r = r + [""] * (len(header) - len(r))
        if r[col["Service / Population Group"]] != "Overall":
            continue
        domain = r[col["Domain"]]
        if domain not in wanted:
            continue
        rating = r[col["Latest Rating"]].strip()
        if rating not in {"Outstanding", "Good", "Requires improvement", "Inadequate"}:
            continue
        found.setdefault((r[col["Location ID"]], domain), set()).add(
            (rating, r[col["Publication Date"]], r[col["Inherited Rating (Y/N)"]])
        )
    out: dict[str, dict[str, FileRating]] = {}
    ambiguous: set[tuple[str, str]] = set()
    for (lid, domain), values in found.items():
        if len({(v[0], v[1]) for v in values}) > 1:
            ambiguous.add((lid, domain))
            continue
        rating, pub, inh = next(iter(values))
        out.setdefault(lid, {})[domain] = FileRating(
            rating=rating,
            publication_date=parse_day(pub),
            inherited={"Y": True, "N": False}.get(inh.strip().upper()),
        )
    return out, ambiguous


def export_current_rating(row: dict[str, Any], domain: str = "Overall") -> tuple[str | None, date | None]:
    """The export's current rating text and report date for one domain."""
    current = row.get("currentRatings")
    if not isinstance(current, dict):
        return None, None
    overall = current.get("overall")
    if not isinstance(overall, dict):
        return None, None
    if domain == "Overall":
        return (
            overall.get("rating"),
            parse_day(current.get("reportDate") or overall.get("reportDate")),
        )
    for kq in overall.get("keyQuestionRatings") or []:
        if isinstance(kq, dict) and kq.get("name") == domain:
            return kq.get("rating"), parse_day(kq.get("reportDate"))
    return None, None


def readonly_connection():
    import psycopg2

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set")
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True)
    return conn
