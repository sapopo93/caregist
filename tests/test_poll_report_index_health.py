"""The CQC report-index source must report its own health.

An empty parse is not a quiet week unless the page says so, and a healthy
rolling sweep must never make the report index look healthy.
"""

from types import SimpleNamespace
from unittest.mock import patch

from tools import poll_cqc_signals as poll
from tools.poll_cqc_signals import classify_report_index

RESULTS = '<a href="/location/1-12345/reports">one</a><a href="/location/1-678901">two</a>'


def _ids(text):
    return {m.group("location_id") for m in poll.LOCATION_ID_PATTERN.finditer(text)}


def test_results_present_is_healthy():
    result = classify_report_index(RESULTS, _ids(RESULTS), status_code=200, content_type="text/html; charset=utf-8")
    assert result["status"] == poll.REPORT_INDEX_OK
    assert result["healthy"] is True
    assert result["uniqueIds"] == 2


def test_zero_stated_by_source_is_verified_zero():
    page = "<main><p>No results found for your search.</p></main>"
    result = classify_report_index(page, set(), status_code=200, content_type="text/html")
    assert result["status"] == poll.REPORT_INDEX_VERIFIED_ZERO
    assert result["healthy"] is True


def test_zero_without_a_stated_empty_result_is_not_healthy():
    page = "<main><div id='app'></div><script src='/bundle.js'></script></main>"
    result = classify_report_index(page, set(), status_code=200, content_type="text/html")
    assert result["status"] == poll.REPORT_INDEX_UNVERIFIED_ZERO
    assert result["healthy"] is False


def test_200_challenge_page_is_unexpected_page_not_a_quiet_week():
    page = "<html><title>Attention Required</title>Please enable JavaScript</html>"
    result = classify_report_index(page, set(), status_code=200, content_type="text/html")
    assert result["status"] == poll.REPORT_INDEX_UNEXPECTED_PAGE
    assert result["healthy"] is False


def test_challenge_page_with_stray_location_links_is_still_unexpected():
    page = RESULTS + "<p>Access denied</p>"
    result = classify_report_index(page, _ids(page), status_code=200, content_type="text/html")
    assert result["status"] == poll.REPORT_INDEX_UNEXPECTED_PAGE


def test_non_html_or_non_200_is_unexpected():
    assert classify_report_index("{}", set(), status_code=200, content_type="application/json")["status"] == poll.REPORT_INDEX_UNEXPECTED_PAGE
    assert classify_report_index(RESULTS, _ids(RESULTS), status_code=503, content_type="text/html")["status"] == poll.REPORT_INDEX_UNEXPECTED_PAGE


def test_visible_next_page_is_pagination_incomplete():
    page = RESULTS + '<a rel="next" href="/search/all?page=1">Next</a>'
    result = classify_report_index(page, _ids(page), status_code=200, content_type="text/html")
    assert result["status"] == poll.REPORT_INDEX_PAGINATION_INCOMPLETE
    assert result["healthy"] is False
    assert result["hasNextPage"] is True


def test_changed_markup_with_other_id_shape_does_not_look_healthy():
    page = '<a href="/location/2-9999999">x</a><a href="/provider/1-1234">y</a>'
    result = classify_report_index(page, _ids(page), status_code=200, content_type="text/html")
    assert result["uniqueIds"] == 0
    assert result["healthy"] is False


def test_fetch_records_health_alongside_unchanged_return_shape():
    response = SimpleNamespace(
        content=b"x",
        text="<p>No results found</p>",
        url="https://www.cqc.org.uk/search/all",
        status_code=200,
        headers={"Content-Type": "text/html"},
    )
    with patch.object(poll, "_request_with_retries", return_value=response):
        ids, content, url = poll.fetch_report_candidates()
    assert ids == set() and content == b"x" and url.endswith("/search/all")
    assert poll._LAST_REPORT_INDEX_HEALTH["status"] == poll.REPORT_INDEX_VERIFIED_ZERO
