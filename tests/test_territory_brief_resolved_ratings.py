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
    kwargs = {"rating_evidence": _file_ratings(), "website_observations": website} if resolved else {}
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
            locations_source=loc, providers_source=prov, rating_evidence=_file_ratings(),
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
    # Every shortlisted location is a group member: NEAD (unrated, registered in
    # the window) is excluded even though it has a new-registration event.
    assert {o.location_id for o in brief.shortlist} == members
    assert brief.considered_locations == len(members)
    excluded_ids = {e["location_id"] for e in brief.rating_resolution["scope_exclusions"]}
    assert "1-29650851551" in excluded_ids and not (excluded_ids & members)
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
    for row, org in zip(rows, data["shortlist"], strict=True):
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


# --------------------------------------------------------------------------- #
# Independent review 2026-10-25 (artifacts/reviews/2026-10-25-pr125-pr123)
# --------------------------------------------------------------------------- #


def _single(tmp_path, row, evidence, *, group=None, flag=True):
    loc = tmp_path / "one.ndjson"
    prov = tmp_path / "one-prov.ndjson"
    loc.write_text(json.dumps(row) + "\n")
    prov.write_text(json.dumps({"providerId": row["providerId"], "name": "P Ltd"}) + "\n")
    with patch("api.config.settings.resolved_rating_contract_enabled", flag):
        return generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire", "window_days": 90}, CONTEXT,
            locations_source=loc, providers_source=prov, provider_group=group, rating_evidence=evidence,
        )


def _conflict_row(lid="test-unresolved", **kw):
    row = {"locationId": lid, "name": "Conflict Home", "providerId": "P-" + lid,
           "localAuthority": "Testershire", "region": "", "registrationDate": "2020-01-01",
           "registrationStatus": "Registered", "dormancy": "N", "numberOfBeds": 30, "postalCode": "TE1 1ST",
           "gacServiceTypes": [{"description": "Care home service without nursing"}],
           "currentRatings": {"overall": {"rating": "Good", "reportDate": "2026-10-01"}, "reportDate": "2026-10-01"},
           "historicRatings": []}
    row.update(kw)
    return row


def _file(lid, value, day):
    return {lid: RatingEvidence(source=SOURCE_FILE, value=value, publication_date=day,
                                source_sha256=SHA, edition_date=EDITION)}


def test_review_finding_1_unresolved_in_window_rating_is_never_asserted(tmp_path):
    brief = _single(tmp_path, _conflict_row(), _file("test-unresolved", "Inadequate", date(2026, 10, 1)))
    assert brief.rating_resolution["by_location"]["test-unresolved"]["status"] == "unresolved"
    data = json.dumps(brief.to_json())
    assert "current rating Good" not in data and '"new_value": "Good"' not in data
    assert "Good" not in brief_to_csv(brief).split("\n", 1)[1]
    assert b"rating Good" not in _pdf_text(render_brief_pdf(brief))


def test_review_finding_1_superseded_api_change_is_dropped_but_history_kept(tmp_path):
    row = _conflict_row(
        currentRatings={"overall": {"rating": "Good", "reportDate": "2026-09-01"}, "reportDate": "2026-09-01"},
        historicRatings=[{"overall": {"rating": "Inadequate"}, "reportDate": "2026-08-15"},
                         {"overall": {"rating": "Requires improvement"}, "reportDate": "2026-08-01"}],
    )
    brief = _single(tmp_path, row, _file("test-unresolved", "Requires improvement", date(2026, 10, 10)))
    org = brief.shortlist[0]
    changes = [(e["old_value"], e["new_value"]) for e in org.evidence if e["event_type"] == "rating_changed"]
    assert changes == [("Requires improvement", "Inadequate")]  # dated history kept; Inadequate->Good dropped
    assert org.current_rating == "Requires improvement"


