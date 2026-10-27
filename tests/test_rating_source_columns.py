"""Every served rating says which source it came from and flags disagreements.

Behaviour of the rule itself is pinned against real Postgres in
tests/integration/test_rating_rule_pg.py; these check the plumbing: every API
projection carries the source columns, they reach every tier that sees the
rating, and one rule definition feeds every expression.
"""

import pytest

from api.config import BASIC_FIELDS, filter_fields
from api.queries.providers import (
    COMPARE_QUERY,
    CQC_ID_LOOKUP,
    DETAIL_BY_SLUG,
    NEARBY_QUERY,
    RATING_CONFLICT,
    RATING_SOURCE,
    RATING_SOURCE_DATE,
    SEARCH_SELECT,
    SEARCH_SELECT_RANKED,
    SERVED_RATING,
    SERVED_RATING_ABSENCE,
    WEBSITE_WINS,
)
from api.routers.providers import _row_to_dict


@pytest.mark.parametrize(
    "query", [SEARCH_SELECT, SEARCH_SELECT_RANKED, NEARBY_QUERY, DETAIL_BY_SLUG, CQC_ID_LOOKUP, COMPARE_QUERY]
)
def test_every_projection_carries_source_date_and_conflict(query):
    assert "AS rating_source," in query
    assert "AS rating_source_date" in query
    assert "AS rating_conflict" in query


def test_source_fields_reach_the_free_tier_with_the_rating():
    assert {"overall_rating", "rating_source", "rating_source_date", "rating_conflict"} <= set(BASIC_FIELDS)
    out = filter_fields(
        {
            "id": "1-1",
            "overall_rating": "Inadequate",
            "rating_absence_reason": None,
            "rating_source": "cqc_file",
            "rating_source_date": "2025-03-12",
            "rating_conflict": "file_vs_api",
        },
        "free",
    )
    assert out["overall_rating"] == "Inadequate"
    assert out["rating_source"] == "cqc_file"
    assert out["rating_conflict"] == "file_vs_api"


def test_one_rule_feeds_every_expression():
    for expr in (SERVED_RATING, SERVED_RATING_ABSENCE, RATING_SOURCE, RATING_SOURCE_DATE, RATING_CONFLICT):
        assert WEBSITE_WINS in expr
    # File before API: the API branch is the last one in the served rating.
    assert SERVED_RATING.index("file_overall_rating IS NOT NULL") < SERVED_RATING.index("rating_state = 'rated'")


def test_whole_row_lookup_serves_the_ruled_rating_not_the_raw_api_column():
    # A SELECT * row carries the raw API value; the rule's choice replaces it.
    row = {
        "id": "1-1",
        "overall_rating": "Inadequate",
        "rating_state": "not_published",
        "served_rating": "Good",
        "served_absence": None,
        "rating_source": "cqc_file",
    }
    d = _row_to_dict(row)
    assert d["overall_rating"] == "Good"
    assert d["rating_state"] == "rated"
    assert filter_fields(d, "free")["overall_rating"] == "Good"
    withheld = _row_to_dict({**row, "served_rating": None, "served_absence": "not_published"})
    assert withheld["overall_rating"] is None
    assert filter_fields(withheld, "free")["rating_absence_reason"] == "not_published"
