from __future__ import annotations

import json
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


def test_fetch_recent_via_list_scan_returns_new_ids(tmp_path, monkeypatch):
    """List scan fetches details for IDs not in the ETL cache and returns those >= since."""
    import incremental_update as iu

    # Patch cache path to a temp file with one known ID
    cache = tmp_path / "_locations_list.ndjson"
    cache.write_text('{"locationId": "LOC-OLD-1"}\n')
    monkeypatch.setattr(iu, "LOCATIONS_LIST_CACHE", cache)

    # CQC list returns both the old ID and a new one
    list_page = Mock(status_code=200)
    list_page.json.return_value = {
        "total": 2,
        "locations": [
            {"locationId": "LOC-OLD-1", "locationName": "Old Provider", "postalCode": "SW1A 1AA"},
            {"locationId": "LOC-NEW-1", "locationName": "New Provider", "postalCode": "EC1A 1BB"},
        ],
    }

    # Detail for the new ID has a recent registrationDate
    detail_resp = Mock(status_code=200)
    detail_resp.json.return_value = {
        "locationId": "LOC-NEW-1",
        "name": "New Provider",
        "registrationDate": "2026-04-10",
        "registrationStatus": "Registered",
    }

    with patch("incremental_update.requests.get", side_effect=[list_page, detail_resp]):
        result = fetch_recent_via_list_scan(
            "https://api.service.cqc.org.uk/public/v1", "key", "2026-04-01T00:00:00", 0
        )

    assert "LOC-NEW-1" in result
    assert "LOC-OLD-1" not in result
    # Cache should now include the new ID
    cache_ids = {json.loads(l)["locationId"] for l in cache.read_text().splitlines() if l.strip()}
    assert "LOC-NEW-1" in cache_ids


def test_fetch_recent_via_list_scan_skips_old_registrations(tmp_path, monkeypatch):
    """New CQC IDs with registrationDate before since are not returned."""
    import incremental_update as iu

    cache = tmp_path / "_locations_list.ndjson"
    cache.write_text("")  # empty cache — every ID is "new"
    monkeypatch.setattr(iu, "LOCATIONS_LIST_CACHE", cache)

    list_page = Mock(status_code=200)
    list_page.json.return_value = {
        "total": 1,
        "locations": [{"locationId": "LOC-OLD-2", "locationName": "Old Reg", "postalCode": "W1A 0AA"}],
    }
    detail_resp = Mock(status_code=200)
    detail_resp.json.return_value = {
        "locationId": "LOC-OLD-2",
        "registrationDate": "2025-06-01",  # before the since date
    }

    with patch("incremental_update.requests.get", side_effect=[list_page, detail_resp]):
        result = fetch_recent_via_list_scan(
            "https://api.service.cqc.org.uk/public/v1", "key", "2026-04-01T00:00:00", 0
        )

    assert result == []


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
