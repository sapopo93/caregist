"""The pre-delivery check of a snapshot against CQC's live pages (pure parts).

Built after a Clitheroe snapshot was found, on 12 Nov 2026, to differ from CQC's
pages for 5 of 23 homes. The HTML fragments below reproduce the three shapes seen
that day: a rated location, a location with no rating of its own, and a
re-registered location that shows only a previous provider's rating.
"""

import json

import pytest

from tools.check_snapshot_against_cqc import (
    NOT_RATED,
    PageReading,
    compare,
    normalise_rating,
    parse_page,
    parse_snapshot,
    render_report,
)

RATED = '<div class="overall-rating__value--value">Good</div><p>Latest report published</p>'
UNRATED = (
    "<p>Not rated – we have not yet rated this area of the service, this is normally because "
    "the assessments we have carried out have been focused on other key questions.</p>"
)
INHERITED = (
    "<p>Registered on 2 April 2024</p><h3>Ratings inherited from last inspection with previous provider</h3>"
    "<p>These ratings were awarded to the previous provider who owned this service. "
    "(Last report published on 11 December 2020)</p>"
)


def test_a_rated_page_is_read():
    page = parse_page(RATED)
    assert page.rating == "Good" and not page.inherited


def test_a_page_with_no_rating_reads_none():
    assert parse_page(UNRATED).rating == "none"


def test_an_inherited_rating_is_not_the_locations_own():
    page = parse_page(UNRATED + INHERITED)
    assert page.rating == "none"
    assert page.inherited
    assert page.report_published == "11 December 2020"
    assert page.registered_on == "2 April 2024"


@pytest.mark.parametrize("value,expected", [("good", "Good"), (" Requires improvement ", "Requires improvement"),
                                            (None, NOT_RATED), ("", NOT_RATED), ("Not yet rated", NOT_RATED)])
def test_snapshot_ratings_are_normalised(value, expected):
    assert normalise_rating(value) == expected


def _compare(rating, page, beds=28, api_beds=28, status="Registered", api=True):
    return compare("1-1", "Home", rating, beds, page, api_beds, status, api)


def test_matching_rating_and_beds_match():
    f = _compare("Good", PageReading("Good", False, None, None))
    assert f.verdict == "match" and f.reasons == []


def test_a_rating_that_differs_from_the_page_is_a_mismatch():
    f = _compare("Not yet rated", PageReading("Outstanding", False, "20 February 2025", None))
    assert f.verdict == "mismatch"
    assert any("Outstanding" in r for r in f.reasons)


def test_a_rated_snapshot_row_for_a_home_with_only_inherited_ratings_is_a_mismatch():
    f = _compare("Good", PageReading("none", True, "11 December 2020", "2 April 2024"))
    assert f.verdict == "mismatch" and f.inherited_only
    assert any("inherited" in r for r in f.reasons)


def test_an_unrated_snapshot_row_matches_an_unrated_page():
    f = _compare("Not yet rated", PageReading("none", False, None, None))
    assert f.verdict == "match"


def test_a_changed_bed_count_is_a_mismatch():
    f = _compare("Good", PageReading("Good", False, None, None), beds=28, api_beds=30)
    assert f.verdict == "mismatch" and any("beds" in r for r in f.reasons)


def test_a_deregistered_location_is_a_mismatch():
    f = _compare("Good", PageReading("Good", False, None, None), status="Deregistered")
    assert f.verdict == "mismatch"


def test_beds_are_not_reported_as_matching_when_the_api_was_not_read():
    f = _compare("Good", PageReading("Good", False, None, None), api_beds=None, status=None, api=False)
    assert f.verdict == "match"
    assert "NOT checked" in render_report([f], "now", api_checked=False)


def test_an_unreadable_page_is_never_a_match():
    f = _compare("Good", None)
    assert f.verdict == "unreadable"


def test_snapshot_lines_and_json_parse_the_same():
    lines = parse_snapshot("# comment\n1-1|Good|28|Home A\n1-2|Not yet rated|\n1-3||40")
    assert [r["id"] for r in lines] == ["1-1", "1-2", "1-3"]
    assert lines[0]["beds"] == 28 and lines[1]["beds"] is None and lines[2]["rating"] == ""
    as_json = parse_snapshot(json.dumps([{"id": "1-1", "name": "Home A", "rating": "Good", "beds": 28}]))
    assert as_json[0] == {"id": "1-1", "name": "Home A", "rating": "Good", "beds": 28}


def test_the_workflow_is_manual_read_only_and_touches_no_database():
    import pathlib

    import yaml

    path = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "check-snapshot-against-cqc.yml"
    text = path.read_text()
    wf = yaml.safe_load(text)
    triggers = wf.get(True) or wf.get("on")  # PyYAML reads the bare key `on` as True
    assert set(triggers) == {"workflow_dispatch"}
    assert wf["permissions"] == {"contents": "read"}
    assert "DATABASE_URL" not in text