def test_review_finding_2_tuple_shape_and_empty_mapping_contract(tmp_path):
    with pytest.raises(TypeError, match="must be RatingEvidence"):
        _single(tmp_path, _conflict_row(), {"test-unresolved": ("Inadequate", date(2026, 10, 1))})
    with pytest.raises(RuntimeError, match="disabled"):
        _single(tmp_path, _conflict_row(), {}, flag=False)
    empty = _single(tmp_path, _conflict_row(), {})  # explicit opt-in with no file evidence
    assert empty.rating_resolution["by_location"]["test-unresolved"]["status"] == "current"


@pytest.mark.parametrize("lid,row_kw,evidence", [
    ("unrated", {"currentRatings": {}, "registrationDate": "2026-09-01"}, {}),
    ("conflicted", {"registrationDate": "2026-09-01"}, "conflict"),
])
def test_review_finding_5_eventful_non_members_are_excluded(tmp_path, lid, row_kw, evidence):
    if evidence == "conflict":
        evidence = _file(lid, "Inadequate", date(2026, 10, 1))
    brief = _single(tmp_path, _conflict_row(lid, **row_kw), evidence, group="requires_improvement")
    assert brief.shortlist == ()
    assert [e["location_id"] for e in brief.rating_resolution["scope_exclusions"]] == [lid]


@pytest.mark.parametrize("page_date", [None, date(2024, 1, 1)])
def test_t2_brief_membership_does_not_depend_on_page_restating_the_date(tmp_path, page_date):
    row = _conflict_row("inh", currentRatings={
        "overall": {"rating": "Requires improvement", "reportDate": "2024-01-01"}, "reportDate": "2024-01-01"})
    loc, prov = tmp_path / "l.ndjson", tmp_path / "p.ndjson"
    loc.write_text(json.dumps(row) + "\n")
    prov.write_text(json.dumps({"providerId": row["providerId"], "name": "P Ltd"}) + "\n")
    evidence = {"inh": RatingEvidence(source=SOURCE_FILE, value="Requires improvement",
                                      publication_date=date(2024, 1, 1), inherited_flag=True,
                                      source_sha256=SHA, edition_date=EDITION)}
    page = {"inh": RatingEvidence(source=SOURCE_WEBSITE, value="Requires improvement",
                                  publication_date=page_date, observed_on=date(2026, 10, 23))}
    with patch("api.config.settings.resolved_rating_contract_enabled", True):
        brief = generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire", "window_days": 90}, CONTEXT,
            locations_source=loc, providers_source=prov, location_ids=["inh"],
            provider_group="requires_improvement", rating_evidence=evidence, website_observations=page,
        )
    assert brief.shortlist == ()
    assert brief.rating_resolution["by_location"]["inh"]["status"] == "inherited"
    assert brief_to_csv(brief).count("\n") == 1



def test_g1_brief_outputs_never_assert_inherited_newer_publication_as_current(tmp_path):
    """Fifth review: file RI 2025 inherited, API RI 2024, page RI 2024 explicitly not inherited."""
    row = _conflict_row("x", currentRatings={
        "overall": {"rating": "Requires improvement", "reportDate": "2024-01-01"}, "reportDate": "2024-01-01"})
    loc, prov = tmp_path / "l.ndjson", tmp_path / "p.ndjson"
    loc.write_text(json.dumps(row) + "\n")
    prov.write_text(json.dumps({"providerId": row["providerId"], "name": "P Ltd"}) + "\n")
    evidence = {"x": RatingEvidence(source=SOURCE_FILE, value="Requires improvement",
                                    publication_date=date(2025, 1, 1), inherited_flag=True,
                                    source_sha256=SHA, edition_date=EDITION)}
    page = {"x": RatingEvidence(source=SOURCE_WEBSITE, value="Requires improvement",
                                publication_date=date(2024, 1, 1), inherited_flag=False,
                                observed_on=date(2026, 10, 23))}
    with patch("api.config.settings.resolved_rating_contract_enabled", True):
        brief = generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire", "window_days": 90}, CONTEXT,
            locations_source=loc, providers_source=prov, location_ids=["x"],
            provider_group="requires_improvement", rating_evidence=evidence, website_observations=page,
        )
    assert brief.shortlist == ()
    assert brief.rating_resolution["by_location"]["x"]["status"] == "inherited"
    assert brief_to_csv(brief).count("\n") == 1
    assert b"Currently rated Requires improvement overall" not in _pdf_text(render_brief_pdf(brief))


