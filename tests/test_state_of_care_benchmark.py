from datetime import date

from tools.state_of_care_benchmark import (
    Service,
    band,
    is_dual_secondary,
    measures,
    movement,
    naive_classifier,
    registered_at,
    service_from_export,
)


def test_band_edges():
    assert [band(b) for b in (None, 0, 1, 10, 11, 49, 50, 300)] == [
        "unknown", "unknown", "1-10", "1-10", "11-49", "11-49", "50+", "50+",
    ]


def test_measures_exclude_dormant_and_compute_large_home_shares():
    services = [
        Service("a", True, 5, False, False, False),
        Service("b", True, 30, False, False, False),
        Service("c", True, 65, False, False, False),
        Service("d", True, 80, False, False, True),  # dormant: excluded
        Service("e", False, None, True, True, False),
        Service("f", False, None, True, False, True),  # dormant homecare
    ]
    m = measures(services)
    assert (m["care_homes"], m["homecare"], m["supported_living"]) == (3, 1, 1)
    assert m["care_homes_by_band"] == {"1-10": 1, "11-49": 1, "50+": 1, "unknown": 0}
    assert m["large_home_share_of_homes"] == round(1 / 3, 4)
    assert m["large_home_share_of_beds"] == round(65 / 100, 4)


def test_service_from_export_reads_care_home_beds_and_service_types():
    s = service_from_export({
        "locationId": "1-1", "careHome": "Y", "numberOfBeds": 42, "dormancy": "N",
        "gacServiceTypes": [{"description": "Care home service with nursing"},
                            {"description": "Domiciliary care service"}],
    })
    assert (s.care_home, s.beds, s.homecare, s.supported_living, s.dormant) == (True, 42, True, False, False)


def test_registered_at_reconstructs_a_past_register():
    as_at = date(2026, 4, 1)
    assert registered_at({"registrationDate": "2020-01-01", "registrationStatus": "Registered"}, as_at)
    assert not registered_at({"registrationDate": "2026-05-01", "registrationStatus": "Registered"}, as_at)
    assert registered_at({"registrationDate": "2020-01-01", "registrationStatus": "Deregistered",
                          "deregistrationDate": "2026-06-01"}, as_at)
    assert not registered_at({"registrationDate": "2020-01-01", "registrationStatus": "Deregistered",
                              "deregistrationDate": "2026-03-01"}, as_at)
    assert not registered_at({"registrationDate": "2020-01-01", "registrationStatus": "Deregistered"}, as_at)


def test_movement_counts_only_confirmed_closures():
    rows = [
        {"careHome": "Y", "registrationDate": "2026-05-01", "registrationStatus": "Registered"},
        {"careHome": "Y", "registrationDate": "2010-01-01", "registrationStatus": "Deregistered",
         "deregistrationDate": "2026-06-01", "locationId": "closed"},
        {"careHome": "Y", "registrationDate": "2010-01-01", "registrationStatus": "Deregistered",
         "deregistrationDate": "2026-06-01", "locationId": "moved"},
        {"careHome": "Y", "registrationDate": "2010-01-01", "registrationStatus": "Deregistered",
         "deregistrationDate": "2024-06-01", "locationId": "old"},
    ]
    end = date(2026, 10, 16)
    naive = movement(rows, window_end=end, classify=naive_classifier)["care_homes"]
    assert (naive["registrations"], naive["registration_endings"], naive["confirmed_closures"]) == (1, 2, 2)
    classified = movement(
        rows, window_end=end,
        classify=lambda r: "re_registration" if r["locationId"] == "moved" else "confirmed_closure",
    )["care_homes"]
    assert classified["confirmed_closures"] == 1
    assert classified["endings_by_class"] == {"confirmed_closure": 1, "re_registration": 1}


def test_dual_registration_keeps_only_the_primary_line():
    assert is_dual_secondary("Dual Registration", "N")
    assert not is_dual_secondary("Dual Registration", "Y")
    assert not is_dual_secondary("", "")
