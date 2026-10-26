"""Unit tests for the buyer-specific pilot layer over the Territory Brief."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from api.services.territory_brief import (
    MAX_SHORTLIST,
    PurchaseContext,
    ScopeError,
    generate_territory_opportunity_brief,
)
from api.services.territory_brief_pilot import (
    CRM_COLUMNS,
    BuyerProfile,
    Suppression,
    build_pilot_brief,
    load_crm_suppression,
    normalise_org_name,
    pilot_to_crm_csv,
    pilot_to_csv,
    pilot_to_review_markdown,
    provider_group_sizes,
    provider_registrations_in_window,
    validate_profile,
)

CONTEXT = PurchaseContext(
    order_reference="test-order",
    generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    terms_version="test",
)


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


def _snapshot(tmp_path: Path):
    """Twelve providers with one in-territory registration each, varied group sizes."""
    locations, providers = [], []
    for i in range(1, 13):
        pid = f"1-P{i:03d}"
        providers.append({"providerId": pid, "name": f"Provider {i} Ltd"})
        locations.append(
            _loc(
                locationId=f"1-L{i:03d}",
                providerId=pid,
                name=f"Home {i}",
                registrationDate=f"2026-02-{i + 10:02d}",
                numberOfBeds=10 * i,
                gacServiceTypes=[
                    {"description": "Domiciliary care service" if i % 4 == 0 else "Care home service without nursing"}
                ],
            )
        )
        # Extra locations elsewhere: provider i has i registered locations in total.
        for extra in range(1, i):
            locations.append(
                _loc(
                    locationId=f"1-L{i:03d}-{extra}",
                    providerId=pid,
                    name=f"Home {i}.{extra}",
                    localAuthority="Elsewhere",
                    registrationDate="2020-01-01",
                )
            )
    # Deregistered locations must not count towards group size.
    locations.append(
        _loc(locationId="1-DEREG", providerId="1-P001", localAuthority="Elsewhere",
             registrationStatus="Deregistered", registrationDate="2019-01-01")
    )
    loc_path = tmp_path / "locations.ndjson"
    prov_path = tmp_path / "providers.ndjson"
    loc_path.write_text("\n".join(json.dumps(r) for r in locations) + "\n", encoding="utf-8")
    prov_path.write_text("\n".join(json.dumps(r) for r in providers) + "\n", encoding="utf-8")
    return loc_path, prov_path, locations


def _base(tmp_path):
    loc_path, prov_path, rows = _snapshot(tmp_path)
    brief = generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": "Testershire", "shortlist_target": MAX_SHORTLIST},
        CONTEXT,
        locations_source=loc_path,
        providers_source=prov_path,
    )
    return brief, loc_path, rows


def _pilot(tmp_path, suppression=None, **profile):
    brief, loc_path, _ = _base(tmp_path)
    profile.setdefault("pilot_target", 10)
    return build_pilot_brief(
        brief, BuyerProfile(**profile), locations_source=loc_path, suppression=suppression
    )


def test_group_size_counts_registered_locations_across_territories(tmp_path):
    _, _, rows = _snapshot(tmp_path)
    sizes = provider_group_sizes(rows)
    assert sizes["1-P001"] == 1  # the deregistered location is ignored
    assert sizes["1-P007"] == 7


def test_registrations_in_window_ignore_old_and_dormant(tmp_path):
    rows = [
        _loc(locationId="a", registrationDate="2026-02-10"),
        _loc(locationId="b", registrationDate="2020-01-01"),
        _loc(locationId="c", registrationDate="2026-02-11", dormancy="Y"),
    ]
    counts = provider_registrations_in_window(
        rows, window_start=date(2026, 1, 1), window_end=date(2026, 3, 1)
    )
    assert counts["1-P001"] == 1


def test_filters_count_each_exclusion(tmp_path):
    pilot = _pilot(
        tmp_path,
        group_size_min=2,
        group_size_max=10,
        beds_max=90,
        exclude_service_types=("Domiciliary care service",),
        exclude_provider_ids=("1-P002",),
    )
    kept = {a.organisation.provider_id for a in pilot.accounts}
    # P002 excluded by id; P004/P008/P012 domiciliary; P001 (1) and P011 (11) outside the
    # group range; P010 (100 beds) outside the bed range.
    assert kept == {"1-P003", "1-P005", "1-P006", "1-P007", "1-P009"}
    assert pilot.exclusions == {
        "excluded_provider": 1,
        "crm_existing": 0,
        "service_type": 3,
        "group_size": 2,
        "beds": 1,
    }
    assert sum(pilot.exclusions.values()) + len(pilot.accounts) == pilot.pool_size


def test_rank_order_preserved_and_renumbered(tmp_path):
    pilot = _pilot(tmp_path, exclude_provider_ids=("1-P001",))
    base_ranks = [a.base_rank for a in pilot.accounts]
    assert base_ranks == sorted(base_ranks)
    assert [a.rank for a in pilot.accounts] == list(range(1, len(pilot.accounts) + 1))


def test_shortfall_disclosed_without_padding(tmp_path):
    pilot = _pilot(tmp_path, group_size_min=10, pilot_target=20)
    assert len(pilot.accounts) == 3
    assert pilot.shortfall_notice and "3 of the 12" in pilot.shortfall_notice
    assert "fewer than the requested 20" in pilot.shortfall_notice


def test_crm_suppression_matches_ids_and_exact_names_only(tmp_path):
    path = tmp_path / "crm.csv"
    path.write_text(
        "Organisation,CQC_Provider_ID,cqc_location_id,Contact Email,Contact Name\n"
        "PROVIDER 3 LIMITED,,,jane@example.com,Jane Doe\n"
        ",1-P005,,bob@example.com,Bob\n"
        ",,1-L007,,\n"
        "Provider 9 Care,,,,\n",
        encoding="utf-8",
    )
    suppression = load_crm_suppression(path)
    pilot = _pilot(tmp_path, suppression=suppression)
    kept = {a.organisation.provider_id for a in pilot.accounts}
    assert not kept & {"1-P003", "1-P005", "1-P007"}
    assert "1-P009" in kept  # near-miss name is not suppressed
    assert pilot.exclusions["crm_existing"] == 3

    outputs = (
        pilot_to_csv(pilot) + pilot_to_crm_csv(pilot) + pilot_to_review_markdown(pilot)
        + json.dumps(pilot.to_json())
    )
    for leaked in ("jane@example.com", "Jane Doe", "bob@example.com"):
        assert leaked not in outputs


def test_crm_suppression_requires_a_known_column(tmp_path):
    path = tmp_path / "crm.csv"
    path.write_text("Email\nx@example.com\n", encoding="utf-8")
    with pytest.raises(ScopeError):
        load_crm_suppression(path)


def test_name_normalisation():
    assert normalise_org_name("  Acme  Care LIMITED ") == normalise_org_name("acme care ltd")
    assert normalise_org_name("Acme Care") != normalise_org_name("Acme Care Group")


def test_qualification_never_claims_what_cqc_cannot_show(tmp_path):
    pilot = _pilot(tmp_path)
    assert pilot.accounts
    for account in pilot.accounts:
        factors = {f.name: f for f in account.qualification}
        for name in ("Existing care-records system", "Buying intent"):
            assert factors[name].status == "Unknown"
        for name in ("Procurement activity", "Decision-maker role"):
            assert factors[name].status == "Not researched"
        for factor in account.qualification:
            if factor.status in ("Verified", "Not met"):
                assert factor.source.startswith("CQC register: location.")
        assert factors["Recent registration"].status == "Verified"
        assert "nationally" in factors["Group size"].finding


def test_missing_beds_and_service_types_are_unknown(tmp_path):
    loc_path = tmp_path / "locations.ndjson"
    prov_path = tmp_path / "providers.ndjson"
    loc_path.write_text(json.dumps(_loc(numberOfBeds=None, gacServiceTypes=[])) + "\n", encoding="utf-8")
    prov_path.write_text(json.dumps({"providerId": "1-P001", "name": "P Ltd"}) + "\n", encoding="utf-8")
    brief = generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": "Testershire"}, CONTEXT,
        locations_source=loc_path, providers_source=prov_path,
    )
    pilot = build_pilot_brief(brief, BuyerProfile(pilot_target=10), locations_source=loc_path)
    factors = {f.name: f for f in pilot.accounts[0].qualification}
    assert factors["Bed count"].status == "Unknown"
    assert factors["Service-type fit"].status == "Unknown"


def test_bed_bounds_exclude_unknown_beds_only_when_bounded(tmp_path):
    loc_path = tmp_path / "locations.ndjson"
    prov_path = tmp_path / "providers.ndjson"
    loc_path.write_text(json.dumps(_loc(numberOfBeds=None)) + "\n", encoding="utf-8")
    prov_path.write_text(json.dumps({"providerId": "1-P001", "name": "P Ltd"}) + "\n", encoding="utf-8")
    brief = generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": "Testershire"}, CONTEXT,
        locations_source=loc_path, providers_source=prov_path,
    )
    assert len(build_pilot_brief(brief, BuyerProfile(), locations_source=loc_path).accounts) == 1
    bounded = build_pilot_brief(brief, BuyerProfile(beds_min=5), locations_source=loc_path)
    assert not bounded.accounts and bounded.exclusions["beds"] == 1


def test_crm_csv_headers_and_one_row_per_provider(tmp_path):
    pilot = _pilot(tmp_path)
    rows = list(csv.reader(io.StringIO(pilot_to_crm_csv(pilot))))
    assert tuple(rows[0]) == CRM_COLUMNS
    external_ids = [row[1] for row in rows[1:]]
    assert len(external_ids) == len(set(external_ids)) == len(pilot.accounts)


def test_qualification_csv_has_status_per_factor(tmp_path):
    pilot = _pilot(tmp_path)
    reader = csv.DictReader(io.StringIO(pilot_to_csv(pilot)))
    first = next(reader)
    assert first["buying_intent_status"] == "Unknown"
    assert first["cqc_record_url"].startswith("https://www.cqc.org.uk/location/")


def test_review_markdown_has_a_checkbox_per_evidence_event(tmp_path):
    pilot = _pilot(tmp_path)
    md = pilot_to_review_markdown(pilot)
    events = sum(len(a.organisation.evidence) for a in pilot.accounts)
    assert md.count("- [ ] ") >= events + 2 * len(pilot.accounts)
    assert "## Limitations" in md


@pytest.mark.parametrize(
    "profile",
    [
        BuyerProfile(pilot_target=5),
        BuyerProfile(pilot_target=31),
        BuyerProfile(group_size_min=10, group_size_max=5),
        BuyerProfile(beds_min=-1),
        BuyerProfile(include_service_types=("X",), exclude_service_types=("x",)),
        BuyerProfile(segment="recruitment"),  # type: ignore[arg-type]
    ],
)
def test_validate_profile_rejects_bad_input(profile):
    with pytest.raises(ScopeError):
        validate_profile(profile)


def test_no_shortfall_notice_when_target_met(tmp_path):
    assert _pilot(tmp_path).shortfall_notice is None


def test_suppression_default_matches_nothing(tmp_path):
    pilot = _pilot(tmp_path, suppression=Suppression())
    assert pilot.exclusions["crm_existing"] == 0