def test_h2_brief_never_calls_a_pre_registration_rating_current(tmp_path):
    row = _conflict_row("x", registrationDate="2025-06-01", currentRatings={
        "overall": {"rating": "Requires improvement", "reportDate": "2024-01-01"}, "reportDate": "2024-01-01"})
    loc, prov = tmp_path / "l.ndjson", tmp_path / "p.ndjson"
    loc.write_text(json.dumps(row) + "\n")
    prov.write_text(json.dumps({"providerId": row["providerId"], "name": "P Ltd"}) + "\n")
    evidence = {"x": RatingEvidence(source=SOURCE_FILE, value="Requires improvement",
                                    publication_date=date(2024, 1, 1), inherited_flag=True,
                                    source_sha256=SHA, edition_date=EDITION)}
    page = {"x": RatingEvidence(source=SOURCE_WEBSITE, value="Requires improvement",
                                publication_date=date(2024, 1, 1), inherited_flag=False,
                                observed_on=date(2026, 10, 23))}
    with patch("api.config.settings.resolved_rating_contract_enabled", True):
        brief = generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire", "window_days": 90}, CONTEXT,
            locations_source=loc, providers_source=prov, location_ids=["x"],
            provider_group="requires_improvement", rating_evidence=evidence, website_observations=page,
        )
    assert brief.shortlist == ()
    assert brief.rating_resolution["by_location"]["x"]["status"] == "inherited"
    assert brief_to_csv(brief).count("\n") == 1
    assert b"Currently rated Requires improvement overall" not in _pdf_text(render_brief_pdf(brief))


@pytest.mark.parametrize("flag", [True, False])
@pytest.mark.parametrize("page_publication", [None, date(2024, 1, 1)])
def test_j1_brief_stale_page_metadata_still_reconciles_older_publication(tmp_path, flag, page_publication):
    row = _conflict_row("x", currentRatings={
        "overall": {"rating": "Requires improvement", "reportDate": "2026-10-24"},
        "reportDate": "2026-10-24"})
    loc, prov = tmp_path / "l.ndjson", tmp_path / "p.ndjson"
    loc.write_text(json.dumps(row) + "\n")
    prov.write_text(json.dumps({"providerId": row["providerId"], "name": "P Ltd"}) + "\n")
    evidence = {"x": RatingEvidence(SOURCE_FILE, "Good", date(2024, 1, 1), inherited_flag=not flag,
                                    source_sha256=SHA, edition_date=EDITION)}
    page = {"x": RatingEvidence(SOURCE_WEBSITE, "Good", page_publication, inherited_flag=flag,
                                observed_on=date(2026, 10, 23))}
    with patch("api.config.settings.resolved_rating_contract_enabled", True):
        brief = generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire", "window_days": 90}, CONTEXT,
            locations_source=loc, providers_source=prov, location_ids=["x"],
            provider_group="requires_improvement", rating_evidence=evidence, website_observations=page,
        )
    expected = "unresolved" if flag or page_publication is None else "current"
    data = brief.to_json()
    assert data["rating_resolution"]["by_location"]["x"]["status"] == expected
    assert data["rating_resolution"]["by_location"]["x"]["website_observed_on"] == "2026-10-23"
    rows = list(csv.DictReader(io.StringIO(brief_to_csv(brief))))
    text = _pdf_text(render_brief_pdf(brief))
    if expected == "unresolved":
        assert brief.shortlist == () and rows == [] and data["shortlist"] == []
        assert b"Currently rated Requires improvement overall" not in text
        assert "Currently rated Requires improvement overall" not in json.dumps(data)
        assert b"x" in text and b"Ratings not shown because the evidence conflicts" in text
    else:
        assert [o.location_id for o in brief.shortlist] == ["x"]
        assert rows[0]["rating_status"] == "current"
        assert rows[0]["current_rating"] == "Requires improvement"
        assert b"Currently rated Requires improvement overall" in text
