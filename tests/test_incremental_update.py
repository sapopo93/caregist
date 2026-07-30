from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from api.services.provider_state_events import ProviderStateEvent
from incremental_update import (
    _insert_trusted_provider_event,
    ALLOWED_COLUMNS,
    CqcActiveSnapshot,
    ChangesFetchError,
    build_snapshot_reconciliation,
    fetch_active_location_snapshot,
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


def test_active_snapshot_discovers_and_validates_official_csv():
    page = Mock(
        status_code=200,
        text='<a href="/system/files/2026-07/29_July_2026_CQC_directory.csv">CSV</a>',
        content=b"page",
    )
    csv_body = (
        "CQC Locations data,,,\n"
        "This data was produced on 29 July 2026,,,\n"
        "Name,Also known as,Address,Postcode,Phone number,Service's website (if available),Service types,Date of latest check,Specialisms/services,Provider name,Local authority,Region,Location URL,CQC Location ID (for office use only),CQC Provider ID (for office use only)\n"
        "One,,Address,AA1 1AA,,,Homecare,,,,London,London,url,1-12345,1-99999\n"
        "Two,,Address,AA1 1AB,,,Homecare,,,,London,London,url,1-12346,1-99999\n"
    ).encode()
    csv_response = Mock(status_code=200, text=csv_body.decode(), content=csv_body)

    with patch("incremental_update._request_with_retries", side_effect=[page, csv_response]):
        snapshot = fetch_active_location_snapshot(min_expected=2)

    assert snapshot.source_published_at == "2026-07-29"
    assert snapshot.source_uri == "https://www.cqc.org.uk/system/files/2026-07/29_July_2026_CQC_directory.csv"
    assert snapshot.location_ids == frozenset({"1-12345", "1-12346"})
    assert len(snapshot.checksum_sha256) == 64


def test_snapshot_reconciliation_includes_all_source_and_deactivation_candidates():
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-07-29",
        retrieved_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000", "1-10001", "1-10002"}),
    )

    with patch("incremental_update.MAX_ACTIVE_COUNT_DROP_RATIO", 0.5):
        plan = build_snapshot_reconciliation(
            snapshot,
            db_ids=frozenset({"1-10000", "1-10001", "1-99999"}),
            db_active_ids=frozenset({"1-10000", "1-10001", "1-99999"}),
        )

    assert plan["new_ids"] == frozenset({"1-10002"})
    assert plan["candidate_deactivation_ids"] == frozenset({"1-99999"})
    assert plan["detail_ids"] == frozenset({"1-10000", "1-10001", "1-10002", "1-99999"})


def test_snapshot_reconciliation_rejects_large_active_count_drop():
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-07-29",
        retrieved_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000"}),
    )

    with pytest.raises(ChangesFetchError, match="refusing reconciliation"):
        build_snapshot_reconciliation(
            snapshot,
            db_ids=frozenset({"1-10000", "1-10001"}),
            db_active_ids=frozenset({"1-10000", "1-10001"}),
        )


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


def test_trusted_event_insert_uses_source_time_and_conflict_safe_return():
    cur = Mock()
    cur.fetchone.return_value = (42,)
    event = ProviderStateEvent(
        event_type="status_changed",
        location_id="LOC1",
        provider_id="PROV1",
        effective_date=date(2026, 7, 29),
        old_value="ACTIVE",
        new_value="INACTIVE",
        dedupe_key="status_changed:LOC1:abc",
        metadata={"source_last_updated": "2026-07-29T08:00:00Z"},
    )

    assert _insert_trusted_provider_event(
        cur,
        event,
        {"last_updated": "2026-07-29T08:00:00Z"},
    )
    sql, params = cur.execute.call_args.args
    assert "ON CONFLICT (dedupe_key) DO NOTHING" in sql
    assert params[-1] == datetime(2026, 7, 29, 8, 0, tzinfo=timezone.utc)
