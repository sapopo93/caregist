from tools.verify_file_ratings_against_site import parse_site_rating


def test_reads_the_overall_rating_from_the_page():
    html = '<span class="overall-rating__value--value">Requires improvement</span>'
    assert parse_site_rating(html) == "Requires improvement"


def test_a_page_with_no_rating_is_none():
    assert parse_site_rating("<html>no rating here</html>") == "none"


def test_an_unknown_value_is_none_not_guessed():
    assert parse_site_rating('<span class="overall-rating__value--value">Inspected but not rated</span>') == "none"
