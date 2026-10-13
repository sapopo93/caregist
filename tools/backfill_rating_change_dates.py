#!/usr/bin/env python3
"""Date historical ``rating_changed`` ledger rows from CQC's own report date.

Since PR #77 (3 October 2026) ingestion writes each new ``rating_changed`` event
with the destination rating's CQC report date. The rows written before that,
observed 10 August to 20 September 2026, have a NULL ``effective_date``, so any
"changed in the last N days" query silently excludes them.

This tool dates a NULL row only when the date is CQC's own publication date for
the rating that row moved *to*, and nothing else. A row qualifies when all of
these hold:

* both ``old_value`` and ``new_value`` are published CQC grades that differ
  (sentinel and blank-destination rows from before the rating-state fix are
  representation churn, not movement, and stay undated);
* it is the latest ``rating_changed`` row for its location, so the location's
  current rating can be the one it moved to;
* ``care_providers`` still serves that same rating (``rating_state = 'rated'``)
  with a ``last_published_rating_date``, which ingestion takes only from
  ``cqc.currentRatings`` report dates;
* that date is on or before the day the row was observed. A report dated after
  the observation belongs to a later publication of the same grade.

Observation, ingestion and inspection dates are never used as a substitute.
Rows that fail any test stay NULL and are counted by reason in the report.

Default is a dry run that changes nothing. ``--apply`` writes in one
transaction, and only to rows whose ``effective_date`` is still NULL, so a
second run is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.rating_states import PUBLISHED_RATING_VALUES, normalize_rating_text  # noqa: E402

EFFECTIVE_DATE_SOURCE = "cqc.currentRatings report date (backfilled from care_providers.last_published_rating_date)"

CANDIDATES_SQL = """
SELECT DISTINCT ON (t.location_id)
       t.id,
       t.location_id,
       t.old_value,
       t.new_value,
       t.observed_at,
       t.effective_date,
       cp.rating_state,
       cp.overall_rating,
       cp.last_published_rating_date
  FROM trusted_event_ledger t
  LEFT JOIN care_providers cp ON cp.id = t.location_id
 WHERE t.event_type = 'rating_changed'
 ORDER BY t.location_id, t.observed_at DESC, t.id DESC
"""

UNDATED_COUNT_SQL = """
SELECT COUNT(*) FROM trusted_event_ledger
 WHERE event_type = 'rating_changed' AND effective_date IS NULL
"""

UPDATE_SQL = """
UPDATE trusted_event_ledger
   SET effective_date = $2,
       effective_date_source = $3,
       metadata = metadata || jsonb_build_object(
         'effective_date_backfill',
         jsonb_build_object('tool', 'backfill_rating_change_dates', 'applied_at', NOW())
       )
 WHERE id = $1
   AND event_type = 'rating_changed'
   AND effective_date IS NULL
"""


@dataclass(frozen=True)
class Decision:
    ledger_id: int
    effective_date: date | None
    reason: str


def _rating_text(value: Any) -> str | None:
    """Return the rating text a ledger JSONB value holds, or None."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            pass
    if isinstance(value, str):
        return normalize_rating_text(value)
    return None


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def decide(row: dict[str, Any]) -> Decision:
    """Decide whether one latest-per-location ledger row can be dated."""
    ledger_id = int(row["id"])
    if row.get("effective_date") is not None:
        return Decision(ledger_id, None, "already_dated")

    old = _rating_text(row.get("old_value"))
    new = _rating_text(row.get("new_value"))
    if old not in PUBLISHED_RATING_VALUES or new not in PUBLISHED_RATING_VALUES:
        return Decision(ledger_id, None, "not_a_grade_to_grade_move")
    if old == new:
        return Decision(ledger_id, None, "not_a_grade_to_grade_move")

    if row.get("rating_state") != "rated":
        return Decision(ledger_id, None, "location_not_currently_rated")
    if normalize_rating_text(row.get("overall_rating")) != new:
        return Decision(ledger_id, None, "current_rating_differs_from_destination")

    report_date = _as_date(row.get("last_published_rating_date"))
    if report_date is None:
        return Decision(ledger_id, None, "no_cqc_report_date_on_record")
    observed = _as_date(row.get("observed_at"))
    if observed is None or report_date > observed:
        return Decision(ledger_id, None, "report_date_after_observation")

    return Decision(ledger_id, report_date, "dated")


async def backfill(conn, *, apply: bool) -> dict[str, Any]:
    undated_before = int(await conn.fetchval(UNDATED_COUNT_SQL) or 0)
    rows = [dict(r) for r in await conn.fetch(CANDIDATES_SQL)]
    decisions = [decide(row) for row in rows]
    reasons = Counter(d.reason for d in decisions)
    # Older NULL rows for a location are superseded by a later move, so the
    # current rating can never date them.
    reasons["superseded_by_later_move"] = undated_before - sum(
        1 for row in rows if row.get("effective_date") is None
    )
    to_date = [d for d in decisions if d.effective_date is not None]

    written = 0
    if apply and to_date:
        async with conn.transaction():
            for d in to_date:
                status = await conn.execute(UPDATE_SQL, d.ledger_id, d.effective_date, EFFECTIVE_DATE_SOURCE)
                written += int(status.split()[-1]) if status.startswith("UPDATE") else 0

    return {
        "mode": "apply" if apply else "dry-run",
        "undated_rating_changed_rows": undated_before,
        "datable_rows": len(to_date),
        "rows_written": written,
        "reasons": dict(sorted(reasons.items())),
    }


def _load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key and key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip()


async def _run(database_url: str, *, apply: bool) -> dict[str, Any]:
    conn = await asyncpg.connect(database_url)
    try:
        return await backfill(conn, apply=apply)
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Date historical rating_changed rows from CQC report dates")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--apply", action="store_true", help="Write the dates. Without it, report only.")
    args = parser.parse_args()

    database_url = args.database_url
    if not database_url:
        _load_env_file()
        database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set it in the environment.", file=sys.stderr)
        return 2

    report = asyncio.run(_run(database_url, apply=args.apply))
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
