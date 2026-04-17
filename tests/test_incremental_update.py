from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from incremental_update import ChangesFetchError, fetch_changes, fetch_recent_via_list_scan, resolve_since


def test_fetch_changes_raises_on_non_200_response():
    response = Mock(status_code=503)
    response.json.return_value = {}

    with patch("incremental_update.requests.get", return_value=response):
        with pytest.raises(ChangesFetchError):
            fetch_changes("https://api.service.cqc.org.uk/public/v1", "key", "2026-04-01T00:00:00", 0)


def test_fetch_changes_returns_none_on_404():
    response = Mock(status_code=404)
    with patch("incremental_update.requests.get", return_value=response):
        result = fetch_changes("https://api.service.cqc.org.uk/public/v1", "key", "2026-04-01T00:00:00", 0)
    assert result is None


def test_fetch_changes_returns_none_on_410():
    response = Mock(status_code=410)
    with patch("incremental_update.requests.get", return_value=response):
        result = fetch_changes("https://api.service.cqc.org.uk/public/v1", "key", "2026-04-01T00:00:00", 0)
    assert result is None


def test_fetch_recent_via_list_scan_returns_new_ids():
    page1 = Mock(status_code=200)
    page1.json.return_value = {
        "total": 2,
        "locations": [
            {"locationId": "LOC-NEW-1", "registrationDate": "2026-04-10"},
            {"locationId": "LOC-OLD-1", "registrationDate": "2025-01-01"},
        ],
    }
    page2 = Mock(status_code=200)
    page2.json.return_value = {"total": 2, "locations": []}

    with patch("incremental_update.requests.get", side_effect=[page1, page2]):
        result = fetch_recent_via_list_scan(
            "https://api.service.cqc.org.uk/public/v1", "key", "2026-04-01T00:00:00", 0
        )

    assert "LOC-NEW-1" in result
    assert "LOC-OLD-1" not in result


def test_resolve_since_prefers_latest_completed_incremental_run():
    cur = Mock()
    cur.fetchone.side_effect = [
        (datetime(2026, 4, 12, 9, 30, tzinfo=timezone.utc),),
    ]

    since = resolve_since(cur, None, now=datetime(2026, 4, 13, tzinfo=timezone.utc))

    assert since == "2026-04-12T09:30:00"


def test_resolve_since_falls_back_to_last_updated_then_lookback_window():
    cur = Mock()
    cur.fetchone.side_effect = [
        (None,),
        (datetime(2026, 4, 10, 8, 15, tzinfo=timezone.utc),),
    ]

    since = resolve_since(cur, None, now=datetime(2026, 4, 13, tzinfo=timezone.utc))

    assert since == "2026-04-10T08:15:00"

    cur = Mock()
    cur.fetchone.side_effect = [
        (None,),
        (None,),
    ]

    fallback_since = resolve_since(cur, None, now=datetime(2026, 4, 13, tzinfo=timezone.utc))
    assert fallback_since == "2026-04-06T00:00:00"
