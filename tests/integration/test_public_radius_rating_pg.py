"""The public radius tool's SQL, run by real Postgres.

Found 12 Nov 2026: a snapshot built from /api/v1/tools/radius-search was checked
against CQC's own pages and 5 of 23 homes carried a rating CQC's page did not
show, because the query projected the raw API ``overall_rating`` and bypassed the
rating rule. The rows below are literal; the query text is the production one.

The query uses PostGIS, so the test skips where PostGIS is not installed (CI's
migration-replay job has it).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

asyncpg = pytest.importorskip("asyncpg")

from api.queries.public_tools import NEARBY_PUBLIC_COUNT, NEARBY_PUBLIC_QUERY  # noqa: E402
from tests.integration.conftest import apply_full_schema, postgis_available  # noqa: E402

pytestmark = pytest.mark.asyncio

# Clitheroe, BB7 9AZ (lon, lat). Every row sits at the same point.
LON, LAT = -2.3965, 53.8708

# (id, name, status, raw API rating, rating_state, file rating, file edition, site rating, site at)
ROWS = [
    ("1-900000001", "File Good", "Active", "Good", "rated", "Good", "2026-10-01", None, None),
    ("1-900000002", "Page shows none", "Active", "Good", "rated", "Good", "2026-10-01", "none", "2026-11-12"),
    ("1-900000003", "Page says Outstanding", "Active", None, "not_published", None, None, "Outstanding", "2026-11-12"),
    ("1-900000004", "Old record, deregistered", "Deregistered", "Good", "rated", "Good", "2026-10-01", None, None),
    ("1-900000005", "Never rated", "Active", None, "not_yet_inspected", None, None, None, None),
]


def _date(value: str | None):
    return date.fromisoformat(value) if value else None


async def _load(conn):
    for lid, name, status, raw, state, file_r, edition, site, site_at in ROWS:
        await conn.execute(
            """
            INSERT INTO care_providers
              (id, name, slug, type, status, postcode, geom, overall_rating, rating_state,
               file_overall_rating, file_rating_edition_date, site_check_rating, site_check_at)
            VALUES ($1, $2, $3, 'Social Care Org', $4, 'BB7 9AZ',
                    ST_SetSRID(ST_MakePoint($5, $6), 4326), $7, $8, $9, $10, $11, $12)
            """,
            lid, name, lid, status, LON, LAT, raw, state, file_r, _date(edition), site,
            datetime.fromisoformat(site_at).replace(tzinfo=timezone.utc) if site_at else None,
        )


async def test_radius_query_serves_the_reconciled_rating_and_only_active_locations(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        if not await postgis_available(conn):
            pytest.skip("PostGIS is not installed in this database")
        await apply_full_schema(conn)
        await _load(conn)
        rows = await conn.fetch(NEARBY_PUBLIC_QUERY, LON, LAT, 5.0, None, None, None, 50)
        count = await conn.fetchrow(NEARBY_PUBLIC_COUNT, LON, LAT, 5.0, None, None, None)
        good_rows = await conn.fetch(NEARBY_PUBLIC_QUERY, LON, LAT, 5.0, None, "Good", None, 50)
        good_count = await conn.fetchrow(NEARBY_PUBLIC_COUNT, LON, LAT, 5.0, None, "Good", None)
    finally:
        await conn.close()

    by_name = {r["name"]: r for r in rows}
    # The deregistered record is not listed, and the count agrees with the list.
    assert "Old record, deregistered" not in by_name
    assert len(rows) == 4 and count["total"] == 4

    assert by_name["File Good"]["overall_rating"] == "Good"
    # A page showing no rating withholds the stored Good, with a reason.
    assert by_name["Page shows none"]["overall_rating"] is None
    assert by_name["Page shows none"]["rating_absence_reason"] == "not_published"
    assert by_name["Page shows none"]["rating_source"] == "cqc_website_unrated"
    # A newer page check wins where the stored rating is absent or different.
    assert by_name["Page says Outstanding"]["overall_rating"] == "Outstanding"
    assert by_name["Page says Outstanding"]["rating_source"] == "cqc_website"
    assert by_name["Never rated"]["overall_rating"] is None
    assert by_name["Never rated"]["rating_absence_reason"] == "not_yet_inspected"

    # The rating filter applies to the served rating, not the raw column: the
    # home whose page shows none is not a "Good" home, and the count agrees.
    assert [r["name"] for r in good_rows] == ["File Good"]
    assert good_count["total"] == 1
