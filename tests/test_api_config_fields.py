"""Tests for public provider field visibility and plan entitlements."""

from api.config import filter_fields, get_subscription_entitlements, get_tier_config


def test_free_tier_exposes_public_provider_profile_fields():
    record = {
        "id": "LOC123",
        "logo_url": "https://example.com/logo.png",
        "funding_types": ["self_funded"],
        "fee_guidance": "From £1,200/week",
        "min_visit_duration": "1 hour",
        "contract_types": ["ongoing"],
        "age_ranges": ["older_adults_65+"],
        "email": "hidden@example.com",
    }

    filtered = filter_fields(record, "free")

    assert filtered["logo_url"] == "https://example.com/logo.png"
    assert filtered["funding_types"] == ["self_funded"]
    assert filtered["fee_guidance"] == "From £1,200/week"
    assert filtered["min_visit_duration"] == "1 hour"
    assert filtered["contract_types"] == ["ongoing"]
    assert filtered["age_ranges"] == ["older_adults_65+"]
    assert filtered["email"] is None


def test_free_plan_launch_limits_match_public_pricing():
    config = get_tier_config("free")

    assert config["rate"] == 2
    assert config["daily"] == 20
    assert config["rolling_7d"] == 60
    assert config["export"] == 25
    assert config["monitors"] == 1


def test_pro_and_business_seat_entitlements_are_persistable():
    pro = get_subscription_entitlements("pro", extra_seats=2)
    business = get_subscription_entitlements("business", extra_seats=0)

    assert pro["included_users"] == 3
    assert pro["extra_seats"] == 2
    assert pro["max_users"] == 5
    assert pro["seat_price_gbp"] == 15
    assert business["included_users"] == 10
    assert business["max_users"] == 10
