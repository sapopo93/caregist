from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from api.services.provider_state_events import ProviderStateEvent
from incremental_update import (
    _fetch_all_cqc_location_stubs,
    _finalize_batch,
    _insert_trusted_provider_event,
    _ensure_no_active_reconciliation_batch,
    _prepare_batch,
    _project_rating_change,
    _resume_batch,
    _sync_reconciliation_run_evidence,
    ALLOWED_COLUMNS,
    CqcActiveSnapshot,
    ChangesFetchError,
    ShardAlreadyRunning,
    build_snapshot_manifest,
    build_snapshot_reconciliation,
    checkpoint_slices,
    fetch_active_location_snapshot,
    fetch_changes,
    fetch_location_detail,
    clean_location,
    fetch_recent_via_list_scan,
    normalize_database_url,
    partition_location_ids,
    resolve_since,
    should_process_list_scan_record,
    shard_for_location,
    validate_shard_coordinates,
)


def test_location_list_scan_retries_mid_scan_403_and_preserves_page(monkeypatch):
    import incremental_update as iu

    responses = [
        SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: {"locations": [{"locationId": "1-10000"}], "total": 2},
        ),
        SimpleNamespace(status_code=403, headers={"Retry-After": "0"}),
        SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: {"locations": [{"locationId": "1-10001"}], "total": 2},
        ),
    ]
    requested_pages: list[int] = []
    sleeps: list[float] = []

    def fake_get(*_args, **kwargs):
        requested_pages.append(kwargs["params"]["page"])
        return responses.pop(0)

    monkeypatch.setattr(iu.requests, "get", fake_get)
    monkeypatch.setattr(iu.time, "sleep", sleeps.append)

    assert _fetch_all_cqc_location_stubs(
        "https://api.service.cqc.org.uk/public/v1", "key", 0.05, min_expected=2
    ) == [
        {"locationId": "1-10000"},
        {"locationId": "1-10001"},
    ]
    assert requested_pages == [1, 2, 2]
    assert sleeps == [0.05, 0.0]


def test_location_list_scan_exhausts_bounded_403_retry_budget(monkeypatch):
    import incremental_update as iu

    attempts = 0
    sleeps: list[float] = []

    def forbidden(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        return SimpleNamespace(status_code=403, headers={"Retry-After": "0"})

    monkeypatch.setattr(iu.requests, "get", forbidden)
    monkeypatch.setattr(iu.time, "sleep", sleeps.append)

    with pytest.raises(ChangesFetchError, match=r"403 on page 1 after 5 attempts"):
        _fetch_all_cqc_location_stubs("https://api.service.cqc.org.uk/public/v1", "key", 0.0)

    assert attempts == 5
    assert sleeps == [0.0, 0.0, 0.0, 0.0]


def test_location_list_scan_does_not_retry_terminal_auth_failure(monkeypatch):
    import incremental_update as iu

    get = Mock(return_value=SimpleNamespace(status_code=401, headers={}))
    sleep = Mock()
    monkeypatch.setattr(iu.requests, "get", get)
    monkeypatch.setattr(iu.time, "sleep", sleep)

    with pytest.raises(ChangesFetchError, match=r"401 on page 1 after 1 attempts"):
        _fetch_all_cqc_location_stubs("https://api.service.cqc.org.uk/public/v1", "key", 0.0)

    get.assert_called_once()
    sleep.assert_not_called()


def test_location_list_retry_delay_supports_http_date_and_caps_delay():
    import incremental_update as iu

    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)

    assert iu._location_list_retry_delay(
        "Thu, 20 Aug 2026 12:05:00 GMT", 1, now=now
    ) == 60.0
    assert iu._location_list_retry_delay("0", 1, now=now) == 0.0
    assert iu._location_list_retry_delay("invalid", 2, now=now) == 30.0


def test_location_list_scan_rejects_premature_empty_page(monkeypatch):
    import incremental_update as iu

    responses = [
        SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: {"locations": [{"locationId": "1-10000"}], "total": 2},
        ),
        SimpleNamespace(status_code=200, headers={}, json=lambda: {"locations": [], "total": 2}),
    ]
    monkeypatch.setattr(iu.requests, "get", lambda *_args, **_kwargs: responses.pop(0))
    monkeypatch.setattr(iu.time, "sleep", lambda _seconds: None)

    with pytest.raises(ChangesFetchError, match=r"ended early on page 2 after 1/2"):
        _fetch_all_cqc_location_stubs(
            "https://api.service.cqc.org.uk/public/v1", "key", 0.0, min_expected=2
        )


