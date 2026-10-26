from tools.verify_file_ratings_against_site import NEWER_REPORT_TARGETS, implausible_none_share, parse_site_rating


def test_reads_the_overall_rating_from_the_page():
    html = '<span class="overall-rating__value--value">Requires improvement</span>'
    assert parse_site_rating(html) == "Requires improvement"


def test_a_page_with_no_rating_is_none():
    assert parse_site_rating("<html>no rating here</html>") == "none"


def test_an_unknown_value_is_none_not_guessed():
    assert parse_site_rating('<span class="overall-rating__value--value">Inspected but not rated</span>') == "none"


def test_a_run_where_most_pages_show_no_rating_is_refused_as_a_markup_change():
    assert implausible_none_share([(str(i), "none") for i in range(30)]) is not None
    mostly_rated = [(str(i), "Good") for i in range(25)] + [(str(i), "none") for i in range(5)]
    assert implausible_none_share(mostly_rated) is None
    assert implausible_none_share([("1", "none")]) is None  # too few to judge


def test_targets_are_newer_reports_and_file_api_disagreements():
    q = " ".join(NEWER_REPORT_TARGETS.split())
    assert "last_published_rating_date > coalesce(file_rating_edition_date" in q
    assert "overall_rating IS DISTINCT FROM file_overall_rating" in q
    assert "status = 'ACTIVE'" in q and "LIMIT %s" in q
