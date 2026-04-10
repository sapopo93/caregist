"""Application configuration via environment variables."""

from __future__ import annotations

import sys

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://caregist:caregist_dev@localhost:5432/caregist"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_master_key: str = "change_me_in_production"
    cors_origins: str = "http://localhost:3000"
    query_timeout_ms: int = 10000
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_pro_seat: str = ""
    stripe_price_business: str = ""
    stripe_price_enterprise: str = ""
    default_page_size: int = 20
    app_url: str = "http://localhost:3000"
    resend_api_key: str = ""
    enquiry_from_email: str = ""
    sentry_dsn: str = ""
    support_platform_url: str = ""
    caregist_to_support_token: str = ""
    support_internal_token: str = "caregist-internal-token"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def validate_production(self) -> None:
        if "pytest" in sys.modules:
            return
        if self.api_master_key == "change_me_in_production":
            # On any non-localhost environment, this is production
            if self.database_url != "postgresql://caregist:caregist_dev@localhost:5432/caregist":
                raise RuntimeError(
                    "FATAL: API_MASTER_KEY is still the default value. "
                    "Set a secure API_MASTER_KEY environment variable before starting in production."
                )
            print("WARNING: API_MASTER_KEY is set to default. Set a secure value in .env", file=sys.stderr)


settings = Settings()
settings.validate_production()

# --- Tier definitions (single source of truth) ---

# Tier limits — staircase designed around job-to-be-done, not just usage caps.
# Free is intentionally constrained to evaluation. Paid tiers are built around the
# first solo workflow, small-team production use, and higher-volume operational integration.
TIERS = {
    "free": {
        "rate": 2,
        "rate_window_seconds": 1,
        "daily": 20,
        "rolling_7d": 60,
        "monthly": 300,
        "page_size": 5,
        "fields": "basic",
        "nearby": False,
        "export": 25,
        "compare": 0,
        "webhooks": False,
        "monitors": 1,
        "feed_rows": 10,
        "saved_filters": 0,
        "feed_digests": 0,
        "feed_api": False,
        "included_users": 1,
        "base_price_gbp": 0,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "next_tier": "starter",
    },
    "starter": {
        "rate": 10,
        "rate_window_seconds": 1,
        "daily": 500,
        "rolling_7d": 3500,
        "monthly": 10000,
        "page_size": 20,
        "fields": "standard",
        "nearby": True,
        "export": 500,
        "compare": 3,
        "webhooks": False,
        "monitors": 15,
        "feed_rows": 25,
        "saved_filters": 3,
        "feed_digests": 1,
        "feed_api": True,
        "included_users": 1,
        "base_price_gbp": 39,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "next_tier": "pro",
    },
    "pro": {
        "rate": 25,
        "rate_window_seconds": 1,
        "daily": 2000,
        "rolling_7d": 14000,
        "monthly": 50000,
        "page_size": 50,
        "fields": "standard",
        "nearby": True,
        "export": 5000,
        "compare": 5,
        "webhooks": False,
        "monitors": 100,
        "feed_rows": 50,
        "saved_filters": 20,
        "feed_digests": 10,
        "feed_api": True,
        "included_users": 3,
        "base_price_gbp": 99,
        "seat_price_gbp": 15,
        "extra_seat_min_tier": "pro",
        "next_tier": "business",
    },
    "business": {
        "rate": 60,
        "rate_window_seconds": 1,
        "daily": 10000,
        "rolling_7d": 70000,
        "monthly": 250000,
        "page_size": 100,
        "fields": "full",
        "nearby": True,
        "export": 10000,
        "compare": 10,
        "webhooks": True,
        "monitors": 500,
        "feed_rows": 100,
        "saved_filters": 100,
        "feed_digests": 100,
        "feed_api": True,
        "included_users": 10,
        "base_price_gbp": 399,
        "seat_price_gbp": 15,
        "extra_seat_min_tier": "business",
        "next_tier": "enterprise",
    },
    "enterprise": {
        "rate": 200,
        "rate_window_seconds": 1,
        "daily": 50000,
        "rolling_7d": 350000,
        "monthly": 1500000,
        "page_size": 100,
        "fields": "full",
        "nearby": True,
        "export": 50000,
        "compare": 20,
        "webhooks": True,
        "monitors": 5000,
        "feed_rows": 250,
        "saved_filters": 500,
        "feed_digests": 500,
        "feed_api": True,
        "included_users": 10,
        "base_price_gbp": 0,
        "seat_price_gbp": 15,
        "extra_seat_min_tier": "business",
        "next_tier": None,
    },
    "admin": {
        "rate": 99999,
        "rate_window_seconds": 1,
        "daily": 9999999,
        "rolling_7d": 99999999,
        "monthly": 99999999,
        "page_size": 100,
        "fields": "full",
        "nearby": True,
        "export": 99999,
        "compare": 99,
        "webhooks": True,
        "monitors": 99999,
        "feed_rows": 1000,
        "saved_filters": 99999,
        "feed_digests": 99999,
        "feed_api": True,
        "included_users": 99999,
        "base_price_gbp": 0,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": "pro",
        "next_tier": None,
    },
}

