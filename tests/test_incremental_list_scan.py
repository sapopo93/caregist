from __future__ import annotations

from pathlib import Path

import incremental_update as iu


def test_fetch_recent_via_list_scan_returns_missing_ids_without_cache_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        iu,
        "_fetch_all_cqc_location_stubs",
        lambda base_url, api_key, sleep: [
            {"locationId": "A"},
            {"locationId": "B"},
            {"locationId": "C"},
        ],
    )

    result = iu.fetch_recent_via_list_scan(
        "https://api.service.cqc.org.uk/public/v1",
        "key",
        "2026-04-15T00:00:00",
        0,
        db_known_ids=frozenset({"A"}),
    )

    assert result == ["B", "C"]
    assert not (Path.cwd() / "_locations_list.ndjson").exists()
