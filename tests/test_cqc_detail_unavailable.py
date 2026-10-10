"""Persistent directory/detail inconsistencies stay explicit and bounded."""

from types import SimpleNamespace

import pytest
import requests

import incremental_update as iu
from api.services.cqc_freshness import build_cqc_freshness
from tests.test_cqc_freshness import NOW, _run


@pytest.mark.parametrize("statuses,member,error", [
    ([404] * 5, True, iu.DetailUnavailableError),
    ([502] * 5, True, iu.ChangesFetchError),
    ([404, 502, 404, 404, 404], True, iu.ChangesFetchError),
    ([404], False, iu.ChangesFetchError),
    ([403], True, iu.ChangesFetchError),
])
def test_only_all_directory_404s_are_unavailable(monkeypatch, statuses, member, error):
    calls = []
    def get(*args, **kwargs):
        calls.append(1)
        return SimpleNamespace(status_code=statuses[len(calls) - 1], headers={})
    monkeypatch.setattr(iu.requests, "get", get)
    monkeypatch.setattr(iu.time, "sleep", lambda _: None)
    with pytest.raises(error) as raised:
        iu.fetch_location_detail(iu.DEFAULT_BASE_URL, None, "1-123456", directory_member=member)
    assert type(raised.value) is error
    assert len(calls) == len(statuses)


@pytest.mark.parametrize("bad_attempt", ["timeout", "json"])
def test_non_404_attempt_cannot_be_tolerated(monkeypatch, bad_attempt):
    calls = []
    def get(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            if bad_attempt == "timeout":
                raise requests.Timeout()
            def invalid_json():
                raise ValueError("invalid JSON")
            return SimpleNamespace(status_code=200, headers={}, json=invalid_json)
        return SimpleNamespace(status_code=404, headers={})
    monkeypatch.setattr(iu.requests, "get", get)
    monkeypatch.setattr(iu.time, "sleep", lambda _: None)
    with pytest.raises(iu.ChangesFetchError) as raised:
        iu.fetch_location_detail(iu.DEFAULT_BASE_URL, None, "1-123456", directory_member=True)
    assert type(raised.value) is iu.ChangesFetchError
    assert len(calls) == 5


def _exception_run(count=25, **state_overrides):
    state = {
        "fullCoverage": True, "detail_unavailable": count, "detailUnavailableCap": 25,
        "detailUnavailableIds": [f"1-{10000 + index}" for index in range(count)],
    }
    state.update(state_overrides)
    return _run(success_count=56742-count, failure_count=count, checkpoint_state=state)


def test_freshness_at_cap_reports_gaps_honestly():
    row = _exception_run()
    result = build_cqc_freshness(row, row, now=NOW)
    assert result["status"] == "fresh"
    assert result["successCount"] == 56717
    assert result["failureCount"] == result["detailUnavailableCount"] == 25
    assert result["detailUnavailableIds"] == row["checkpoint_state"]["detailUnavailableIds"]
    assert "persistently returned 404" in result["message"]
    assert "without collection errors" not in result["message"]


@pytest.mark.parametrize("count,state", [
    (26, {}), (1, {"fullCoverage": False}), (1, {"detail_unavailable": 0}), (1, {"detail_unavailable": 1.0}),
    (1, {"detailUnavailableIds": []}), (2, {"detailUnavailableIds": ["1-10000"] * 2}),
    (1, {"detailUnavailableIds": [None]}), (1, {"detailUnavailableIds": [""]}),
    (1, {"detailUnavailableCap": 0}), (1, {"detailUnavailableCap": 26}),
    (1, {"detailUnavailableCap": "25"}), (1, {"detailUnavailableCap": 25.5}),
])
def test_freshness_refuses_unproven_or_over_cap_exceptions(count, state):
    row = _exception_run(count, **state)
    assert build_cqc_freshness(row, row, now=NOW)["status"] == "unknown"


def test_slug_repair_excludes_unavailable_rows():
    from unittest.mock import Mock
    cur = Mock()
    cur.fetchall.side_effect = [
        [("1-10000", "Untouched", "Town"), ("1-10001", "Repaired", "Town")], [],
    ]
    iu._repair_missing_slugs(cur, ["1-10000"])
    writes = [call.args[1] for call in cur.execute.call_args_list if call.args[0].startswith("UPDATE")]
    assert len(writes) == 1
    assert writes[0][1] == "1-10001"


@pytest.mark.parametrize("override,expected", [("0", 0), ("2", 2), ("30", 30)])
def test_cap_environment_override(override, expected):
    import os
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-c", "from incremental_update import DETAIL_UNAVAILABLE_CAP; print(DETAIL_UNAVAILABLE_CAP)"],
        env={**os.environ, "CQC_DETAIL_UNAVAILABLE_CAP": override}, capture_output=True, text=True, check=True,
    )
    assert int(result.stdout.strip()) == expected


@pytest.mark.parametrize("override", ["-1", "invalid", "1.5"])
def test_invalid_cap_fails_closed(override):
    import os
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-c", "import incremental_update"],
        env={**os.environ, "CQC_DETAIL_UNAVAILABLE_CAP": override}, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "ValueError" in result.stderr


def test_noncanonical_shard_key_refuses_instead_of_overwriting_evidence():
    import uuid
    from unittest.mock import Mock
    cur = Mock()
    cur.fetchall.return_value = [("0", ["1-10000"]), ("00", ["1-10001"])]
    with pytest.raises(iu.ChangesFetchError, match="Invalid detail-unavailable"):
        iu._detail_unavailable_shards(cur, uuid.uuid4())
