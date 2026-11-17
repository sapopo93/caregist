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


def _response(text, url="https://www.cqc.org.uk/search/all"):
    return SimpleNamespace(text=text, content=text.encode(), url=url,
                           status_code=200, headers={"Content-Type": "text/html"})


def test_whitespace_wrapped_cqc_location_links_are_extracted():
    # Source markup observed 17 Nov 2026; the old raw regex lost these IDs.
    page = '<a href="            /location/1-13878557294\n        ">Raven House</a>'
    with patch.object(poll, "_request_with_retries", return_value=_response(page)):
        ids, _, _ = poll.fetch_report_candidates()
    assert ids == {"1-13878557294"}
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is True


def test_all_pages_are_followed_and_previous_links_do_not_make_final_page_incomplete():
    first = RESULTS + '<a rel="next" href="/search/all?page=2&amp;sort=date">Next</a>'
    final = '<a href="/location/1-55555">three</a><a rel="prev" href="?page=1">Previous</a>'
    responses = [_response(first), _response(final, "https://www.cqc.org.uk/search/all?page=2&sort=date")]
    with patch.object(poll, "_request_with_retries", side_effect=responses) as request:
        ids, content, _ = poll.fetch_report_candidates()
    assert ids == {"1-12345", "1-678901", "1-55555"}
    assert request.call_args_list[1].args[0] == "https://www.cqc.org.uk/search/all?page=2&sort=date"
    assert len(content) == sum(len(r.content) + 8 for r in responses)
    assert poll._LAST_REPORT_INDEX_HEALTH["pagesFetched"] == 2
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is True


def test_unverified_or_challenged_later_page_refuses_whole_source():
    import pytest
    first = RESULTS + '<a rel="next" href="?page=2">Next</a>'
    for final in ['<div id="app"></div>', '<p>Access denied</p>']:
        with patch.object(poll, "_request_with_retries", side_effect=[_response(first), _response(final, "https://www.cqc.org.uk/search/all?page=2")]):
            with pytest.raises(poll.ReportIndexSourceError):
                poll.fetch_report_candidates()
        assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is False


def test_pagination_limit_or_loop_refuses_source():
    import pytest
    first = RESULTS + '<a rel="next" href="?page=2">Next</a>'
    with patch.object(poll, "MAX_REPORT_INDEX_PAGES", 1), patch.object(poll, "_request_with_retries", return_value=_response(first)):
        with pytest.raises(poll.ReportIndexSourceError, match="page limit"):
            poll.fetch_report_candidates()
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is False
    with patch.object(poll, "_request_with_retries", side_effect=[_response(first), _response(first, "https://www.cqc.org.uk/search/all?page=2")]):
        with pytest.raises(poll.ReportIndexSourceError, match="repeated"):
            poll.fetch_report_candidates()
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is False


def test_external_location_and_unsafe_next_link_are_not_followed():
    import pytest
    page = RESULTS + '<a href="https://example.org/location/1-99999">external</a><a rel="next" href="https://example.org/search/all?page=2">Next</a>'
    with patch.object(poll, "_request_with_retries", return_value=_response(page)) as request:
        with pytest.raises(poll.ReportIndexSourceError, match="unsafe next"):
            poll.fetch_report_candidates()
    assert request.call_count == 1
    assert poll._LAST_REPORT_INDEX_HEALTH["uniqueIds"] == 2
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is False


def test_later_page_404_is_not_treated_as_the_end_of_results():
    import pytest
    first = RESULTS + '<a rel="next" href="?page=2">Next</a>'
    with patch.object(poll, "_request_with_retries", side_effect=[_response(first), poll.ChangesFetchError("CQC resource returned 404")]):
        with pytest.raises(poll.ReportIndexSourceError, match="page fetch failed"):
            poll.fetch_report_candidates()
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is False
    assert poll._LAST_REPORT_INDEX_HEALTH["pagesFetched"] == 1


def test_missing_next_markup_cannot_hide_a_source_result_count_shortfall():
    import pytest
    with patch.object(poll, "_request_with_retries", return_value=_response('<h1>We found\n211\nresults for All services</h1>' + RESULTS)):
        with pytest.raises(poll.ReportIndexSourceError, match="source result count"):
            poll.fetch_report_candidates()
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is False


def test_source_count_drift_refuses_inconsistent_pagination():
    import pytest
    first = '<h1>We found 3 results</h1>' + RESULTS + '<a rel="next" href="?page=2">Next</a>'
    final = '<h1>We found 4 results</h1><a href="/location/1-99999">last</a>'
    with patch.object(poll, "_request_with_retries", side_effect=[_response(first), _response(final, 'https://www.cqc.org.uk/search/all?page=2')]):
        with pytest.raises(poll.ReportIndexSourceError, match="count changed"):
            poll.fetch_report_candidates()


def test_changed_pager_without_rel_next_never_silently_completes():
    import pytest
    for href in ['?page=2', '?page=1', '?page=cursor-token']:
        page = RESULTS + f'<a href="{href}">Next</a>'
        with patch.object(poll, "_request_with_retries", return_value=_response(page)):
            with pytest.raises(poll.ReportIndexSourceError, match="no explicit next"):
                poll.fetch_report_candidates()
        assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is False


def test_terminal_page_allows_lower_numbered_navigation_without_rel():
    page = RESULTS + '<a href="?page=1">1</a>'
    with patch.object(poll, "_request_with_retries", return_value=_response(page, 'https://www.cqc.org.uk/search/all?page=2')):
        ids, _, _ = poll.fetch_report_candidates()
    assert len(ids) == 2
    assert poll._LAST_REPORT_INDEX_HEALTH["healthy"] is True
