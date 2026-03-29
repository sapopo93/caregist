"""Tests for quality_audit.py scoring logic."""

import pytest
import pandas as pd

from quality_audit import score_row, score_to_tier


def _make_row(**kwargs) -> pd.Series:
    """Build a test row with defaults."""
    defaults = {
        "name": "Test Provider",
        "postalCode": "IP1 6TB",
        "mainPhoneNumber": "01234567890",
        "website": "https://example.com",
        "latitude": "52.088",
        "longitude": "1.150",
        "overallRating": "Good",
        "lastInspectionDate": "2024-01-15",
        "serviceTypes": "Residential Homes",
        "specialisms": "Dementia",
        "regulatedActivities": "Accommodation",
        "numberOfBeds": "66",
        "localAuthority": "Suffolk",
        "region": "East",
        "type": "Care Home",
        "name_issue": "",
        "postalCode_issue": "",
        "mainPhoneNumber_issue": "",
        "website_issue": "",
        "coords_issue": "",
        "date_issue": "",
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


class TestScoreRow:
    def test_complete_record(self):
        row = _make_row()
        score = score_row(row)
        assert score >= 85, f"Complete record should be COMPLETE tier, got {score}"

    def test_minimal_record(self):
        row = _make_row(
            mainPhoneNumber="", website="", latitude="", longitude="",
            lastInspectionDate="", serviceTypes="", specialisms="",
            regulatedActivities="", numberOfBeds="", localAuthority="", region="",
            coords_issue="MISSING_COORDS",
        )
        score = score_row(row)
        assert score < 40, f"Minimal record should be SPARSE tier, got {score}"

    def test_invalid_fields_reduce_score(self):
        good_row = _make_row()
        bad_row = _make_row(
            postalCode_issue="INVALID_POSTCODE",
            mainPhoneNumber_issue="INVALID_PHONE",
        )
        assert score_row(bad_row) < score_row(good_row)

    def test_name_gives_points(self):
        with_name = _make_row()
        without_name = _make_row(name="")
        assert score_row(with_name) > score_row(without_name)


class TestScoreToTier:
    def test_complete(self):
        assert score_to_tier(85) == "COMPLETE"
        assert score_to_tier(100) == "COMPLETE"

    def test_good(self):
        assert score_to_tier(60) == "GOOD"
        assert score_to_tier(84) == "GOOD"

    def test_partial(self):
        assert score_to_tier(40) == "PARTIAL"
        assert score_to_tier(59) == "PARTIAL"

    def test_sparse(self):
        assert score_to_tier(0) == "SPARSE"
        assert score_to_tier(39) == "SPARSE"
