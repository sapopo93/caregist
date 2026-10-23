from datetime import date

from tools.check_file_ratings_freshness import verdict


def test_recent_file_is_ok():
    assert verdict(date(2026, 10, 1), date(2026, 10, 23), 45)[0] is True


def test_old_file_is_stale():
    ok, message = verdict(date(2026, 8, 1), date(2026, 10, 23), 45)
    assert ok is False and "import the current file" in message


def test_empty_overlay_is_stale():
    assert verdict(None, date(2026, 10, 23), 45)[0] is False
