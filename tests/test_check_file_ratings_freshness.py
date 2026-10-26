from datetime import date

from tools.check_file_ratings_freshness import verdict
from tools.import_cqc_latest_ratings import edition_problem

TODAY = date(2026, 10, 23)


def test_recent_edition_is_ok():
    assert verdict(date(2026, 10, 1), 9000, 0, TODAY, 45)[0] is True


def test_old_edition_is_stale():
    ok, message = verdict(date(2026, 8, 1), 9000, 0, TODAY, 45)
    assert ok is False and "import the current file" in message


def test_age_is_measured_from_the_edition_not_the_newest_rating():
    # A file published yesterday is fresh however old its newest rating is.
    assert verdict(date(2026, 10, 22), 9000, 0, TODAY, 45)[0] is True


def test_empty_overlay_is_stale():
    assert verdict(None, 0, 0, TODAY, 45)[0] is False


def test_rating_without_a_recorded_edition_is_stale():
    ok, message = verdict(date(2026, 10, 1), 9000, 12, TODAY, 45)
    assert ok is False and "--edition-date" in message


def test_importer_requires_a_plausible_edition_date():
    assert edition_problem(None, date(2026, 9, 30), TODAY) is not None
    assert "future" in edition_problem(date(2026, 10, 24), None, TODAY)
    assert "predates" in edition_problem(date(2026, 9, 1), date(2026, 9, 30), TODAY)
    assert edition_problem(date(2026, 10, 2), date(2026, 9, 30), TODAY) is None
