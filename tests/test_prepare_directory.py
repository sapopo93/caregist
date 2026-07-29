"""Tests for prepare_directory.py output generation."""


from prepare_directory import (
    generate_slug,
    geocode_from_postcode,
    meta_title,
    meta_description,
    normalize_rating,
    choose_type,
    inspection_url,
    _friendly_type,
    _location_text,
    BRAND_NAME,
)


class TestGenerateSlug:
    def test_basic(self):
        used = set()
        slug = generate_slug("Henley House", "Ipswich", "1-123", used)
        assert slug == "henley-house-ipswich"
        assert slug in used

    def test_collision(self):
        used = {"henley-house-ipswich"}
        slug = generate_slug("Henley House", "Ipswich", "1-456", used)
        assert slug != "henley-house-ipswich"
        assert slug in used

    def test_no_town(self):
        used = set()
        slug = generate_slug("Test Provider", "", "1-789", used)
        assert slug == "test-provider"


class TestMetaTitle:
    def test_with_town(self):
        title = meta_title("Henley House", "Ipswich")
        assert "Henley House" in title
        assert "Ipswich" in title
        assert BRAND_NAME in title

    def test_without_town(self):
        title = meta_title("Test", None)
        assert "England" in title

    def test_care_home_type(self):
        title = meta_title("Henley House", "Ipswich", service_types="Residential Homes")
        assert "Care Home" in title


class TestMetaDescription:
    def test_care_home(self):
        desc = meta_description(
            "Henley House", "Social Care Org", "Ipswich", "Suffolk",
            "Good", "Dementia|Physical Disabilities", "East",
            service_types="Residential Homes", beds=66,
        )
        assert "66 beds" in desc
        assert "Ipswich" in desc
        assert "Good" in desc
        assert BRAND_NAME in desc

    def test_dental(self):
        desc = meta_description(
            "My Dentist", "Primary Dental Care", "London", None,
            "Good", None, "London",
        )
        assert "dental" in desc.lower()

    def test_gp(self):
        desc = meta_description(
            "St Johns", "Primary Medical Services", "Altrincham", None,
            "Good", None, "North West",
        )
        assert "GP surgery" in desc

    def test_no_england_duplication(self):
        desc = meta_description(
            "Test", None, None, None, "Good", None, None,
        )
        assert "England, England" not in desc


class TestLocationText:
    def test_town_and_county(self):
        assert _location_text("Ipswich", "Suffolk", "East") == "Ipswich, Suffolk"

    def test_town_only(self):
        assert _location_text("Ipswich", None, "East") == "Ipswich"

    def test_region_fallback(self):
        assert _location_text(None, None, "East") == "East"

    def test_england_fallback(self):
        assert _location_text(None, None, None) == "England"

    def test_no_duplicate(self):
        assert _location_text("London", "London", "London") == "London"


class TestFriendlyType:
    def test_residential_homes(self):
        assert _friendly_type(None, "Residential Homes") == "Care Home"

    def test_nursing_homes(self):
        assert _friendly_type(None, "Nursing Homes") == "Nursing Home"

    def test_homecare(self):
        assert _friendly_type(None, "Homecare Agencies") == "Home Care Agency"

    def test_dental_by_type(self):
        assert _friendly_type("Primary Dental Care", None) == "Dental Practice"

    def test_fallback(self):
        assert _friendly_type(None, None) == "care provider"


class TestNormalizeRating:
    def test_good(self):
        assert normalize_rating("Good") == "Good"

    def test_empty(self):
        assert normalize_rating("") == "Not Yet Inspected"

    def test_none(self):
        assert normalize_rating(None) == "Not Yet Inspected"


class TestChooseType:
    def test_raw_type(self):
        assert choose_type("Social Care Org", None) == "Social Care Org"

    def test_from_service_types(self):
        assert choose_type(None, "Residential Homes|Nursing Homes") == "Residential Homes"

    def test_both_none(self):
        assert choose_type(None, None) is None


class TestInspectionUrl:
    def test_with_id(self):
        url = inspection_url("1-123", None)
        assert url == "https://www.cqc.org.uk/location/1-123"

    def test_existing_url(self):
        url = inspection_url("1-123", "https://custom.url")
        assert url == "https://custom.url"

    def test_empty(self):
        assert inspection_url("", None) is None


class _FakeResponse:
    status_code = 200

    def json(self):
        return {
            "result": {
                "latitude": 51.501,
                "longitude": -0.141,
            }
        }


class _FakePostcodeCache:
    def __init__(self, initial=None):
        self.initial = initial or {}
        self.set_calls = []

    def get(self, postcode):
        return self.initial.get(postcode)

    def set(self, postcode, latitude, longitude):
        self.set_calls.append((postcode, latitude, longitude))


def test_geocode_from_postcode_uses_cache_before_http(monkeypatch):
    cache = _FakePostcodeCache({"SW1A 1AA": (51.501, -0.141)})

    def fail_get(*args, **kwargs):
        raise AssertionError("postcodes.io should not be called on cache hit")

    monkeypatch.setattr("prepare_directory.requests.get", fail_get)

    assert geocode_from_postcode("SW1A 1AA", cache=cache) == (51.501, -0.141)


def test_geocode_from_postcode_writes_successful_http_result_to_cache(monkeypatch):
    cache = _FakePostcodeCache()
    monkeypatch.setattr("prepare_directory.requests.get", lambda *args, **kwargs: _FakeResponse())

    assert geocode_from_postcode("SW1A 1AA", cache=cache) == (51.501, -0.141)
    assert cache.set_calls == [("SW1A 1AA", 51.501, -0.141)]
