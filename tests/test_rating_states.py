"""Regression tests for CQC rating-state classification.

The defect these pin: CQC publishes a real rating, a sentinel string, or
nothing at all through ``currentRatings.overall.rating``. The pipeline treated
all three as a rating value, so blanks and sentinels were stored (and
overwrote real ratings) and representation churn was recorded as rating
movement. These tests fix the meaning of each shape.
"""

from __future__ import annotations

import pytest

from api.services.rating_states import (
    NON_RATED_STATES,
    NOT_APPLICABLE,
    NOT_PUBLISHED,
    NOT_YET_INSPECTED,
    RATED,
    RATING_STATES,
    SENTINEL_STATES,
    UNKNOWN,
    UNRATED,
    assess_location_rating,
    classify_rating,
    is_published_value,
    is_sentinel_rating_text,
    normalize_rating_text,
    stored_rating_is_published,
)

# --- published ratings ------------------------------------------------------

RATED_VALUES = [
    "Outstanding",
    "Good",
    "Requires improvement",
    "Inadequate",
    "  Good  ",
    "Requires Improvement",
    "GOOD",
]


@pytest.mark.parametrize("raw_value", RATED_VALUES)
def test_real_ratings_are_rated_and_keep_their_value(raw_value):
    state, value = classify_rating(raw_value, current_ratings_present=True, historic_rating_present=False)

    assert state == RATED
    assert is_published_value(state) is True
    assert value is not None
    assert value == raw_value.strip()
    assert value != ""


def test_rating_value_is_never_a_sentinel():
    for sentinel in ("Not Yet Inspected", "No Published Rating", "Inspected but not rated"):
        state, value = classify_rating(sentinel, True, False)
        assert state in NON_RATED_STATES
        assert value is None


# --- sentinels (every observed one, casing and whitespace variants) ----------

SENTINELS = [
    ("Not Yet Inspected", NOT_YET_INSPECTED),
    ("not yet inspected", NOT_YET_INSPECTED),
    ("NOT YET INSPECTED", NOT_YET_INSPECTED),
    ("Not  Yet   Inspected", NOT_YET_INSPECTED),
    ("  Not Yet Inspected  ", NOT_YET_INSPECTED),
    ("No Published Rating", NOT_PUBLISHED),
    ("No published rating", NOT_PUBLISHED),
    ("NO PUBLISHED RATING", NOT_PUBLISHED),
    ("no  published   rating", NOT_PUBLISHED),
    ("Inspected but not rated", UNRATED),
    ("Inspected But Not Rated", UNRATED),
    ("inspected  but not rated", UNRATED),
    ("Not rated", UNRATED),
    ("Unrated", UNRATED),
    ("Not Applicable", NOT_APPLICABLE),
    ("not applicable", NOT_APPLICABLE),
    ("N/A", NOT_APPLICABLE),
]


@pytest.mark.parametrize("raw_value,expected_state", SENTINELS)
def test_every_sentinel_maps_to_a_non_rated_state_without_a_value(raw_value, expected_state):
    state, value = classify_rating(raw_value, current_ratings_present=True, historic_rating_present=False)

    assert state == expected_state
    assert state in RATING_STATES
    assert state in NON_RATED_STATES
    assert is_published_value(state) is False
    assert value is None


@pytest.mark.parametrize("raw_value,expected_state", SENTINELS)
def test_sentinel_detection_matches_the_mapping(raw_value, expected_state):
    assert is_sentinel_rating_text(raw_value) is True
    assert is_sentinel_rating_text(f"  {raw_value}  ") is True


def test_ratings_are_not_sentinels():
    assert is_sentinel_rating_text("Good") is False
    assert is_sentinel_rating_text("Requires improvement") is False
    assert is_sentinel_rating_text("") is False
    assert is_sentinel_rating_text(None) is False


# --- absent vs empty -------------------------------------------------------


@pytest.mark.parametrize("raw_value", [None, "", "   ", "\t\n"])
def test_present_ratings_block_without_a_value_is_unknown(raw_value):
    state, value = classify_rating(raw_value, current_ratings_present=True, historic_rating_present=False)

    assert state == UNKNOWN
    assert value is None


@pytest.mark.parametrize("raw_value", [None, "", "   "])
def test_no_ratings_block_is_not_published(raw_value):
    state, value = classify_rating(raw_value, current_ratings_present=False, historic_rating_present=False)

    assert state == NOT_PUBLISHED
    assert value is None


@pytest.mark.parametrize("raw_value", [None, ""])
def test_historic_only_payload_is_not_published_and_never_reports_a_value(raw_value):
    state, value = classify_rating(raw_value, current_ratings_present=False, historic_rating_present=True)

    assert state == NOT_PUBLISHED
    assert value is None


def test_historic_ratings_are_context_not_a_current_value():
    """The historic flag never turns the current field into a value."""
    # A non-empty current field is still the current field.
    assert classify_rating("Good", current_ratings_present=True, historic_rating_present=True) == (
        RATED,
        "Good",
    )
    # With no current value, a historic rating produces a state and no value.
    assert classify_rating(None, current_ratings_present=False, historic_rating_present=True) == (
        NOT_PUBLISHED,
        None,
    )


# --- contract guarantees ----------------------------------------------------


