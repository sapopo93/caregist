"""The public radius tool serves the CareGist rating rule, not the raw API rating.

On 12 Nov 2026 a snapshot built from this endpoint was checked against CQC's own
pages: 5 of 23 homes carried a rating CQC's page did not show. The cause was that
this path projected and filtered on the raw ``overall_rating`` column, bypassing
SERVED_RATING. These tests pin the SQL text; behaviour of the rule itself is
pinned on real Postgres in tests/integration/test_rating_rule_pg.py.
"""

import pytest

from api.queries.providers import (
    RATING_SOURCE_COLUMNS,
    SERVED_RATING,
    SERVED_RATING_ABSENCE,
    SERVED_RATING_ABSENCE_COLUMN,
    SERVED_RATING_COLUMN,
    SERVED_RATING_NORMALISED,
)
from api.queries.public_tools import NEARBY_PUBLIC_COUNT, NEARBY_PUBLIC_QUERY


def _projection(query: str) -> str:
    return query.split("FROM care_providers")[0]


def test_projection_serves_the_reconciled_rating_not_the_raw_column():
    projection = _projection(NEARBY_PUBLIC_QUERY)
    assert f"{SERVED_RATING} AS overall_rating" in projection
    assert f"{SERVED_RATING_ABSENCE} AS rating_absence_reason" in projection
    # Once the three served-rating column groups are removed, no raw
    # `overall_rating` select item is left over from the old query.
    remainder = projection
    for part in (SERVED_RATING_COLUMN, SERVED_RATING_ABSENCE_COLUMN, RATING_SOURCE_COLUMNS):
        remainder = remainder.replace(part, "")
    assert "overall_rating" not in remainder


@pytest.mark.parametrize("query", [NEARBY_PUBLIC_QUERY, NEARBY_PUBLIC_COUNT])
def test_rating_filter_uses_the_served_rating(query):
    assert f"{SERVED_RATING_NORMALISED} = LOWER(BTRIM($5))" in query
    # The old filter compared the raw column.
    assert "LOWER(BTRIM(overall_rating))" not in query


@pytest.mark.parametrize("query", [NEARBY_PUBLIC_QUERY, NEARBY_PUBLIC_COUNT])
def test_only_active_locations_are_listed(query):
    assert "UPPER(status) = 'ACTIVE'" in query


def test_count_and_list_apply_the_same_predicates():
    where = lambda q: q.split("WHERE", 1)[1].split("ORDER BY")[0].split("LIMIT")[0].strip()
    assert where(NEARBY_PUBLIC_QUERY) == where(NEARBY_PUBLIC_COUNT)