# Fields included in the free-tier basic CSV export
# Deliberately richer than CQC's own CSV (which omits ratings entirely)
BASIC_CSV_FIELDS = [
    "name", "town", "county", "postcode", "region", "local_authority",
    "phone", "website", "overall_rating", "type", "service_types",
    "specialisms", "number_of_beds", "quality_score", "quality_tier",
    "last_inspection_date", "inspection_report_url",
]

BASIC_FIELDS = [
    "id", "name", "slug", "type", "status", "town", "county", "postcode",
    "region", "local_authority", "overall_rating", "service_types",
    "specialisms", "number_of_beds", "quality_score", "quality_tier",
    "phone", "website", "last_inspection_date", "inspection_report_url",
    "inspection_summary", "profile_description", "profile_photos",
    "virtual_tour_url", "inspection_response", "profile_tier",
    "logo_url", "funding_types", "fee_guidance", "min_visit_duration",
    "contract_types", "age_ranges",
]

STANDARD_FIELDS = BASIC_FIELDS + [
    "email", "latitude", "longitude",
    "regulated_activities", "ownership_type",
    "rating_safe", "rating_effective", "rating_caring",
    "rating_responsive", "rating_well_led",
    "is_claimed", "review_count", "avg_review_rating",
]

FULL_FIELDS = STANDARD_FIELDS + [
    "provider_id", "registration_date", "geocode_source",
    "data_source", "data_attribution", "created_at", "updated_at",
]

FIELD_SETS = {
    "basic": set(BASIC_FIELDS),
    "standard": set(STANDARD_FIELDS),
    "full": set(FULL_FIELDS),
}

TIER_RANK = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "business": 3,
    "enterprise": 4,
    "admin": 5,
}


def get_tier_config(tier: str) -> dict:
    """Get config for a tier, defaulting to free."""
    normalized = (tier or "free").lower()
    if normalized in TIERS:
        return TIERS[normalized]
    if normalized.startswith("enterprise"):
        return TIERS["enterprise"]
    return TIERS["free"]


def get_tier_price_gbp(tier: str) -> int:
    return int(get_tier_config(tier).get("base_price_gbp", 0))


def get_included_user_count(tier: str) -> int:
    return int(get_tier_config(tier).get("included_users", 1))


def get_seat_price_gbp(tier: str) -> int:
    return int(get_tier_config(tier).get("seat_price_gbp", 0))


def get_next_tier(tier: str) -> str | None:
    return get_tier_config(tier).get("next_tier")


def get_tier_rank(tier: str) -> int:
    normalized = (tier or "free").lower()
    if normalized.startswith("enterprise"):
        normalized = "enterprise"
    return int(TIER_RANK.get(normalized, 0))


def max_tier(*tiers: str | None) -> str:
    candidates = [tier for tier in tiers if tier]
    if not candidates:
        return "free"
    return max(candidates, key=get_tier_rank)


def allows_extra_seats(tier: str) -> bool:
    return get_seat_price_gbp(tier) > 0


def get_max_users(tier: str, extra_seats: int = 0) -> int:
    base = get_included_user_count(tier)
    return base + max(0, extra_seats) if allows_extra_seats(tier) else base


def get_subscription_entitlements(tier: str, extra_seats: int = 0) -> dict[str, int | str | bool | None]:
    config = get_tier_config(tier)
    return {
        "tier": tier,
        "included_users": get_included_user_count(tier),
        "extra_seats": max(0, extra_seats),
        "max_users": get_max_users(tier, extra_seats),
        "seat_price_gbp": get_seat_price_gbp(tier),
        "allows_extra_seats": allows_extra_seats(tier),
        "next_tier": config.get("next_tier"),
    }


def get_allowed_fields(tier: str) -> set[str]:
    """Get the set of fields allowed for a tier."""
    config = get_tier_config(tier)
    return FIELD_SETS.get(config["fields"], FIELD_SETS["basic"])


def filter_fields(record: dict, tier: str) -> dict:
    """Strip fields not allowed by the tier. Hidden fields become None."""
    allowed = get_allowed_fields(tier)
    return {k: (v if k in allowed else None) for k, v in record.items()}
