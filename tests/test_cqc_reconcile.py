from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from tools.cqc_reconcile import (
    CONFIRM_PHRASE,
    CqcSnapshot,
    ReconciliationError,
    _assert_live_plan_matches_manifest,
    _assert_write_confirmation,
    _clean_and_verify_detail,
    _fetch_detail,
    build_manifest,
    build_plan,
    fetch_snapshot,
    load_manifest,
    partition_location_ids,
)


def snapshot(ids: set[str] | None = None) -> CqcSnapshot:
    return CqcSnapshot(
        source_uri="https://www.cqc.org.uk/current.csv",
        source_published_at=date(2026, 7, 29),
        source_retrieved_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
        source_checksum_sha256="a" * 64,
        location_ids=frozenset(ids or {"1-10000", "1-10001", "1-10002"}),
    )


def test_plan_separates_additions_reactivations_and_deactivations():
    plan = build_plan(
        snapshot(),
        [("1-10000", "ACTIVE"), ("1-10001", "INACTIVE"), ("1-99999", "ACTIVE")],
    )

    assert plan.counts() == {
        "sourceCount": 3,
        "currentCount": 2,
        "intersectionCount": 1,
        "additionCount": 1,
        "reactivationCount": 1,
        "deactivationCount": 1,
    }
    assert plan.addition_ids == {"1-10002"}
    assert plan.reactivation_ids == {"1-10001"}
    assert plan.deactivation_ids == {"1-99999"}


def test_manifest_is_deterministic_and_rejects_tampering(tmp_path):
    plan = build_plan(snapshot(), [("1-10000", "ACTIVE")])
    batch_id = uuid.UUID("12345678-1234-5678-9234-567812345678")
    manifest = build_manifest(snapshot(), plan, batch_id=batch_id, shard_count=4, max_deactivations=0)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    assert load_manifest(path) == manifest
    manifest["sourceCount"] = 999
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="checksum"):
        load_manifest(path)


def test_deactivation_ceiling_fails_closed():
    plan = build_plan(snapshot({"1-10000"}), [("1-99999", "ACTIVE")])
    with pytest.raises(ReconciliationError, match="above the approved ceiling"):
        build_manifest(snapshot({"1-10000"}), plan, batch_id=uuid.uuid4(), shard_count=1, max_deactivations=0)


def test_write_confirmation_requires_every_exact_value():
    plan = build_plan(snapshot(), [("1-10000", "ACTIVE")])
    manifest = build_manifest(snapshot(), plan, batch_id=uuid.uuid4(), shard_count=1, max_deactivations=0)
    args = SimpleNamespace(
        confirm_phrase=CONFIRM_PHRASE,
        confirm_source_sha256=manifest["sourceChecksumSha256"],
        confirm_source_published_at=manifest["sourcePublishedAt"],
        confirm_source_count=manifest["sourceCount"],
        confirm_current_count=manifest["currentCount"],
        confirm_intersection_count=manifest["intersectionCount"],
        confirm_addition_count=manifest["additionCount"],
        confirm_reactivation_count=manifest["reactivationCount"],
        confirm_deactivation_count=manifest["deactivationCount"],
    )
    _assert_write_confirmation(args, manifest)
    args.confirm_deactivation_count += 1
    with pytest.raises(ReconciliationError, match="confirmation mismatch"):
        _assert_write_confirmation(args, manifest)


def test_live_classification_must_still_match_the_approved_manifest():
    initial = build_plan(snapshot(), [("1-10000", "ACTIVE")])
    manifest = build_manifest(
        snapshot(), initial, batch_id=uuid.uuid4(), shard_count=1, max_deactivations=0
    )
    _assert_live_plan_matches_manifest(initial, manifest)

    drifted = build_plan(
        snapshot(), [("1-10000", "ACTIVE"), ("1-10001", "INACTIVE")]
    )
    with pytest.raises(ReconciliationError, match="changed after approval"):
        _assert_live_plan_matches_manifest(drifted, manifest)


def test_response_identity_must_equal_requested_and_cleaned_id():
    with pytest.raises(ReconciliationError, match="identity mismatch"):
        _clean_and_verify_detail(
            "1-10000",
            {"locationId": "1-10001", "name": "Wrong", "registrationStatus": "Registered"},
        )

    record = _clean_and_verify_detail(
        "1-10000",
        {"locationId": "1-10000", "name": "Right", "registrationStatus": "Registered"},
    )
    assert record["id"] == "1-10000"
    assert record["status"] == "ACTIVE"


def test_detail_fetch_does_not_forward_api_keys_through_redirects():
    redirect = Mock(status_code=302)
    with patch("tools.cqc_reconcile.requests.get", return_value=redirect) as request:
        with pytest.raises(ReconciliationError, match="Detail fetch failed"):
            _fetch_detail(
                "https://api.service.cqc.org.uk/public/v1", "secret-key", "1-10000"
            )
    assert request.call_args.kwargs["allow_redirects"] is False


def test_shards_are_deterministic_exhaustive_and_disjoint():
    ids = [f"1-{number}" for number in range(10000, 10137)]
    first = partition_location_ids(ids, 4)
    second = partition_location_ids(reversed(ids), 4)
    assert first == second
    assert sorted(item for shard in first for item in shard) == sorted(ids)
    assert len({item for shard in first for item in shard}) == len(ids)


def test_snapshot_parser_uses_official_source_and_rejects_duplicates():
    page = Mock(
        status_code=200,
        text='<a href="/system/files/current_CQC_directory.csv">CSV</a>',
        content=b"page",
        url="https://www.cqc.org.uk/about-us/transparency/using-cqc-data",
    )
    csv_body = (
        "CQC locations,,,\n"
        "This data was produced on 29 July 2026,,,\n"
        "Name,Also known as,Address,Postcode,Phone number,Service's website (if available),Service types,Date of latest check,Specialisms/services,Provider name,Local authority,Region,Location URL,CQC Location ID (for office use only),CQC Provider ID (for office use only)\n"
        "One,,Address,AA1 1AA,,,,,,,,,url,1-10000,1-90000\n"
        "Two,,Address,AA1 1AB,,,,,,,,,url,1-10001,1-90000\n"
    ).encode()
    csv_response = Mock(
        status_code=200,
        text=csv_body.decode(),
        content=csv_body,
        url="https://www.cqc.org.uk/system/files/current_CQC_directory.csv",
    )
    with patch("tools.cqc_reconcile._request_with_retries", side_effect=[page, csv_response]):
        result = fetch_snapshot(min_expected=2)
    assert result.location_ids == {"1-10000", "1-10001"}
    assert result.source_published_at == date(2026, 7, 29)


def test_workflow_has_readonly_and_protected_write_boundaries():
    workflow = Path(".github/workflows/cqc-reconciliation.yml").read_text(encoding="utf-8")
    assert "CQC_READONLY_DATABASE_URL" in workflow
    assert "CQC_PRODUCTION_DATABASE_URL" in workflow
    assert workflow.count("environment: Production") == 6
    assert "RECONCILE CQC PRODUCTION" in workflow
    assert "options: [plan, reconcile, resume, abort]" in workflow
    assert "--phase abort" in workflow
    assert "--phase shard" in workflow
    for field in (
        "confirm_source_sha256",
        "confirm_source_published_at",
        "confirm_source_count",
        "confirm_current_count",
        "confirm_intersection_count",
        "confirm_addition_count",
        "confirm_reactivation_count",
        "confirm_deactivation_count",
    ):
        assert field in workflow
        argument = field.replace("_", "-")
        assert f'--{argument} "${{{{ inputs.' not in workflow
    assert "schedule:" not in workflow
