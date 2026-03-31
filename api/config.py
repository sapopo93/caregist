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
    default_page_size: int = 20
    app_url: str = "http://localhost:3000"
    resend_api_key: str = ""
    enquiry_from_email: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def validate_production(self) -> None:
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

# Tier limits — designed so free users can evaluate for a full month
# but professionals who use it daily hit the monthly cap and upgrade.
#
# Free:     150/day × 30 = 4,500/month → family completes search, pro evaluates for ~3 weeks
# Starter:  500/day × 30 = 15,000/month (cap at 10,000 — pro hits it mid-month)
# Pro:      2,000/day × 30 = 60,000/month (cap at 50,000 — team hits it in week 3)
# Business: 10,000/day × 30 = 300,000/month (cap at 250,000)
TIERS = {
    "free":     {"rate": 5,    "daily": 150,    "monthly": 4500,     "page_size": 5,   "fields": "basic",    "nearby": False, "export": 100,   "compare": 0,  "webhooks": False, "monitors": 2},
    "starter":  {"rate": 30,   "daily": 500,    "monthly": 10000,    "page_size": 20,  "fields": "standard", "nearby": True,  "export": 500,   "compare": 3,  "webhooks": False, "monitors": 25},
    "pro":      {"rate": 60,   "daily": 2000,   "monthly": 50000,    "page_size": 50,  "fields": "standard", "nearby": True,  "export": 5000,  "compare": 5,  "webhooks": False, "monitors": 100},
    "business": {"rate": 200,  "daily": 10000,  "monthly": 250000,   "page_size": 100, "fields": "full",     "nearby": True,  "export": 10000, "compare": 10, "webhooks": True,  "monitors": 500},
    "admin":    {"rate": 99999,"daily": 9999999,"monthly": 99999999, "page_size": 100, "fields": "full",     "nearby": True,  "export": 99999, "compare": 99, "webhooks": True,  "monitors": 99999},
}

# Fields included in the free-tier basic CSV export
BASIC_CSV_FIELDS = ["name", "town", "postcode", "overall_rating", "type", "last_inspection_date"]

BASIC_FIELDS = [
    "id", "name", "slug", "type", "status", "town", "postcode",
    "region", "overall_rating", "service_types", "quality_tier",
]

STANDARD_FIELDS = BASIC_FIELDS + [
    "phone", "email", "website", "latitude", "longitude", "county",
    "local_authority", "specialisms", "regulated_activities",
    "number_of_beds", "ownership_type", "quality_score",
    "rating_safe", "rating_effective", "rating_caring",
    "rating_responsive", "rating_well_led", "last_inspection_date",
    "inspection_report_url", "is_claimed", "review_count", "avg_review_rating",
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
    return TIERS.get(tier, TIERS["free"])


def get_allowed_fields(tier: str) -> set[str]:
    """Get the set of fields allowed for a tier."""
    config = get_tier_config(tier)
    return FIELD_SETS.get(config["fields"], FIELD_SETS["basic"])


def filter_fields(record: dict, tier: str) -> dict:
    """Strip fields not allowed by the tier. Hidden fields become None."""
    allowed = get_allowed_fields(tier)
    return {k: (v if k in allowed else None) for k, v in record.items()}
