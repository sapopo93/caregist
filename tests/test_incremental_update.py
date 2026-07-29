from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from incremental_update import (
    ALLOWED_COLUMNS,
    ChangesFetchError,
    fetch_changes,
    fetch_recent_via_list_scan,
    resolve_since,
    should_process_list_scan_record,
)


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


def test_fetch_recent_via_list_scan_returns_ids_missing_from_database(monkeypatch):
    """List scan diffs CQC IDs against the database baseline."""
    import incremental_update as iu

    monkeypatch.setattr(
        iu,
        "_fetch_all_cqc_location_stubs",
        lambda base_url, api_key, sleep: [
            {"locationId": "LOC-OLD-1", "locationName": "Old Provider", "postalCode": "SW1A 1AA"},
            {"locationId": "LOC-NEW-1", "locationName": "New Provider", "postalCode": "EC1A 1BB"},
        ],
    )

    result = fetch_recent_via_list_scan(
        "https://api.service.cqc.org.uk/public/v1",
        "key",
        "2026-04-01T00:00:00",
        0,
        db_known_ids=frozenset({"LOC-OLD-1"}),
    )

    assert result == ["LOC-NEW-1"]


def test_fetch_recent_via_list_scan_does_not_fetch_details(monkeypatch):
    """Registration-date filtering belongs to the main detail/upsert loop."""
    import incremental_update as iu

    monkeypatch.setattr(
        iu,
        "_fetch_all_cqc_location_stubs",
        lambda base_url, api_key, sleep: [{"locationId": "LOC-OLD-2"}],
    )
    monkeypatch.setattr(
        iu,
        "fetch_location_detail",
        Mock(side_effect=AssertionError("fallback must not fetch detail records")),
    )

    result = fetch_recent_via_list_scan(
        "https://api.service.cqc.org.uk/public/v1",
        "key",
        "2026-04-01T00:00:00",
        0,
        db_known_ids=frozenset(),
    )

    assert result == ["LOC-OLD-2"]


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


def test_should_process_list_scan_record_respects_since_watermark():
    since = "2026-04-01T00:00:00"

    assert should_process_list_scan_record(
        {"registration_date": "2026-04-02", "last_updated": None},
        since,
    )
    assert should_process_list_scan_record(
        {"registration_date": "2025-01-01", "last_updated": "2026-04-01T12:00:00"},
        since,
    )
    assert not should_process_list_scan_record(
        {"registration_date": "2025-01-01", "last_updated": "2026-03-31T23:59:59"},
        since,
    )
    assert not should_process_list_scan_record(
        {"registration_date": "2025-01-01", "last_updated": None},
        since,
    )


def test_upsert_allows_last_updated_watermark_column():
    assert "last_updated" in ALLOWED_COLUMNS


def test_completion_summary_is_not_emitted_from_finally_block():
    source = Path("incremental_update.py").read_text(encoding="utf-8")
    summary_line = next(line for line in source.splitlines() if 'print("\\nIncremental update complete:")' in line)

    assert summary_line.startswith("    print(")
