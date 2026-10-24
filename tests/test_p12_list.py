import csv
import io
from datetime import date
from unittest.mock import patch

import pytest

from api.queries.p12_list import P12_BASE_POPULATION
from api.services.p12_list import (
    STATEMENT,
    FileDomainRating,
    P12Disabled,
    build_p12_list,
    p12_to_csv,
)


def _base(lid, reg=date(2015, 1, 1), beds=30):
    return {"id": lid, "provider_id": "P" + lid, "name": f"Home {lid}", "postcode": "M1 1AA",
            "local_authority": "Manchester", "region": "North West", "number_of_beds": beds,
            "registration_date": reg}


def _build(base, api, file):
    with patch("api.config.settings.p12_list_enabled", True):
        return build_p12_list(region="North West", base_rows=base, api_well_led=api, file_well_led=file,
                              file_edition_date=date(2026, 10, 2), file_sha256="abc")


def test_flag_defaults_off_and_refuses():
    from api.config import Settings

    assert Settings.model_fields["p12_list_enabled"].default is False
    with pytest.raises(P12Disabled):
        build_p12_list(region="x", base_rows=[], api_well_led={}, file_well_led={},
                       file_edition_date=None, file_sha256=None)


def test_base_population_sql_is_11_to_49_active_care_homes():
    sql = " ".join(P12_BASE_POPULATION.split())
    assert "number_of_beds BETWEEN 11 AND 49" in sql
    assert "UPPER(status) = 'ACTIVE'" in sql and "ILIKE '%care home service%'" in sql


def test_lists_only_current_below_good_and_reconciles_every_base_row():
    base = [_base(str(i)) for i in range(7)] + [_base("inh", reg=date(2025, 1, 1))]
    api = {
        "0": ("Requires improvement", date(2025, 3, 1)),
        "1": ("Good", date(2019, 1, 1)),             # older API Good
        "2": ("Inadequate", date(2024, 1, 1)),
        "3": ("Good", date(2024, 1, 1)),
        "4": ("Outstanding", date(2022, 1, 1)),
        "5": (None, None),
        "6": ("Good", None),                          # undated conflict
        "inh": ("Inadequate", date(2020, 1, 1)),      # predates registration
    }
    file = {
        "1": FileDomainRating("Requires improvement", date(2026, 5, 1), False),  # newer file wins
        "2": FileDomainRating("Inadequate", date(2024, 1, 1), False),
        "6": FileDomainRating("Inadequate", date(2026, 1, 1), False),
    }
    result = _build(base, api, file)
    assert [r["cqc_location_id"] for r in result.rows] == ["0", "1", "2"]
    assert result.reconciliation == {
        "current_good": 1, "current_outstanding": 1, "inherited": 1, "listed": 3, "none": 1, "unresolved": 1,
    }
    assert sum(result.reconciliation.values()) == result.base_count == 8
    row1 = next(r for r in result.rows if r["cqc_location_id"] == "1")
    assert (row1["well_led_rating"], row1["well_led_published"], row1["rating_source"]) == (
        "Requires improvement", "2026-05-01", "cqc_ratings_file")
    assert (row1["api_well_led"], row1["api_well_led_date"]) == ("Good", "2019-01-01")


def test_csv_wording_is_factual_and_carries_dates():
    result = _build([_base("0")], {"0": ("Inadequate", date(2025, 3, 1))}, {})
    rows = list(csv.DictReader(io.StringIO(p12_to_csv(result))))
    assert rows[0]["well_led_published"] == "2025-03-01"
    assert rows[0]["statement"] == STATEMENT
    lowered = STATEMENT.lower()
    assert "no prediction" in lowered
    for word in ("likely", "at risk", "will fail", "struggling", "opportunity"):
        assert word not in lowered


def test_empty_region_writes_header_only():
    result = _build([], {}, {})
    assert p12_to_csv(result).count("\n") == 1
