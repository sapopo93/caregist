"""The CareGist rating rule, evaluated by real Postgres.

The precedence is SQL text in three places that must agree: the API
(api.queries.providers), the website (frontend/lib/directory-query-clauses.ts)
and order preparation (tools.prepare_order). Substring tests cannot show that a
CASE picks the right branch, so each case below runs the real expressions over
literal rows.

Rule: the ratings file is the main source; a CQC page check made on or after the
file's edition wins where it differs (a page showing none withholds the rating);
the API fills only the file's gaps; every disagreement is flagged.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

asyncpg = pytest.importorskip("asyncpg")

from api.queries.providers import (  # noqa: E402
    RATING_CONFLICT,
    RATING_SOURCE,
    RATING_SOURCE_DATE,
    SERVED_RATING,
    SERVED_RATING_ABSENCE,
)
from tools.prepare_order import RECONCILED_RATING_SQL as ORDER_SQL  # noqa: E402

DATABASE_URL = os.getenv("CAREGIST_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="CAREGIST_TEST_DATABASE_URL not set")

TS = (Path(__file__).resolve().parents[2] / "frontend" / "lib" / "directory-query-clauses.ts").read_text()
WEB_SQL = re.search(r"RECONCILED_RATING_SQL = `(.*?)`;", TS, re.S).group(1)
WEB_SOURCE = re.search(r"RATING_SOURCE_SQL = `(.*?)`;", TS, re.S).group(1)

EDITION = date(2026, 10, 1)
AFTER = datetime(2026, 10, 20, tzinfo=timezone.utc)
BEFORE = datetime(2026, 9, 20, tzinfo=timezone.utc)

# (name, overall_rating, rating_state, file_rating, file_edition, site_rating, site_at,
#  expected served, expected source, expected conflict, expected absence)
CASES = [
    ("file fills an API gap", None, "not_published", "Inadequate", EDITION, None, None,
     "Inadequate", "cqc_file", None, None),
    ("file wins over a differing API rating", "Inadequate", "rated", "Good", EDITION, None, None,
     "Good", "cqc_file", "file_vs_api", None),
    ("file and API agree", "Good", "rated", "Good", EDITION, None, None,
     "Good", "cqc_file", None, None),
    ("API only where the file has none", "Good", "rated", None, None, None, None,
     "Good", "cqc_api", None, None),
    ("newer page check wins", None, "not_published", "Good", EDITION, "Inadequate", AFTER,
     "Inadequate", "cqc_website", "website_vs_file", None),
    ("page check older than the file is superseded", None, "not_published", "Good", EDITION, "Inadequate", BEFORE,
     "Good", "cqc_file", None, None),
    ("page showing no rating withholds it", "Good", "rated", "Good", EDITION, "none", AFTER,
     None, "cqc_website_unrated", "website_vs_file", "not_published"),
    ("agreeing page check keeps the file as source", None, "not_published", "Good", EDITION, "Good", AFTER,
     "Good", "cqc_file", None, None),
    ("page check for a location the file lacks", None, "not_published", None, None, "Good", AFTER,
     "Good", "cqc_website", None, None),
    ("no source at all keeps the state as the reason", None, "not_yet_inspected", None, None, None, None,
     None, None, None, "not_yet_inspected"),
]

COLUMNS = (
    "overall_rating, rating_state, file_overall_rating, file_rating_edition_date, "
    "site_check_rating, site_check_at, file_overall_rating_date, last_published_rating_date"
)


async def _evaluate(conn, case):
    _, api, state, file_r, edition, site, site_at = case[:7]
    sql = (
        f"SELECT {SERVED_RATING} AS served, {RATING_SOURCE} AS source, {RATING_CONFLICT} AS conflict, "
        f"{SERVED_RATING_ABSENCE} AS absence, {RATING_SOURCE_DATE} AS source_date, "
        f"{WEB_SQL} AS web, {WEB_SOURCE} AS web_source, {ORDER_SQL} AS order_rating "
        f"FROM (SELECT $1::text, $2::text, $3::text, $4::date, $5::text, $6::timestamptz, "
        f"$7::date, $8::date) AS care_providers({COLUMNS})"
    )
    return await conn.fetchrow(sql, api, state, file_r, edition, site, site_at, date(2026, 9, 30), date(2026, 9, 1))


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
async def test_rating_rule(case):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await _evaluate(conn, case)
    finally:
        await conn.close()
    served, source, conflict, absence = case[7:]
    assert row["served"] == served
    assert row["source"] == source
    assert row["conflict"] == conflict
    assert row["absence"] == absence
    # The website and order preparation serve the same rating as the API. (For a
    # row with no source the website falls back to the API's stored sentinel text,
    # which is NULL here.)
    assert row["web"] == served
    assert row["order_rating"] == served
    assert row["web_source"] == source
    if source == "cqc_website":
        assert row["source_date"] == AFTER.date()
