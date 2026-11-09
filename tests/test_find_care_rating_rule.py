"""Find Care (public radius tool) must serve the same rating as search and the
provider page, and must not list deregistered locations."""

from api.queries.providers import SERVED_RATING, SERVED_RATING_COLUMN
from api.queries.public_tools import NEARBY_PUBLIC_COUNT, NEARBY_PUBLIC_QUERY


def test_nearby_returns_the_served_rating():
    assert SERVED_RATING_COLUMN in NEARBY_PUBLIC_QUERY


def test_nearby_rating_filter_uses_the_served_rating():
    for query in (NEARBY_PUBLIC_QUERY, NEARBY_PUBLIC_COUNT):
        assert "LOWER(BTRIM(overall_rating))" not in query
        assert f"LOWER(BTRIM({SERVED_RATING})) = LOWER(BTRIM($5))" in query


def test_nearby_lists_active_locations_only():
    for query in (NEARBY_PUBLIC_QUERY, NEARBY_PUBLIC_COUNT):
        assert "UPPER(status) = 'ACTIVE'" in query
