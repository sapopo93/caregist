from __future__ import annotations

import pytest

from api.services.postcode_geocode import (
    compact_uk_postcode,
    is_uk_outward_code,
    postcodes_io_fallback_path,
    postcodes_io_lookup_path,
)


@pytest.mark.parametrize(
    ("value", "compact"),
    [
        ("SO15", "SO15"),
        ("so15", "SO15"),
        ("BN14", "BN14"),
        ("SO15 2BG", "SO152BG"),
        ("sw1a 1aa", "SW1A1AA"),
    ],
)
def test_compact_uk_postcode(value, compact):
    assert compact_uk_postcode(value) == compact


@pytest.mark.parametrize(
    ("value", "outward"),
    [
        ("SO15", True),
        ("BN14", True),
        ("SW1A", True),
        ("SO15 2BG", False),
        ("so15 2bg", False),
        ("NOTAPLACE", False),
        ("123", False),
    ],
)
def test_outward_code_detection(value, outward):
    assert is_uk_outward_code(value) is outward


def test_so15_uses_outcodes_endpoint():
    assert postcodes_io_lookup_path("SO15") == "/outcodes/SO15"
    assert postcodes_io_lookup_path("BN14") == "/outcodes/BN14"
    assert postcodes_io_lookup_path("SO15 2BG") == "/postcodes/SO152BG"


def test_full_postcode_can_fall_back_to_outward_district():
    assert postcodes_io_fallback_path("SO15 2BG") == "/outcodes/SO15"
    assert postcodes_io_fallback_path("SO15") is None
    assert postcodes_io_fallback_path("zzzz") is None
