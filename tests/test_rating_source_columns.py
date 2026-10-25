"""A rating served from CQC's ratings file says so, on every API projection.

The region and services pages render API search rows. Without the source on
those rows a file-sourced rating was shown unlabelled there, while the directory
pages (which query the database directly) labelled it.
"""

import pytest

from api.config import BASIC_FIELDS, filter_fields
from api.queries.providers import (
    FILE_RATING_SERVABLE,
    NEARBY_QUERY,
    RATING_SOURCE,
    RATING_SOURCE_DATE,
    SEARCH_SELECT,
    SEARCH_SELECT_RANKED,
    SERVED_RATING,
    SERVED_RATING_ABSENCE,
)


@pytest.mark.parametrize("query", [SEARCH_SELECT, SEARCH_SELECT_RANKED, NEARBY_QUERY])
def test_row_projections_carry_the_rating_source(query):
    assert "AS rating_source," in query
    assert "AS rating_source_date" in query


def test_source_fields_reach_the_free_tier_with_the_rating():
    assert {"overall_rating", "rating_source", "rating_source_date"} <= set(BASIC_FIELDS)
    # The shape of a search row: the served rating, no raw rating_state.
    out = filter_fields(
        {
            "id": "1-1",
            "overall_rating": "Inadequate",
            "rating_absence_reason": None,
            "rating_source": "cqc_file",
            "rating_source_date": "2025-03-12",
        },
        "free",
    )
    assert out["overall_rating"] == "Inadequate"
    assert out["rating_source"] == "cqc_file"
    assert out["rating_source_date"] == "2025-03-12"


def test_source_follows_the_same_rule_that_serves_the_rating():
    # One definition of "a file rating may be served": the rating, its absence
    # reason, its source label and its date cannot drift apart.
    for expr in (SERVED_RATING, SERVED_RATING_ABSENCE, RATING_SOURCE, RATING_SOURCE_DATE):
        assert FILE_RATING_SERVABLE in expr
    assert RATING_SOURCE.startswith("CASE WHEN rating_state = 'rated' THEN NULL ")
    assert "'cqc_file_disputed'" in RATING_SOURCE
    assert RATING_SOURCE_DATE.startswith("CASE WHEN rating_state = 'rated' THEN NULL ")
