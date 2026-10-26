"""prepare_order.build_brief in the integrated PR #125 + PR #123 tree.

Independent review 2026-10-25, finding 2: the preparation entry point must run
in both flag states with empty and populated ratings-file evidence.
Database reads are replaced by stubs; everything else is the real path.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from api.services.rating_resolver import SOURCE_FILE, SOURCE_WEBSITE, RatingEvidence
from tools import prepare_order as po

NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def _row(lid, rating=None, report=None):
    current = {"overall": {"rating": rating, "reportDate": report}, "reportDate": report} if rating else {}
    return {"locationId": lid, "providerId": f"P-{lid}", "name": f"Home {lid}", "region": "North West",
            "localAuthority": "Manchester", "registrationStatus": "Registered", "registrationDate": "2012-01-10",
            "dormancy": "N", "gacServiceTypes": [{"description": "Care home service without nursing"}],
            "currentRatings": current, "historicRatings": []}


ROWS = [
    _row("api-ri", "Requires improvement", "2026-08-01"),
    _row("stale-api", "Good", "2019-07-16"),      # file says RI 2026: resolver -> RI
    _row("file-only"),                              # file says RI 2026
    _row("checked", "Requires improvement", "2024-01-01"),  # page check says Good
]
#: What the website coverage query (API-first, file fallback) returns for
#: "Requires improvement": stale-api is absent because its API value is Good.
COVERAGE_IDS = ["api-ri", "checked", "file-only"]


def _export(tmp_path):
    d = tmp_path / "cqc-export-20261020-final"
    d.mkdir()
    (d / "_locations_detail.ndjson").write_text("\n".join(json.dumps(r) for r in ROWS) + "\n")
    (d / "_providers_detail.ndjson").write_text(
        "\n".join(json.dumps({"providerId": r["providerId"], "name": f"Provider {r['locationId']}"}) for r in ROWS) + "\n")
    (d / "RECEIPT.json").write_text(json.dumps({"source_retrieved_at": "2026-10-20T07:41:27+00:00"}))
    return d


def _args(export_dir):
    return argparse.Namespace(export_dir=export_dir, region="North West", provider_group="requires_improvement",
                              service_type=None, expected_count=None, shortlist=10, order_ref="t", stage="quote")


async def _ids(*_a):
    return COVERAGE_IDS


def _legacy(populated):
    async def fetch(*_a):
        return {"stale-api": ("Requires improvement", date(2026, 5, 20)),
                "file-only": ("Requires improvement", date(2026, 6, 1))} if populated else {}
    return fetch


def _evidence(populated):
    async def fetch(*_a):
        if not populated:
            return {}, {}
        ev = {lid: RatingEvidence(source=SOURCE_FILE, value=v, publication_date=d, source_sha256="abc")
              for lid, v, d in [("stale-api", "Requires improvement", date(2026, 5, 20)),
                                ("file-only", "Requires improvement", date(2026, 6, 1)),
                                ("checked", "Requires improvement", date(2024, 1, 1))]}
        obs = {"checked": RatingEvidence(source=SOURCE_WEBSITE, value="Good", observed_on=date(2026, 10, 23))}
        return ev, obs
    return fetch


def _run(tmp_path, *, env_flag, settings_flag, populated):
    order_dir = tmp_path / "order"
    order_dir.mkdir()
    env = {"DATABASE_URL": "postgresql://stub", "RESOLVED_RATING_CONTRACT_ENABLED": "true" if env_flag else "false"}
    with patch.object(po, "fetch_scope_location_ids", _ids), \
         patch.object(po, "fetch_file_ratings", _legacy(populated)), \
         patch.object(po, "fetch_rating_evidence", _evidence(populated)), \
         patch("api.config.settings.resolved_rating_contract_enabled", settings_flag):
        checks, summary, files = po.build_brief(_args(_export(tmp_path)), env=env, order_dir=order_dir, now=NOW)
    manifest = json.loads(next(f for f in files if f.name.endswith("source-manifest.json")).read_text())
    return checks, manifest


def _members(manifest):
    return {o["location_id"] for o in manifest["shortlist"]}


def test_flag_off_empty_keeps_api_only_behaviour(tmp_path):
    _, m = _run(tmp_path, env_flag=False, settings_flag=False, populated=False)
    assert "rating_resolution" not in m
    assert _members(m) == {"api-ri", "checked"}


def test_flag_off_populated_uses_pr123_api_else_file_fill(tmp_path):
    _, m = _run(tmp_path, env_flag=False, settings_flag=False, populated=True)
    assert "rating_resolution" not in m
    # Legacy precedence: the older API Good still wins for stale-api (disclosed gap).
    assert _members(m) == {"api-ri", "checked", "file-only"}


def test_flag_on_empty_evidence_resolves_from_api_alone(tmp_path):
    checks, m = _run(tmp_path, env_flag=True, settings_flag=True, populated=False)
    assert m["rating_resolution"]["status_counts"] == {"current": 2, "none": 1}
    assert _members(m) == {"api-ri", "checked"}


def test_flag_on_populated_uses_resolved_contract(tmp_path):
    _, m = _run(tmp_path, env_flag=True, settings_flag=True, populated=True)
    res = m["rating_resolution"]["by_location"]
    assert res["file-only"]["value"] == "Requires improvement" and res["file-only"]["source"] == SOURCE_FILE
    assert res["checked"]["value"] == "Good" and res["checked"]["source"] == SOURCE_WEBSITE
    assert _members(m) == {"api-ri", "file-only"}
    assert {e["location_id"] for e in m["rating_resolution"]["scope_exclusions"]} == {"checked"}
    # Disclosed gap: the resolver can only narrow the coverage query's scope.
    # stale-api (API Good 2019, file RI 2026) is never offered to the Brief.
    assert "stale-api" not in res


def test_env_on_but_settings_off_fails_closed(tmp_path):
    with pytest.raises(RuntimeError, match="disabled"):
        _run(tmp_path, env_flag=True, settings_flag=False, populated=True)


# --------------------------------------------------------------------------- #
# Repeat review 2026-10-25 (PR #127): N1 and N2 through the real loader.
# Only the asyncpg connection and the coverage lookup are stubbed.
# --------------------------------------------------------------------------- #


class _Txn:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Conn:
    def __init__(self, rows):
        self.rows = rows

    def transaction(self, readonly=False):
        assert readonly
        return _Txn()

    async def fetch(self, _sql, ids):
        return [r for r in self.rows if r["id"] in ids]

    async def close(self):
        pass


def _db_row(site_check=None):
    return {"id": "x", "file_overall_rating": "Requires improvement",
            "file_overall_rating_date": date(2024, 1, 1), "file_rating_source_sha256": "abc",
            "site_check_rating": site_check,
            "site_check_at": datetime(2026, 10, 23, tzinfo=timezone.utc) if site_check else None}


def _run_real_loader(tmp_path, site_check, *, api_report="2024-01-01"):
    import asyncpg

    rows = [_row("x", "Requires improvement", api_report),
            {**_row("later"), "registrationDate": "2026-10-20"}]  # realistic newest date, out of scope
    d = tmp_path / "cqc-export-20261020-final"
    d.mkdir()
    (d / "_locations_detail.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (d / "_providers_detail.ndjson").write_text(
        "\n".join(json.dumps({"providerId": r["providerId"], "name": f"Provider {r['locationId']}"}) for r in rows) + "\n")
    (d / "RECEIPT.json").write_text(json.dumps({"source_retrieved_at": "2026-10-24T07:41:27+00:00"}))
    order_dir = tmp_path / "order"
    order_dir.mkdir()

    async def connect(*_a, **_k):
        return _Conn([_db_row(site_check)])

    async def ids(*_a):
        return ["x"]

    env = {"DATABASE_URL": "postgresql://stub", "RESOLVED_RATING_CONTRACT_ENABLED": "true"}
    with patch.object(asyncpg, "connect", connect), patch.object(po, "fetch_scope_location_ids", ids), \
         patch("api.config.settings.resolved_rating_contract_enabled", True):
        _, _, files = po.build_brief(_args(d), env=env, order_dir=order_dir, now=NOW)
    return json.loads(next(f for f in files if f.name.endswith("source-manifest.json")).read_text())


def test_n1_agreeing_page_check_keeps_membership_and_publication_date(tmp_path):
    for check, sub in ((None, "plain"), ("Requires improvement", "checked")):
        (tmp_path / sub).mkdir()
        m = _run_real_loader(tmp_path / sub, check)
        assert _members(m) == {"x"}
        res = m["rating_resolution"]["by_location"]["x"]
        assert (res["status"], res["publication_date"]) == ("current", "2024-01-01")
        assert res["website_observed_on"] == ("2026-10-23" if check else None)


def test_n2_none_page_check_is_kept_and_withholds_the_rating(tmp_path):
    m = _run_real_loader(tmp_path, "none")
    res = m["rating_resolution"]["by_location"]["x"]
    assert res["status"] == "unresolved" and res["value"] is None
    assert (res["website_raw_value"], res["website_observed_on"]) == ("none", "2026-10-23")
    assert res["file_value"] == "Requires improvement"  # file evidence retained
    assert "agree" not in res["reason"]
    assert _members(m) == set()
    assert [e["location_id"] for e in m["rating_resolution"]["scope_exclusions"]] == ["x"]


def test_n2_rating_published_after_none_check_is_current(tmp_path):
    m = _run_real_loader(tmp_path, "none", api_report="2026-10-24")
    res = m["rating_resolution"]["by_location"]["x"]
    assert (res["status"], res["source"], res["publication_date"]) == ("current", "cqc_api", "2026-10-24")
    assert res["website_raw_value"] == "none"