def test_location_list_scan_rejects_changing_total(monkeypatch):
    import incremental_update as iu

    responses = [
        SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: {"locations": [{"locationId": "1-10000"}], "total": 2},
        ),
        SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: {"locations": [{"locationId": "1-10001"}], "total": 3},
        ),
    ]
    monkeypatch.setattr(iu.requests, "get", lambda *_args, **_kwargs: responses.pop(0))
    monkeypatch.setattr(iu.time, "sleep", lambda _seconds: None)

    with pytest.raises(ChangesFetchError, match=r"total changed from 2 to 3 on page 2"):
        _fetch_all_cqc_location_stubs(
            "https://api.service.cqc.org.uk/public/v1", "key", 0.0, min_expected=2
        )


def test_location_list_scan_rejects_duplicate_ids(monkeypatch):
    import incremental_update as iu

    response = SimpleNamespace(
        status_code=200,
        headers={},
        json=lambda: {
            "locations": [{"locationId": "1-10000"}, {"locationId": "1-10000"}],
            "total": 2,
        },
    )
    monkeypatch.setattr(iu.requests, "get", lambda *_args, **_kwargs: response)

    with pytest.raises(ChangesFetchError, match=r"duplicate IDs on page 1"):
        _fetch_all_cqc_location_stubs(
            "https://api.service.cqc.org.uk/public/v1", "key", 0.0, min_expected=2
        )


def test_normalize_database_url_rewrites_neon_pooler_hosts():
    assert normalize_database_url(
        "postgresql://user:pass@ep-example-123-pooler.eu-west-2.aws.neon.tech/db?sslmode=require"
    ) == "postgresql://user:pass@ep-example-123.eu-west-2.aws.neon.tech/db?sslmode=require"


def test_fetch_location_detail_retries_transient_status_and_honors_bounded_delay(monkeypatch):
    import incremental_update as iu

    responses = [
        SimpleNamespace(status_code=429, headers={"Retry-After": "0"}),
        SimpleNamespace(status_code=503, headers={}),
        SimpleNamespace(status_code=200, headers={}, json=lambda: {"locationId": "1-123456"}),
    ]
    sleeps: list[float] = []
    monkeypatch.setattr(iu.requests, "get", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(iu.time, "sleep", sleeps.append)

    assert fetch_location_detail("https://api.service.cqc.org.uk/public/v1", "key", "1-123456") == {
        "locationId": "1-123456"
    }
    assert sleeps == [1, 2]


def test_fetch_location_detail_preserves_sanitized_failure_evidence(monkeypatch):
    import incremental_update as iu

    response = SimpleNamespace(status_code=503, headers={})
    monkeypatch.setattr(iu.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(iu.time, "sleep", lambda _: None)

    with pytest.raises(ChangesFetchError, match=r"1-123456.*status:503"):
        fetch_location_detail("https://api.service.cqc.org.uk/public/v1", "key", "1-123456")


def test_fetch_location_detail_fails_closed_on_terminal_status(monkeypatch):
    import incremental_update as iu

    monkeypatch.setattr(
        iu.requests,
        "get",
        lambda *args, **kwargs: SimpleNamespace(status_code=404, headers={}),
    )

    with pytest.raises(ChangesFetchError, match=r"status=404"):
        fetch_location_detail("https://api.service.cqc.org.uk/public/v1", "key", "1-123456")


def test_clean_location_uses_active_directory_membership_over_lagging_detail_status():
    detail = {
        "locationId": "1-123456",
        "name": "Example Care",
        "registrationStatus": "Deregistered",
    }

    assert clean_location(detail)["status"] == "INACTIVE"
    assert clean_location(detail, directory_active=True)["status"] == "ACTIVE"
    assert normalize_database_url(
        "postgresql://user:pass@db.example.com/app"
    ) == "postgresql://user:pass@db.example.com/app"


@pytest.mark.parametrize("shard_count", [1, 2, 4, 8, 17])
def test_shard_partition_is_deterministic_exhaustive_and_disjoint(shard_count):
    location_ids = [f"1-{number:05d}" for number in range(1000, 1137)]
    first = partition_location_ids(location_ids, shard_count)
    second = partition_location_ids(list(reversed(location_ids)), shard_count)

    assert first == second
    assert sorted(item for shard in first for item in shard) == sorted(location_ids)
    assert sum(len(set(shard)) for shard in first) == len(location_ids)
    assert all(shard_for_location(item, shard_count) == index for index, shard in enumerate(first) for item in shard)


@pytest.mark.parametrize("shard_count,shard_index", [(0, None), (-1, None), (4, -1), (4, 4)])
def test_invalid_shard_coordinates_are_rejected(shard_count, shard_index):
    with pytest.raises(ValueError):
        validate_shard_coordinates(shard_count, shard_index)


def test_snapshot_manifest_is_sorted_and_deterministic():
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10002", "1-10000", "1-10001"}),
    )
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")

    first = build_snapshot_manifest(snapshot, batch_id, 4)
    second = build_snapshot_manifest(snapshot, batch_id, 4)

    assert first == second
    assert first["locationIds"] == ["1-10000", "1-10001", "1-10002"]
    assert len(first["manifestChecksumSha256"]) == 64


def test_snapshot_manifest_checksum_changes_with_shard_count():
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000", "1-10001"}),
    )
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")

    assert (
        build_snapshot_manifest(snapshot, batch_id, 4)["manifestChecksumSha256"]
        != build_snapshot_manifest(snapshot, batch_id, 8)["manifestChecksumSha256"]
    )


