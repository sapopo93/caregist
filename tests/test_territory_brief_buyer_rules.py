"""Buyer-specific rules: objective, identifier-based exclusions, versioned scope.

Historical (rule-less) scopes must validate, generate and render exactly as before.
"""

import json
import re
import zlib
from datetime import datetime, timezone

import pytest

from api.services.territory_brief import (
    PurchaseContext,
    ScopeError,
    TerritoryScope,
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
OBJECTIVE = "Governance consultancy: find new homecare providers needing first-inspection support"


def _loc(location_id, provider_id, name, **over):
    base = {
        "locationId": location_id,
        "name": name,
        "providerId": provider_id,
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


LOCS = [
    _loc("1-100001", "1-900001", "Alpha House"),
    _loc("1-100002", "1-900002", "Beta House"),
    _loc("1-100003", "1-900002", "Beta Annex"),
    _loc("1-100004", "1-900003", "Gamma House"),
]
PROVIDERS = [
    {"providerId": "1-900001", "name": "Alpha Care Ltd"},
    {"providerId": "1-900002", "name": "Beta Care Ltd"},
    {"providerId": "1-900003", "name": "Gamma Care Ltd"},
]


def _generate(tmp_path, **scope_over):
    loc_path = tmp_path / "locations.ndjson"
    prov_path = tmp_path / "providers.ndjson"
    loc_path.write_text("\n".join(json.dumps(r) for r in LOCS) + "\n", encoding="utf-8")
    prov_path.write_text("\n".join(json.dumps(r) for r in PROVIDERS) + "\n", encoding="utf-8")
    scope = {"kind": "local_authority", "name": "Testershire", "window_days": 120}
    scope.update(scope_over)
    return generate_territory_opportunity_brief(
        scope, CONTEXT, locations_source=loc_path, providers_source=prov_path
    )


def _pdf_text(pdf):
    return b"\n".join(zlib.decompress(x) for x in re.findall(rb"stream\n(.*?)\nendstream", pdf, re.S))


def _names(brief):
    return [o.organisation_name for o in brief.shortlist]


def test_legacy_scope_is_byte_stable_and_carries_no_buyer_fields(tmp_path):
    brief = _generate(tmp_path)
    assert "buyer_objective" not in brief.scope.to_json()
    assert "rule_version" not in brief.scope.to_json()
    assert "buyer_scope" not in brief.executive_summary
    assert brief_to_csv(brief).splitlines()[0].endswith(",licence")
    assert sorted(_names(brief)) == ["Alpha Care Ltd", "Beta Care Ltd", "Gamma Care Ltd"]


def test_provider_exclusion_removes_all_its_locations_and_is_not_listed(tmp_path):
    brief = _generate(tmp_path, excluded_provider_ids=["1-900002"], buyer_objective=OBJECTIVE)
    assert sorted(_names(brief)) == ["Alpha Care Ltd", "Gamma Care Ltd"]
    assert brief.executive_summary["buyer_scope"]["excluded_with_signal"] == 2
    pdf_and_csv = _pdf_text(render_brief_pdf(brief)).decode("latin-1") + brief_to_csv(brief)
    assert "Alpha Care" in pdf_and_csv  # guards against an empty extraction
    assert "Beta Care" not in pdf_and_csv
    assert "1-900002" not in brief_to_csv(brief)


def test_location_exclusion_keeps_the_provider_if_another_location_has_a_signal(tmp_path):
    brief = _generate(tmp_path, excluded_location_ids=["1-100002"])
    beta = next(o for o in brief.shortlist if o.organisation_name == "Beta Care Ltd")
    assert beta.location_id == "1-100003"


def test_objective_and_version_reach_pdf_csv_and_json(tmp_path):
    brief = _generate(tmp_path, buyer_objective=OBJECTIVE, rule_version=2)
    assert brief.scope.to_json()["rule_version"] == 2
    csv_text = brief_to_csv(brief)
    header, first = csv_text.splitlines()[0], csv_text.splitlines()[1]
    assert header.endswith("buyer_objective,scope_rule_version")
    assert OBJECTIVE in csv_text and first.endswith(",2")
    assert any("purchasing authority" in c for c in brief.data_caveats)
    pdf = _pdf_text(render_brief_pdf(brief)).decode("latin-1")
    assert "Agreed buyer rules" in pdf and "version 2" in pdf and "first-inspection support" in pdf


def test_objective_does_not_change_ranking(tmp_path):
    plain = _generate(tmp_path)
    ruled = _generate(tmp_path, buyer_objective=OBJECTIVE)
    assert [o.location_id for o in plain.shortlist] == [o.location_id for o in ruled.shortlist]
    assert [o.score for o in plain.shortlist] == [o.score for o in ruled.shortlist]


@pytest.mark.parametrize(
    "extra",
    [
        {"excluded_provider_ids": ["Alpha Care Ltd"]},  # names are never matched
        {"excluded_provider_ids": "1-900002"},
        {"excluded_location_ids": ["1-12"]},
        {"buyer_objective": "short"},
        {"buyer_objective": "<script>alert(1)</script> to find providers"},
        {"rule_version": 0},
        {"excluded_provider_ids": [f"1-{n:09d}" for n in range(501)]},
    ],
)
def test_invalid_buyer_rules_are_rejected(extra):
    catalogue = known_territories([_loc("1-100001", "1-900001", "A")])
    raw = {"kind": "local_authority", "name": "Testershire", **extra}
    with pytest.raises(ScopeError):
        validate_scope(raw, catalogue)


def test_scope_object_round_trips_through_validation():
    catalogue = known_territories([_loc("1-100001", "1-900001", "A")])
    scope = TerritoryScope(
        kind="local_authority", name="Testershire",
        buyer_objective=OBJECTIVE, excluded_provider_ids=("1-900001",), rule_version=3,
    )
    assert validate_scope(scope, catalogue) == scope
