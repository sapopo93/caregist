"""Tests for clean_cqc.py normalization functions."""

import pytest

from clean_cqc import (
    normalize_name,
    normalize_phone,
    normalize_postcode,
    normalize_website,
    normalize_rating,
    normalize_coordinates,
    compute_directory_status,
    normalize_address,
    is_blank,
)


class TestNormalizeName:
    def test_basic(self):
        name, issue = normalize_name("Henley House")
        assert name == "Henley House"
        assert issue == ""

    def test_all_caps(self):
        name, issue = normalize_name("HENLEY HOUSE")
        assert name == "Henley House"

    def test_special_chars(self):
        name, issue = normalize_name("Test (Care) Home")
        assert issue == "INVALID_NAME_CHARS"

    def test_blank(self):
        name, issue = normalize_name("")
        assert name == ""


class TestNormalizePhone:
    def test_valid_uk(self):
        phone, issue = normalize_phone("07908973809")
        assert issue == ""
        assert phone.replace(" ", "").startswith("0")

    def test_blank(self):
        phone, issue = normalize_phone("")
        assert phone == "NULL"
        assert issue == ""

    def test_invalid(self):
        phone, issue = normalize_phone("123")
        assert issue == "INVALID_PHONE"

    def test_international(self):
        phone, issue = normalize_phone("+447908973809")
        assert issue == ""


class TestNormalizePostcode:
    def test_valid(self):
        pc, issue = normalize_postcode("IP1 6TB")
        assert pc == "IP1 6TB"
        assert issue == ""

    def test_no_space(self):
        pc, issue = normalize_postcode("IP16TB")
        assert pc == "IP1 6TB"
        assert issue == ""

    def test_lowercase(self):
        pc, issue = normalize_postcode("ip1 6tb")
        assert pc == "IP1 6TB"

    def test_invalid(self):
        pc, issue = normalize_postcode("INVALID")
        assert issue == "INVALID_POSTCODE"

    def test_blank(self):
        pc, issue = normalize_postcode("")
        assert pc == ""


class TestNormalizeWebsite:
    def test_add_https(self):
        url, issue = normalize_website("example.com")
        assert url == "https://example.com"
        assert issue == ""

    def test_already_https(self):
        url, issue = normalize_website("https://example.com")
        assert url == "https://example.com"

    def test_blank(self):
        url, issue = normalize_website("")
        assert url == "NULL"


class TestNormalizeRating:
    def test_good(self):
        assert normalize_rating("Good", "Registered") == "Good"

    def test_case_insensitive(self):
        assert normalize_rating("good", "Registered") == "Good"

    def test_requires_improvement(self):
        assert normalize_rating("Requires improvement", "Registered") == "Requires Improvement"

    def test_empty_registered(self):
        assert normalize_rating("", "Registered") == "Not Yet Inspected"

    def test_outstanding(self):
        assert normalize_rating("Outstanding", "Registered") == "Outstanding"


class TestNormalizeCoordinates:
    def test_valid_uk(self):
        lat, lon, issue = normalize_coordinates("52.088", "1.150")
        assert issue == ""
        assert float(lat) == pytest.approx(52.088, abs=0.001)

    def test_outside_uk(self):
        lat, lon, issue = normalize_coordinates("40.0", "-74.0")
        assert issue == "INVALID_COORDS"

    def test_missing(self):
        lat, lon, issue = normalize_coordinates(None, None)
        assert issue == "MISSING_COORDS"


class TestComputeDirectoryStatus:
    def test_registered(self):
        assert compute_directory_status("Registered", "", "") == "ACTIVE"

    def test_deregistered(self):
        assert compute_directory_status("Deregistered", "2024-01-01", "") == "INACTIVE"

    def test_suspended(self):
        assert compute_directory_status("Registered", "", "true") == "SUSPENDED"


class TestNormalizeAddress:
    def test_normal(self):
        addr, issue = normalize_address("333 Henley Road, Ipswich")
        assert addr == "333 Henley Road, Ipswich"
        assert issue == ""

    def test_short(self):
        addr, issue = normalize_address("Flat 1")
        assert issue == "SUSPECT_ADDRESS"

    def test_blank(self):
        addr, issue = normalize_address("")
        assert addr == ""


class TestIsBlank:
    def test_none(self):
        assert is_blank(None) is True

    def test_empty(self):
        assert is_blank("") is True

    def test_null_string(self):
        assert is_blank("NULL") is True

    def test_value(self):
        assert is_blank("hello") is False