def test_resume_requires_failed_batch_and_consumes_one_wave(tmp_path):
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000"}),
    )
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")
    manifest = build_snapshot_manifest(snapshot, batch_id, 8)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    cursor = Mock()
    cursor.fetchone.side_effect = [
        (8, 1, manifest["manifestChecksumSha256"], manifest["sourceChecksumSha256"]),
        (
            "failed",
            42,
            {
                "resumeWaves": 0,
                "prepareExecution": {"gitSha": "a" * 40, "workflowRunId": "123"},
            },
        ),
        *[(True,) for _ in range(8)],
        (0,),
    ]
    connection = Mock()
    args = SimpleNamespace(
        batch_id=str(batch_id),
        snapshot_manifest=str(manifest_path),
        dry_run=False,
        release_sha="a" * 40,
        resume_source_run_id="123",
        workflow_run_id="456",
        workflow_run_attempt="1",
    )

    assert _resume_batch(args, connection, cursor) == 0
    connection.commit.assert_called_once()
    statements = [str(call.args[0]) for call in cursor.execute.call_args_list]
    assert any("status = 'prepared'" in statement for statement in statements)
    assert any("'{resumeWaves}'" in statement for statement in statements)


def test_resume_refuses_a_second_wave(tmp_path):
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000"}),
    )
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")
    manifest = build_snapshot_manifest(snapshot, batch_id, 8)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    cursor = Mock()
    cursor.fetchone.side_effect = [
        (8, 1, manifest["manifestChecksumSha256"], manifest["sourceChecksumSha256"]),
        (
            "failed",
            42,
            {
                "resumeWaves": 1,
                "prepareExecution": {"gitSha": "a" * 40, "workflowRunId": "123"},
            },
        ),
    ]
    args = SimpleNamespace(
        batch_id=str(batch_id),
        snapshot_manifest=str(manifest_path),
        dry_run=False,
        release_sha="a" * 40,
        resume_source_run_id="123",
    )

    with pytest.raises(ChangesFetchError, match="already used its single resume wave"):
        _resume_batch(args, Mock(), cursor)


@pytest.mark.parametrize(
    ("release_sha", "source_run_id"),
    [("b" * 40, "123"), ("a" * 40, "999")],
)
def test_resume_rejects_different_prepare_lineage(tmp_path, release_sha, source_run_id):
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000"}),
    )
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")
    manifest = build_snapshot_manifest(snapshot, batch_id, 8)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    cursor = Mock()
    cursor.fetchone.side_effect = [
        (8, 1, manifest["manifestChecksumSha256"], manifest["sourceChecksumSha256"]),
        (
            "failed",
            42,
            {
                "resumeWaves": 0,
                "prepareExecution": {"gitSha": "a" * 40, "workflowRunId": "123"},
            },
        ),
    ]
    args = SimpleNamespace(
        batch_id=str(batch_id),
        snapshot_manifest=str(manifest_path),
        dry_run=False,
        release_sha=release_sha,
        resume_source_run_id=source_run_id,
    )

    with pytest.raises(ChangesFetchError, match="original prepare code SHA"):
        _resume_batch(args, Mock(), cursor)
    assert not any(
        "UPDATE reconciliation_batches" in str(call.args[0])
        for call in cursor.execute.call_args_list
    )


