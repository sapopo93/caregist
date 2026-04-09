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
            # On Render (or any host that sets DATABASE_URL externally), this is production
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
#
# Free:       evaluation — taste the data, hit friction fast, upgrade to solve a real problem
#             100/day keeps it useful for search/browse without enabling recurring workflows
# Starter:    first real workflow — enough for a solo consultant or operator to act on data daily
#             500/day × 30 = 15,000/month (cap at 10,000 — hits it mid-month in heavy use)
# Pro:        small-team production use — broader monitoring and more volume
#             2,000/day × 30 = 60,000/month (cap at 50,000 — team hits it in week 3)
# Business:   operational integration — high limits, full fields, workflow embedding
#             10,000/day × 30 = 300,000/month (cap at 250,000)
# Enterprise: custom — negotiated per contract
TIERS = {
    "free":       {"rate": 5,    "daily": 100,    "monthly": 3000,     "page_size": 5,   "fields": "basic",    "nearby": False, "export": 25,    "compare": 0,  "webhooks": False, "monitors": 1},
    "starter":    {"rate": 30,   "daily": 500,    "monthly": 10000,    "page_size": 20,  "fields": "standard", "nearby": True,  "export": 500,   "compare": 3,  "webhooks": False, "monitors": 15},
    "pro":        {"rate": 60,   "daily": 2000,   "monthly": 50000,    "page_size": 50,  "fields": "standard", "nearby": True,  "export": 5000,  "compare": 5,  "webhooks": False, "monitors": 100},
    "business":   {"rate": 200,  "daily": 10000,  "monthly": 250000,   "page_size": 100, "fields": "full",     "nearby": True,  "export": 10000, "compare": 10, "webhooks": True,  "monitors": 500},
    "enterprise": {"rate": 500,  "daily": 50000,  "monthly": 1500000,  "page_size": 100, "fields": "full",     "nearby": True,  "export": 50000, "compare": 20, "webhooks": True,  "monitors": 5000},
    "admin":      {"rate": 99999,"daily": 9999999,"monthly": 99999999, "page_size": 100, "fields": "full",     "nearby": True,  "export": 99999, "compare": 99, "webhooks": False, "monitors": 99999},
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


def get_tier_config(tier: str) -> dict:
    """Get config for a tier, defaulting to free."""
    normalized = (tier or "free").lower()
    if normalized in TIERS:
        return TIERS[normalized]
    if normalized.startswith("enterprise"):
        return TIERS["enterprise"]
    return TIERS["free"]


def get_allowed_fields(tier: str) -> set[str]:
    """Get the set of fields allowed for a tier."""
    config = get_tier_config(tier)
    return FIELD_SETS.get(config["fields"], FIELD_SETS["basic"])


def filter_fields(record: dict, tier: str) -> dict:
    """Strip fields not allowed by the tier. Hidden fields become None."""
    allowed = get_allowed_fields(tier)
    return {k: (v if k in allowed else None) for k, v in record.items()}
