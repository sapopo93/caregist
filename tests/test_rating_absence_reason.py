"""Every withheld rating states why it was withheld.

`SERVED_RATING` renders NULL for six different source conditions. Collapsing
them at the API boundary destroys the distinction a reader most needs -- a
location CQC has never inspected is a new entrant, one whose rating CQC has
withdrawn is a regulatory event, and the two look identical as a bare null.

It also produces a *false gap*: a response that says "no rating" without saying
whether the source published none or whether this build could not read what it
published is asserting something about CQC that CQC did not say. These tests pin
that every suppression is attributed, in `rating_states`' own vocabulary.
"""

import pytest

from api.config import BASIC_FIELDS, filter_fields
from api.queries.providers import (
    NEARBY_QUERY,
    SEARCH_SELECT,
    SEARCH_SELECT_RANKED,
    SERVED_RATING_ABSENCE,
)
from api.services.rating_states import (
    NON_RATED_STATES,
    RATED,
    RATING_STATES,
    UNKNOWN,
)


def _row(**kw):
    base = {"id": "1-1", "name": "Example", "overall_rating": None, "rating_state": None}
    base.update(kw)
    return base


# --- the reason travels with the rating, at every tier that sees the rating ---

def test_reason_is_a_basic_field_like_the_rating_it_explains():
    # A free-tier reader is exactly the one who would otherwise see a bare null.
    assert "overall_rating" in BASIC_FIELDS
    assert "rating_absence_reason" in BASIC_FIELDS


@pytest.mark.parametrize("query", [SEARCH_SELECT, SEARCH_SELECT_RANKED, NEARBY_QUERY])
def test_row_projections_carry_the_reason(query):
    assert "rating_absence_reason" in query


def test_sql_returns_null_reason_only_for_a_rated_row():
    # The two fields are complementary: never both populated, never both empty.
    assert SERVED_RATING_ABSENCE == (
        "CASE WHEN rating_state = 'rated' THEN NULL ELSE rating_state END"
    )


# --- a served rating has no absence to explain ---

def test_rated_row_serves_the_rating_and_no_reason():
    out = filter_fields(
        _row(overall_rating="Good", rating_state=RATED, rating_absence_reason=None),
        "free",
    )
    assert out["overall_rating"] == "Good"
    assert out["rating_absence_reason"] is None


# --- each non-rated state is reported as itself, not flattened ---

@pytest.mark.parametrize("state", sorted(NON_RATED_STATES))
def test_each_non_rated_state_is_reported_distinctly(state):
    out = filter_fields(
        _row(overall_rating=None, rating_state=state, rating_absence_reason=state),
        "free",
    )
    assert out["overall_rating"] is None
    assert out["rating_absence_reason"] == state


def test_the_six_states_do_not_collapse_to_one_answer():
    reasons = {
        filter_fields(_row(rating_state=s, rating_absence_reason=s), "free")[
            "rating_absence_reason"
        ]
        for s in RATING_STATES - {RATED}
    }
    assert reasons == RATING_STATES - {RATED}


# --- the paths SQL cannot see must not emit a bare, unattributed null ---

def test_select_star_row_without_the_derived_column_still_explains_itself():
    # Detail / CQC-id / compare select *, so they carry rating_state but not the
    # CASE expression. The reason is recovered from the state.
    out = filter_fields(_row(rating_state="not_yet_inspected"), "free")
    assert out["rating_absence_reason"] == "not_yet_inspected"


def test_legacy_writer_claiming_rated_reports_the_stored_value_not_a_bare_null():
    # The false-gap case: state still says 'rated' so SQL derives a NULL reason,
    # while the serialiser suppresses the unreadable value. Without recovery the
    # row would claim "no rating" with no reason at all.
    row = _row(overall_rating="Suspended", rating_state=RATED, rating_absence_reason=None)
    out = filter_fields(row, "free")
    assert out["overall_rating"] is None, "unreadable text must not serve as a rating"
    assert out["rating_absence_reason"] == UNKNOWN


def test_pre_migration_row_with_no_state_at_all_is_unknown_not_guessed():
    # Storage says nothing about what the source published. 'unknown' is honest;
    # inferring 'not_published' would invent a CQC statement.
    row = {"id": "1-1", "name": "Example", "overall_rating": None}
    out = filter_fields(row, "free")
    assert out["rating_absence_reason"] == UNKNOWN


def test_no_suppressed_rating_is_ever_left_unattributed():
    for state in RATING_STATES:
        for value in (None, "", "Good", "Suspended"):
            out = filter_fields(
                _row(overall_rating=value or None, rating_state=state), "free"
            )
            if out["overall_rating"] is None:
                assert out["rating_absence_reason"], (
                    f"bare null for state={state!r} value={value!r}"
                )
            else:
                assert out["rating_absence_reason"] is None
