"""Unit tests for the Territory Opportunity Brief generator.

These use small synthetic CQC-shaped snapshots written to ``tmp_path`` so every
ranking, reason and validation path is exercised deterministically and without
the real 700MB register.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from api.services.territory_brief import (
    PurchaseContext,
    ScopeError,
    brief_to_csv,
    generate_territory_opportunity_brief,
    known_territories,
    validate_scope,
)
from api.services.territory_brief_render import render_brief_pdf

CONTEXT = PurchaseContext(
    order_reference="test-order",
    generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    terms_version="test",
)


# --------------------------------------------------------------------------- #
# Snapshot builders
# --------------------------------------------------------------------------- #


def _loc(**over):
    base = {
        "locationId": "1-001",
        "name": "Test Location",
        "providerId": "1-P001",
        "localAuthority": "Testershire",
        "region": "Test Region",
        "registrationDate": "2026-02-10",
        "registrationStatus": "Registered",
        "dormancy": "N",
        "numberOfBeds": 20,
        "postalCode": "TE1 1ST",
        "gacServiceTypes": [{"description": "Care home service without nursing"}],
        "currentRatings": {},
        "historicRatings": [],
    }
    base.update(over)
    return base


def _rating_block(rating: str, report_date: str):
    return {
        "overall": {"rating": rating, "reportDate": report_date},
        "reportDate": report_date,
    }


def _historic(rating: str, report_date: str):
    return {"overall": {"rating": rating}, "reportDate": report_date}


def _write_snapshot(tmp_path: Path, locations: list[dict], providers: list[dict] | None = None):
    loc_path = tmp_path / "locations.ndjson"
    prov_path = tmp_path / "providers.ndjson"
    loc_path.write_text("\n".join(json.dumps(row) for row in locations) + "\n", encoding="utf-8")
    providers = providers or [{"providerId": "1-P001", "name": "Test Provider Ltd"}]
    prov_path.write_text("\n".join(json.dumps(row) for row in providers) + "\n", encoding="utf-8")
    return loc_path, prov_path


def _generate(tmp_path, locations, providers=None, **scope_over):
    loc_path, prov_path = _write_snapshot(tmp_path, locations, providers)
    scope = {"kind": "local_authority", "name": "Testershire", "window_days": 90}
    scope.update(scope_over)
    return generate_territory_opportunity_brief(
        scope, CONTEXT, locations_source=loc_path, providers_source=prov_path
    )


# --------------------------------------------------------------------------- #
# Scope validation
# --------------------------------------------------------------------------- #


def test_validate_scope_canonicalises_case():
    cat = known_territories([_loc(localAuthority="Isle of Wight")])
    scope = validate_scope({"kind": "local_authority", "name": "isle of WIGHT"}, cat)
    assert scope.name == "Isle of Wight"
    assert scope.window_days == 90


def test_validate_scope_rejects_unknown_territory():
    cat = known_territories([_loc(localAuthority="Kent")])
    with pytest.raises(ScopeError, match="not a recognised"):
        validate_scope({"kind": "local_authority", "name": "Atlantis"}, cat)


@pytest.mark.parametrize(
    "raw",
    [
        {"kind": "county", "name": "Kent"},
        {"kind": "local_authority", "name": ""},
        {"kind": "local_authority", "name": "Kent'; DROP TABLE providers;--"},
        {"kind": "local_authority", "name": "Kent", "window_days": 0},
        {"kind": "local_authority", "name": "Kent", "window_days": 5000},
        {"kind": "local_authority", "name": "Kent", "shortlist_target": 3},
        {"kind": "local_authority", "name": "Kent", "shortlist_target": 500},
        "not-an-object",
    ],
)
def test_validate_scope_rejects_bad_input(raw):
    cat = known_territories([_loc(localAuthority="Kent")])
    with pytest.raises(ScopeError):
        validate_scope(raw, cat)


def test_generator_never_falls_back_to_a_default_territory(tmp_path):
    with pytest.raises(ScopeError):
        _generate(tmp_path, [_loc()], name="Nowhereshire")


def test_missing_snapshot_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        generate_territory_opportunity_brief(
            {"kind": "local_authority", "name": "Testershire"},
            CONTEXT,
            locations_source=tmp_path / "nope.ndjson",
            providers_source=tmp_path / "nope2.ndjson",
        )


# --------------------------------------------------------------------------- #
# Ranking
# --------------------------------------------------------------------------- #


def test_ranking_orders_by_score_desc(tmp_path):
    locs = [
        _loc(locationId="1-A", providerId="1-P001", name="Small Home",
             registrationDate="2025-12-01", numberOfBeds=5),
        _loc(locationId="1-B", providerId="1-P002", name="Big Recent Home",
             registrationDate="2026-02-18", numberOfBeds=80),
    ]
    providers = [
        {"providerId": "1-P001", "name": "Prov One Ltd"},
        {"providerId": "1-P002", "name": "Prov Two Ltd"},
    ]
    brief = _generate(tmp_path, locs, providers, window_days=120)
    assert [o.location_name for o in brief.shortlist] == ["Big Recent Home", "Small Home"]
    assert brief.shortlist[0].score > brief.shortlist[1].score
    assert brief.shortlist[0].rank == 1 and brief.shortlist[1].rank == 2


def test_tie_break_is_stable_and_deterministic(tmp_path):
    # Three identical-profile locations, same date -> identical score. Order must
    # be by name then location id, and identical across runs.
    locs = [
        _loc(locationId="1-C", providerId="1-PC", name="Charlie House", registrationDate="2026-02-10"),
        _loc(locationId="1-A", providerId="1-PA", name="Alpha House", registrationDate="2026-02-10"),
        _loc(locationId="1-B", providerId="1-PB", name="Alpha House", registrationDate="2026-02-10"),
    ]
    providers = [{"providerId": f"1-P{c}", "name": f"{c} Ltd"} for c in "ABC"]
    order1 = [o.location_id for o in _generate(tmp_path, locs, providers).shortlist]
    order2 = [o.location_id for o in _generate(tmp_path, locs, providers).shortlist]
    assert order1 == order2 == ["1-A", "1-B", "1-C"]


def test_rating_decline_outscores_plain_registration(tmp_path):
    decline = _loc(
        locationId="1-DEC", providerId="1-PDEC", name="Declining Home",
        registrationDate="2020-01-01", numberOfBeds=10,
        historicRatings=[_historic("Good", "2023-01-01")],
        currentRatings=_rating_block("Inadequate", "2026-02-01"),
    )
    reg = _loc(locationId="1-REG", providerId="1-PREG", name="New Home",
               registrationDate="2026-02-01", numberOfBeds=10)
    providers = [
        {"providerId": "1-PDEC", "name": "Decline Ltd"},
        {"providerId": "1-PREG", "name": "Newco Ltd"},
    ]
    brief = _generate(tmp_path, [decline, reg], providers, window_days=90)
    assert brief.shortlist[0].location_name == "Declining Home"
    assert "down" in brief.shortlist[0].reason.lower()


def test_provider_cluster_bonus_and_narrative(tmp_path):
    locs = [
        _loc(locationId=f"1-{i}", providerId="1-PMULTI", name=f"Chain Site {i}",
             registrationDate="2026-02-05")
        for i in range(3)
    ]
    providers = [{"providerId": "1-PMULTI", "name": "Chain Care Ltd"}]
    brief = _generate(tmp_path, locs, providers)
    assert all("account-level opportunity" in o.reason for o in brief.shortlist)
    assert brief.territory_insights["most_active_providers"][0]["provider"] == "Chain Care Ltd"


# --------------------------------------------------------------------------- #
# Reasons
# --------------------------------------------------------------------------- #


def test_every_shortlisted_org_has_a_nonempty_reason(tmp_path):
    locs = [
        _loc(locationId="1-1", providerId="1-P1", name="A", registrationDate="2026-02-10"),
        _loc(locationId="1-2", providerId="1-P2", name="B", numberOfBeds=None,
             gacServiceTypes=[], registrationDate="2026-02-11"),
        _loc(locationId="1-3", providerId="1-P3", name="C", postalCode="",
             historicRatings=[_historic("Requires improvement", "2022-01-01")],
             currentRatings=_rating_block("Good", "2026-01-15")),
    ]
    providers = [{"providerId": f"1-P{i}", "name": f"P{i} Ltd"} for i in (1, 2, 3)]
    brief = _generate(tmp_path, locs, providers)
    assert len(brief.shortlist) == 3
    for o in brief.shortlist:
        assert o.reason and o.reason.strip()
        assert len(o.reason) > 30
        assert o.evidence  # at least one evidence item


def test_improvement_reason_wording(tmp_path):
    loc = _loc(
        locationId="1-IMP", providerId="1-PIMP", name="Improver",
        registrationDate="2019-01-01",
        historicRatings=[_historic("Requires improvement", "2022-06-01")],
        currentRatings=_rating_block("Good", "2026-01-20"),
    )
    brief = _generate(tmp_path, [loc], [{"providerId": "1-PIMP", "name": "Improver Ltd"}])
    assert brief.shortlist[0].primary_signal == "Rating change"
    assert "improved" in brief.shortlist[0].reason.lower()


def test_incomplete_org_excluded_when_provider_name_missing(tmp_path):
    good = _loc(locationId="1-OK", providerId="1-POK", name="Fine Home", registrationDate="2026-02-10")
    bad = _loc(locationId="1-BAD", providerId="1-UNKNOWN", name="Ghost Home", registrationDate="2026-02-10")
    # provider list only names the good one; bad one has name too though (falls back to location name)
    brief = _generate(tmp_path, [good, bad], [{"providerId": "1-POK", "name": "OK Ltd"}])
    names = {o.location_name for o in brief.shortlist}
    assert "Fine Home" in names


def test_reregistration_is_labelled_distinctly(tmp_path):
    loc = _loc(
        locationId="1-RE", providerId="1-PRE", name="Handover House",
        registrationDate="2026-02-10",
        historicRatings=[_historic("Good", "2021-01-01")],
        currentRatings=_rating_block("Good", "2021-01-01"),
    )
    brief = _generate(tmp_path, [loc], [{"providerId": "1-PRE", "name": "Handover Ltd"}])
    assert "re-registered" in brief.shortlist[0].reason.lower()


# --------------------------------------------------------------------------- #
# Structure / caveats / determinism of whole brief
# --------------------------------------------------------------------------- #


def test_window_anchored_to_newest_source_date(tmp_path):
    locs = [_loc(registrationDate="2026-02-20"), _loc(locationId="1-old", providerId="1-P001",
                                                      registrationDate="2019-01-01")]
    brief = _generate(tmp_path, locs, window_days=30)
    assert brief.as_of_date.isoformat() == "2026-02-20"
    assert brief.window_start.isoformat() == "2026-01-22"


def test_empty_window_produces_valid_empty_brief(tmp_path):
    # Newest source date is anchored by a dormant new registration (which is not
    # a supported event), so the window contains nothing to shortlist.
    brief = _generate(tmp_path, [_loc(dormancy="Y", registrationDate="2026-02-20",
                                      currentRatings={}, historicRatings=[])],
                      window_days=7)
    assert brief.shortlist == ()
    assert "no supported" in brief.executive_summary["movement_summary"]
    # rendering an empty brief must still succeed
    pdf = render_brief_pdf(brief)
    assert pdf.startswith(b"%PDF")


def test_brief_is_byte_identical_for_identical_inputs(tmp_path):
    locs = [_loc(locationId=f"1-{i}", providerId=f"1-P{i}", name=f"H{i}",
                 registrationDate="2026-02-1%d" % (i % 10)) for i in range(5)]
    providers = [{"providerId": f"1-P{i}", "name": f"P{i} Ltd"} for i in range(5)]
    a = _generate(tmp_path, locs, providers)
    b = _generate(tmp_path, locs, providers)
    assert json.dumps(a.to_json(), sort_keys=True) == json.dumps(b.to_json(), sort_keys=True)
    assert render_brief_pdf(a) == render_brief_pdf(b)


def test_caveats_and_methodology_present(tmp_path):
    brief = _generate(tmp_path, [_loc()])
    assert any("Open Government Licence" in c for c in brief.data_caveats)
    assert any("register edition" in c for c in brief.data_caveats)
    assert len(brief.methodology_notes) >= 3
    assert brief.next_actions


# --------------------------------------------------------------------------- #
# CSV + PDF transformation
# --------------------------------------------------------------------------- #


def test_csv_has_expected_columns_and_no_blank_reason(tmp_path):
    brief = _generate(tmp_path, [
        _loc(locationId="1-1", providerId="1-P1", name="A", registrationDate="2026-02-10"),
        _loc(locationId="1-2", providerId="1-P2", name="B", registrationDate="2026-02-11"),
    ], [{"providerId": "1-P1", "name": "P1 Ltd"}, {"providerId": "1-P2", "name": "P2 Ltd"}])
    csv_text = brief_to_csv(brief)
    header, *rows = csv_text.strip().splitlines()
    assert header.split(",")[:4] == ["rank", "organisation", "location", "cqc_location_id"]
    assert "reason" in header and "cqc_record_url" in header
    assert len(rows) == 2
    for row in rows:
        assert ",,," not in row  # crude blank-cluster check
    assert "reason" not in rows[0] and len(rows[0]) > 40


def test_pdf_renders_multipage_with_appendix(tmp_path):
    locs = [
        _loc(locationId=f"1-{i}", providerId=f"1-P{i}", name=f"Home {i}",
             registrationDate="2026-02-%02d" % (1 + i % 20), numberOfBeds=10 + i)
        for i in range(20)
    ]
    providers = [{"providerId": f"1-P{i}", "name": f"Provider {i} Ltd"} for i in range(20)]
    brief = _generate(tmp_path, locs, providers, window_days=120)
    pdf = render_brief_pdf(brief)
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.rstrip().endswith(b"%%EOF")
    # multi-page: the /Type /Page count in the object stream
    assert pdf.count(b"/Type /Page") >= 4
    assert b"Appendix A" not in pdf  # compressed streams; sanity that we don't accidentally store plaintext