@pytest.mark.parametrize(
    "raw_value,current_present,historic_present",
    [
        (value, current, historic)
        for value in (None, "", "Good", "Not Yet Inspected", "No published rating", "Inspected but not rated")
        for current in (True, False)
        for historic in (True, False)
    ],
)
def test_classification_always_returns_a_contract_state(raw_value, current_present, historic_present):
    state, value = classify_rating(raw_value, current_present, historic_present)

    assert state in RATING_STATES
    if is_published_value(state):
        assert value not in (None, "")
    else:
        assert value is None


def test_normalisation_is_case_and_whitespace_insensitive():
    assert normalize_rating_text("Requires Improvement") == normalize_rating_text("requires  improvement")
    assert normalize_rating_text("  Good ") == "good"
    assert normalize_rating_text("") is None
    assert normalize_rating_text(None) is None


def test_sentinel_states_only_contain_states_a_sentinel_can_produce():
    assert SENTINEL_STATES.issubset(NON_RATED_STATES)
    assert RATED not in SENTINEL_STATES
    assert UNKNOWN not in SENTINEL_STATES


def test_stored_rating_is_published_guards_overwrites():
    assert stored_rating_is_published("Good") is True
    assert stored_rating_is_published("Requires improvement") is True
    assert stored_rating_is_published("Not Yet Inspected") is False
    assert stored_rating_is_published("Inspected but not rated") is False
    assert stored_rating_is_published("") is False
    assert stored_rating_is_published(None) is False


# --- payload assessment (clean_location's decision input) -------------------


def test_payload_with_current_rating_is_rated():
    rating = assess_location_rating(
        {
            "currentRatings": {"overall": {"rating": "Good", "reportDate": "2026-08-01"}},
        }
    )

    assert rating.state == RATED
    assert rating.value == "Good"
    assert rating.evidenced is True
    assert rating.report_date == "2026-08-01"
    assert rating.evidence == "cqc.currentRatings.overall.rating"


def test_payload_with_sentinel_current_rating_is_evidenced_and_valueless():
    rating = assess_location_rating({"currentRatings": {"overall": {"rating": "Not Yet Inspected"}}})

    assert rating.state == NOT_YET_INSPECTED
    assert rating.value is None
    assert rating.evidenced is True


def test_payload_without_current_ratings_is_not_published():
    rating = assess_location_rating({"locationId": "1-1", "name": "Home"})

    assert rating.state == NOT_PUBLISHED
    assert rating.value is None
    assert rating.evidenced is True
    assert rating.evidence == "cqc.currentRatings absent"


def test_payload_with_no_current_rating_but_historic_evidence_is_not_published():
    """The 2026-09 shape: currentRatings has no overall, historicRatings does."""

    rating = assess_location_rating(
        {
            "currentRatings": {"reportDate": "2026-09-10"},
            "historicRatings": [
                {"overall": {"rating": "Good"}, "reportDate": "2025-01-05"},
            ],
        }
    )

    # Source-supported state, not an evidence gap: the rating is gone, not
    # unknown, and the historic rating is evidence rather than a current value.
    assert rating.state == NOT_PUBLISHED
    assert rating.value is None
    assert rating.evidenced is True
    assert rating.historic_rating == "Good"
    assert rating.historic_rating_state == RATED
    assert rating.historic_rating_date == "2025-01-05"
    assert rating.report_date == "2026-09-10"


def test_payload_whose_historic_rating_is_a_sentinel_is_not_a_rating():
    rating = assess_location_rating(
        {
            "currentRatings": {"reportDate": "2026-09-10"},
            "historicRatings": [{"overall": {"rating": "Inspected but not rated"}}],
        }
    )

    assert rating.state == NOT_PUBLISHED
    assert rating.historic_rating == "Inspected but not rated"
    assert rating.historic_rating_state == UNRATED
    assert rating.value is None


def test_payload_with_no_current_rating_and_no_historic_evidence_is_unknown():
    rating = assess_location_rating({"currentRatings": {"reportDate": "2026-09-10"}})

    assert rating.state == UNKNOWN
    assert rating.value is None
    assert rating.evidenced is False
    assert "no historic evidence" in rating.evidence


def test_blank_rating_string_is_not_a_rating_value():
    rating = assess_location_rating({"currentRatings": {"overall": {"rating": "   "}}})

    assert rating.state == UNKNOWN
    assert rating.value is None
    assert rating.evidenced is False


def test_historic_ratings_as_a_single_dict_is_supported():
    rating = assess_location_rating(
        {
            "currentRatings": {"reportDate": "2026-09-10"},
            "historicRatings": {"overall": {"rating": "Outstanding"}, "date": "2024-04-04"},
        }
    )

    assert rating.state == NOT_PUBLISHED
    assert rating.historic_rating == "Outstanding"
    assert rating.historic_rating_date == "2024-04-04"


def test_payload_assessment_never_invents_a_rating():
    for payload in (
        {"locationId": "1-1"},
        {"currentRatings": {}},
        {"currentRatings": {"overall": {}}},
        {"currentRatings": {"overall": {"rating": "No Published Rating"}}},
        {"currentRatings": {"reportDate": "2026-09-10"}, "historicRatings": []},
    ):
        rating = assess_location_rating(payload)
        assert rating.state in RATING_STATES
        if rating.state != RATED:
            assert rating.value is None
