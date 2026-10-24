"""Territory Brief under the resolved rating contract, on the frozen audit sample.

The 30 audit fixtures (tests/fixtures/rating_audit_2026_10_22.json) are placed in
one synthetic territory so tables, narrative, evidence appendix, PDF, CSV, JSON
and rating-based group decisions can be checked against the same resolution.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zlib
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from api.services.rating_resolver import SOURCE_FILE, SOURCE_WEBSITE, RatingEvidence
from api.services.territory_brief import (
    PurchaseContext,
    brief_to_csv,
    generate_territory_opportunity_brief,
)
from api.services.territory_brief_render import render_brief_pdf

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "rating_audit_2026_10_22.json").read_text())
EDITION = date.fromisoformat(FIXTURE["file_edition_date"])
SHA = "aba66fd8ca207828a4f6325e7329d98eec3b82aee12a0bfdbceddd58da0c59cd"
CONTEXT = PurchaseContext("resolved-test", datetime(2026, 10, 24, tzinfo=timezone.utc), terms_version="test")


def _row(f):
    current = {}
    if f["api_value"]:
        current = {"overall": {"rating": f["api_value"], "reportDate": f["api_publication_date"]},
                   "reportDate": f["api_publication_date"]}
    return {
        "locationId": f["id"], "name": f["name"], "providerId": "P-" + f["id"],
        "localAuthority": "Testershire", "region": "Test Region",
        "registrationDate": f["registration_date"], "registrationStatus": "Registered", "dormancy": "N",
        "numberOfBeds": 30, "postalCode": "TE1 1ST",
        "gacServiceTypes": [{"description": "Care home service without nursing"}],
        "currentRatings": current, "historicRatings": [],
    }


def _file_ratings():
    return {
        f["id"]: RatingEvidence(
            source=SOURCE_FILE, value=f["file_value"],
            publication_date=date.fromisoformat(f["file_publication_date"]),
            inherited_flag=f["file_inherited_flag"], source_sha256=f["file_sha256"], edition_date=EDITION,
        )
        for f in FIXTURE["fixtures"] if f["file_value"]
    }


def _snapshot(tmp_path):
    loc = tmp_path / "locations.ndjson"
    prov = tmp_path / "providers.ndjson"
    loc.write_text("\n".join(json.dumps(_row(f)) for f in FIXTURE["fixtures"]) + "\n")
    prov.write_text("\n".join(json.dumps({"providerId": "P-" + f["id"], "name": f["name"] + " Ltd"})
                              for f in FIXTURE["fixtures"]) + "\n")
    return loc, prov


def _brief(tmp_path, group, *, resolved=True, website=None):
    loc, prov = _snapshot(tmp_path)
    kwargs = {"file_ratings": _file_ratings(), "website_observations": website} if resolved else {}
    with patch("api.config.settings.resolved_rating_contract_enabled", True):
        return generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire", "window_days": 90}, CONTEXT,
            locations_source=loc, providers_source=prov,
            location_ids=[f["id"] for f in FIXTURE["fixtures"]], provider_group=group, **kwargs,
        )


def _group_members(brief):
    return [o for o in brief.shortlist if any(e["event_type"] == "rating_current" for e in o.evidence)]


def _pdf_text(pdf):
    return b"\n".join(zlib.decompress(s) for s in re.findall(rb"stream\n(.*?)\nendstream", pdf, re.S))


RI_FILE = {f["id"] for f in FIXTURE["fixtures"] if f["stratum"] == "file-backed Requires improvement"}
OLDER_API_CONFLICTS = {"1-152721284", "1-390976877", "1-552527797"}


def test_flag_off_refuses_resolved_inputs(tmp_path):
    loc, prov = _snapshot(tmp_path)
    with pytest.raises(RuntimeError, match="resolved rating contract is disabled"):
        generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire"}, CONTEXT,
            locations_source=loc, providers_source=prov, file_ratings=_file_ratings(),
        )


def test_flag_defaults_off():
    from api.config import Settings

    assert Settings.model_fields["resolved_rating_contract_enabled"].default is False


def test_legacy_brief_is_unchanged_without_resolved_inputs(tmp_path):
    brief = _brief(tmp_path, "requires_improvement", resolved=False)
    assert brief.rating_resolution is None
    assert "rating_resolution" not in brief.to_json()
    assert "rating_status" not in brief_to_csv(brief).splitlines()[0]
    # API-only reader: file-backed RI ratings never reach the group.
    assert not ({o.location_id for o in brief.shortlist} & RI_FILE)


def test_ri_group_uses_resolved_current_ratings_only(tmp_path):
    brief = _brief(tmp_path, "requires_improvement")
    members = {o.location_id for o in _group_members(brief)}
    assert members == RI_FILE | OLDER_API_CONFLICTS
    # The only other shortlisted location is an in-window new registration with no rating.
    others = [o for o in brief.shortlist if o.location_id not in members]
    assert [(o.location_id, o.current_rating, o.primary_signal) for o in others] == [
        ("1-29650851551", None, "New CQC registration")
    ]
    for o in _group_members(brief):
        assert o.current_rating == "Requires improvement"
        assert o.rating_resolution["status"] == "current"
        assert o.rating_resolution["source"] == SOURCE_FILE
        assert o.rating_resolution["file_sha256"] == SHA
    excluded = {e["location_id"]: e for e in brief.rating_resolution["scope_exclusions"]}
    assert excluded["1-19886383752"]["status"] == "unresolved"
    assert excluded["1-22160036426"]["status"] == "unresolved"
    assert excluded["1-16491295796"]["status"] == "inherited"


def test_unresolved_and_inherited_are_reported_and_never_ranked(tmp_path):
    brief = _brief(tmp_path, "requires_improvement")
    res = brief.rating_resolution
    assert res["omitted_unresolved"] == ["1-19886383752", "1-22160036426"]
    assert res["inherited"] == ["1-16491295796"]
    assert res["status_counts"] == {"current": 22, "inherited": 1, "none": 5, "unresolved": 2}
    assert res["by_location"]["1-19886383752"]["value"] is None
    assert "2 location(s) with conflicting evidence are shown without a rating" in brief.data_caveats[0]


def test_inadequate_group_and_post_snapshot_observation(tmp_path):
    base = {o.location_id for o in _group_members(_brief(tmp_path, "inadequate"))}
    assert "1-125730630" in base and "1-390976877" not in base  # Althorp now RI, not Inadequate
    obs = {"1-125730630": RatingEvidence(source=SOURCE_WEBSITE, value="Requires improvement",
                                         publication_date=date(2026, 10, 13), observed_on=date(2026, 10, 22))}
    later = _brief(tmp_path, "inadequate", website=obs)
    assert "1-125730630" not in {o.location_id for o in _group_members(later)}
    chestnuts = later.rating_resolution["by_location"]["1-125730630"]
    assert chestnuts["value"] == "Requires improvement" and chestnuts["newer_than_file_edition"] is True


def test_evidence_appendix_carries_file_provenance_and_no_rating_change_events(tmp_path):
    brief = _brief(tmp_path, "requires_improvement")
    for o in _group_members(brief):
        types = {e["event_type"] for e in o.evidence}
        assert "rating_changed" not in types
        rating_ev = [e for e in o.evidence if e["event_type"] == "rating_current"]
        assert rating_ev and rating_ev[0]["source_field"] == "resolved_rating.cqc_ratings_file"
        assert SHA in rating_ev[0]["source_edition"]
        assert "source: CQC published ratings file" in rating_ev[0]["detail"]
    assert brief.territory_insights["events_by_type"].get("rating_changed") is None


def test_pdf_csv_and_json_agree_on_the_same_resolution(tmp_path):
    brief = _brief(tmp_path, "requires_improvement")
    data = brief.to_json()
    rows = list(csv.DictReader(io.StringIO(brief_to_csv(brief))))
    assert len(rows) == len(brief.shortlist)
    for row, org in zip(rows, data["shortlist"]):
        res = data["rating_resolution"]["by_location"][row["cqc_location_id"]]
        assert org["rating_resolution"] == res
        assert row["current_rating"] == (res["value"] or "")
        assert row["rating_status"] == res["status"]
        assert row["rating_source"] == (res["source"] or "")
        if res["status"] == "current":
            assert row["rating_file_sha256"] == SHA
            assert row["rating_file_edition_date"] == EDITION.isoformat()
            assert row["rating_file_inherited_flag"] == "N"
    text = _pdf_text(render_brief_pdf(brief))
    assert b"Appendix C. Rating provenance" in text
    assert SHA.encode() in text
    assert b"1-19886383752" in text  # omitted conflict is named, not silently dropped
    assert data["source_provenance"]["rating_contract"] == "resolved_current_rating_v1"
    assert data["source_provenance"]["ratings_file_editions"] == [{"edition_date": EDITION.isoformat(), "sha256": SHA}]


def test_resolved_brief_is_deterministic(tmp_path):
    a = _brief(tmp_path, "requires_improvement")
    b = _brief(tmp_path, "requires_improvement")
    assert render_brief_pdf(a) == render_brief_pdf(b)
    assert brief_to_csv(a) == brief_to_csv(b)
