from datetime import date

from tools.rating_accuracy_sample import (
    ALLOCATION,
    _export_facts,
    assign_stratum,
    compare,
    select_sample,
)
from tools.report_sources import FileRating


def _db(**kw):
    base = {
        "id": "1-1", "name": "X", "status": "ACTIVE", "registration_date": date(2015, 1, 1),
        "overall_rating": None, "last_published_rating_date": None,
        "file_overall_rating": None, "file_overall_rating_date": None,
        "file_rating_source_sha256": None, "updated_at": None,
    }
    base.update(kw)
    return base


def _row(**kw):
    base = {"locationId": "1-1", "registrationStatus": "Registered", "registrationDate": "2015-01-01",
            "dormancy": "N", "relationships": []}
    base.update(kw)
    return base


def _rated(rating, report_date, historic=()):
    return {
        "currentRatings": {"overall": {"rating": rating}, "reportDate": report_date},
        "historicRatings": [{"reportDate": d, "overall": {"rating": r}} for d, r in historic],
    }


def test_conflict_ids_are_always_their_own_stratum():
    assert assign_stratum(_db(id="1-152721284"), None, None) == "conflict_2026_10_22"


def test_strata_priority_order():
    dereg = _export_facts(_row(registrationStatus="Deregistered", deregistrationDate="2026-10-13"))
    assert assign_stratum(_db(), dereg, None) == "deregistration"
    down = _export_facts(_row(**_rated("Requires improvement", "2026-01-01", [("2022-01-01", "Good")])))
    assert assign_stratum(_db(overall_rating="Requires improvement"), down, None) == "downgrade"
    rereg = _export_facts(_row(relationships=[{"type": "HSCA Predecessor", "relatedLocationId": "1-0"}]))
    assert assign_stratum(_db(), rereg, None) == "re_registration"
    plain = _export_facts(_row())
    assert assign_stratum(_db(file_overall_rating="Good"), plain, None) == "file_only"
    assert assign_stratum(_db(), plain, None) == "unrated"
    assert assign_stratum(_db(overall_rating="Good"), _export_facts(_row(**_rated("Good", "2025-01-01"))), None) is None


def test_sentinel_history_is_not_a_downgrade():
    facts = _export_facts(_row(**_rated("Good", "2026-01-01", [("2022-01-01", "Inspected but not rated")])))
    assert facts["downgrade"] is False


def test_selection_is_seeded_and_capped():
    pools = {"conflict_2026_10_22": ["b", "a"], "unrated": [f"1-{i}" for i in range(50)]}
    one = select_sample(pools, "seed")
    assert one == select_sample(pools, "seed")
    assert one["conflict_2026_10_22"] == ["a", "b"]
    assert len(one["unrated"]) == ALLOCATION["unrated"]
    assert one["unrated"] != select_sample(pools, "other")["unrated"]


def test_compare_flags_unreconciled_deregistration():
    exp = _export_facts(_row(registrationStatus="Deregistered", deregistrationDate="2026-10-13"))
    out = compare(_db(), exp, None, set(), date(2026, 10, 2))
    assert out["status_match"] is False
    assert "status_deregistration_unreconciled" in out["root_cause_codes"]
    quarantined = compare(_db(), exp, None, {"1-1"}, date(2026, 10, 2))
    assert "status_quarantined" in quarantined["root_cause_codes"]


def test_compare_flags_precedence_defect_and_resolves_to_newer_file():
    db = _db(overall_rating="Good", last_published_rating_date=date(2019, 7, 16),
             file_overall_rating="Requires improvement", file_overall_rating_date=date(2026, 5, 20))
    exp = _export_facts(_row(**_rated("Good", "2019-07-16")))
    file_r = FileRating("Requires improvement", date(2026, 5, 20), False)
    out = compare(db, exp, file_r, set(), date(2026, 10, 2))
    assert out["rating_match"] is True  # stored API value mirrors the API
    codes = out["root_cause_codes"].split()
    assert "precedence_api_over_newer_file" in codes
    assert "served_differs_from_resolved" in codes
    assert out["cqc_resolved_rating"] == "Requires improvement"


def test_compare_clean_row_has_no_discrepancy():
    db = _db(overall_rating="Good", last_published_rating_date=date(2025, 1, 1))
    exp = _export_facts(_row(**_rated("Good", "2025-01-01")))
    out = compare(db, exp, FileRating("Good", date(2025, 1, 1), False), set(), date(2026, 10, 2))
    assert out["discrepancy"] is False and out["root_cause_codes"] == ""