def test_prepare_dry_run_performs_database_reads_without_writes(tmp_path, monkeypatch):
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000"}),
    )
    monkeypatch.setattr("incremental_update.fetch_active_location_snapshot", lambda *_args, **_kwargs: snapshot)
    cursor = Mock()
    cursor.fetchall.return_value = []
    manifest_path = tmp_path / "manifest.json"
    args = SimpleNamespace(
        batch_id="12345678-1234-5678-9234-567812345678",
        snapshot_manifest=str(manifest_path),
        shard_count=4,
        data_page_url="https://www.cqc.org.uk/data",
        dry_run=True,
    )

    assert _prepare_batch(args, Mock(), cursor) == 0
    assert not manifest_path.exists()
    assert all(str(call.args[0]).lstrip().upper().startswith("SELECT") for call in cursor.execute.call_args_list)


def test_ensure_no_active_batch_is_noop_when_idle():
    cursor = Mock()
    cursor.fetchone.return_value = None
    args = SimpleNamespace(batch_id="new-batch", dry_run=False)

    _ensure_no_active_reconciliation_batch(args, Mock(), cursor)

    assert args.batch_id == "new-batch"
    assert not any("UPDATE" in str(call.args[0]).upper() for call in cursor.execute.call_args_list if call.args)


def test_ensure_no_active_batch_aborts_idle_stale_batch_then_rechecks(monkeypatch):
    cursor = Mock()
    cursor.fetchone.side_effect = [("stale-uuid",), None]
    aborted: list[str] = []

    def fake_abort(args, _conn, _cur):
        aborted.append(args.batch_id)
        return 0

    monkeypatch.setattr("incremental_update._abort_batch", fake_abort)
    args = SimpleNamespace(batch_id="new-batch", dry_run=False)

    _ensure_no_active_reconciliation_batch(args, Mock(), cursor)

    assert aborted == ["stale-uuid"]
    assert args.batch_id == "new-batch"


def test_ensure_no_active_batch_refuses_when_a_shard_worker_is_live(monkeypatch):
    cursor = Mock()
    cursor.fetchone.return_value = ("stale-uuid",)
    monkeypatch.setattr(
        "incremental_update._abort_batch",
        Mock(side_effect=ShardAlreadyRunning("Shard 0 is still running; batch abort refused.")),
    )
    args = SimpleNamespace(batch_id="new-batch", dry_run=False)

    with pytest.raises(ChangesFetchError, match="stale-uuid is still active"):
        _ensure_no_active_reconciliation_batch(args, Mock(), cursor)
    assert args.batch_id == "new-batch"


def test_ensure_no_active_batch_refuses_if_another_batch_is_active_after_abort(monkeypatch):
    cursor = Mock()
    cursor.fetchone.side_effect = [("stale-1",), ("stale-2",)]
    monkeypatch.setattr("incremental_update._abort_batch", lambda *_args, **_kwargs: 0)
    args = SimpleNamespace(batch_id="new-batch", dry_run=False)

    with pytest.raises(ChangesFetchError, match="stale-2 is still active"):
        _ensure_no_active_reconciliation_batch(args, Mock(), cursor)
    assert args.batch_id == "new-batch"


def test_prepare_still_fail_closes_without_marking_partial_imports_complete():
    source = Path("incremental_update.py").read_text(encoding="utf-8")
    assert "_ensure_no_active_reconciliation_batch" in source
    assert "counts_reconciled = TRUE, reconciled_at = NOW()" in source
    assert "counts_reconciled = FALSE, reconciled_at = NULL" in source
    assert "A completed reconciliation batch cannot be aborted." in source


def test_reconciliation_evidence_is_derived_from_committed_shard_state():
    cursor = Mock()
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")

    _sync_reconciliation_run_evidence(cursor, batch_id)

    sql, params = cursor.execute.call_args.args
    assert "SUM(s.processed_count)" in sql
    assert "s.status = 'failed' AND s.processed_count < s.expected_count" in sql
    assert "checked_count = evidence.processed + evidence.failed" in sql
    assert "success_count = evidence.processed" in sql
    assert "failure_count = evidence.failed" in sql
    assert "'nextOffset', s.next_offset" in sql
    assert params == (str(batch_id),)


def test_reconciliation_authority_requires_atomic_full_coverage_fields():
    source = Path("incremental_update.py").read_text(encoding="utf-8")

    assert "source_total_count = %s, checked_count = %s" in source
    assert "success_count = %s, failure_count = 0" in source
    assert "counts_reconciled = TRUE, reconciled_at = NOW()" in source
    assert 'json.dumps({"fullCoverage": True, "restartable": False})' in source
    assert "counts_reconciled = FALSE, reconciled_at = NULL" in source
    assert "AND counts_reconciled = TRUE AND reconciled_at IS NOT NULL" in source
    assert "pg_try_advisory_xact_lock" in source
    assert "shard {shard_index} is still running" in source


def test_checkpoint_resume_starts_at_persisted_offset_without_overlap():
    location_ids = [f"LOC-{index}" for index in range(10)]

    checkpoints = list(checkpoint_slices(location_ids, start_offset=6, checkpoint_size=3))

    assert checkpoints == [(6, ["LOC-6", "LOC-7", "LOC-8"]), (9, ["LOC-9"])]
    assert [item for _, batch in checkpoints for item in batch] == location_ids[6:]


def test_finalizer_fails_closed_when_shard_coverage_is_incomplete(tmp_path):
    snapshot = CqcActiveSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at="2026-08-01",
        retrieved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        location_ids=frozenset({"1-10000", "1-10001"}),
    )
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")
    manifest = build_snapshot_manifest(snapshot, batch_id, 2)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    cursor = Mock()
    cursor.fetchone.return_value = (
        2,
        2,
        manifest["manifestChecksumSha256"],
        manifest["sourceChecksumSha256"],
    )
    cursor.fetchall.return_value = []
    args = SimpleNamespace(
        batch_id=str(batch_id),
        snapshot_manifest=str(manifest_path),
        dry_run=False,
    )

    with pytest.raises(ChangesFetchError, match="coverage is incomplete"):
        _finalize_batch(args, Mock(), cursor)

    assert all(str(call.args[0]).lstrip().upper().startswith("SELECT") for call in cursor.execute.call_args_list)


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


def test_rating_projection_targets_the_existing_partial_unique_index():
    cur = Mock()
    event = ProviderStateEvent(
        event_type="rating_changed",
        location_id="LOC1",
        provider_id="PROV1",
        effective_date=None,
        effective_at=None,
        effective_date_source=None,
        old_value="Good",
        new_value="Outstanding",
        dedupe_key="rating_changed:LOC1:abc",
        metadata={},
    )

    _project_rating_change(cur, event, {"name": "Provider"})

    sql = cur.execute.call_args.args[0]
    assert "ON CONFLICT (event_dedupe_key)" in sql
    assert "WHERE event_dedupe_key IS NOT NULL" in sql


def test_cli_requires_explicit_batch_phase_and_has_no_global_run_lock():
    source = Path("incremental_update.py").read_text(encoding="utf-8")

    assert 'choices=("prepare", "resume", "shard", "finalize", "abort")' in source
    assert "INCREMENTAL_UPDATE_LOCK_ID" not in source
    assert "acquire_run_lock" not in source
    assert 're.fullmatch(r"[0-9a-f]{40}", args.release_sha.lower())' in source


def test_trusted_event_insert_uses_source_time_and_conflict_safe_return():
    cur = Mock()
    cur.fetchone.return_value = (42,)
    event = ProviderStateEvent(
        event_type="status_changed",
        location_id="LOC1",
        provider_id="PROV1",
        effective_date=date(2026, 7, 29),
        effective_at=None,
        effective_date_source="cqc.registrationDate",
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
    sql, params = next(
        call.args
        for call in cur.execute.call_args_list
        if "INSERT INTO trusted_event_ledger" in call.args[0]
    )
    assert "ON CONFLICT (dedupe_key) DO NOTHING" in sql
    assert params[6] == "cqc.registrationDate"
    assert params[11] == datetime(2026, 7, 29, 8, 0, tzinfo=timezone.utc)
    assert params[14] is None
    assert ("\n" + "          observed_at,") not in sql
    assert any("INSERT INTO delivery_outbox" in call.args[0] for call in cur.execute.call_args_list)


def test_trusted_event_insert_keeps_unknown_effective_time_null():
    cur = Mock()
    cur.fetchone.return_value = None
    event = ProviderStateEvent(
        event_type="status_changed",
        location_id="LOC1",
        provider_id="PROV1",
        effective_date=None,
        effective_at=None,
        effective_date_source=None,
        old_value="ACTIVE",
        new_value="INACTIVE",
        dedupe_key="status_changed:LOC1:abc",
        metadata={"source_last_updated": "2026-07-29T08:00:00Z"},
    )

    assert not _insert_trusted_provider_event(
        cur,
        event,
        {"last_updated": "2026-07-29T08:00:00Z"},
    )
    sql, params = next(
        call.args
        for call in cur.execute.call_args_list
        if "INSERT INTO trusted_event_ledger" in call.args[0]
    )
    assert params[4:7] == (None, None, None)
    assert "ON CONFLICT (dedupe_key) DO NOTHING" in sql
