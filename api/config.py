"""Application configuration via environment variables."""

from __future__ import annotations

import base64
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic_settings import BaseSettings


AWS_SECRET_ID_ENV = "AWS_SECRETS_MANAGER_SECRET_ID"
AWS_REGION_ENV = "AWS_REGION"

SECRET_ENV_NAMES = {
    "database_url": "DATABASE_URL",
    "api_master_key": "API_MASTER_KEY",
    "stripe_secret_key": "STRIPE_SECRET_KEY",
    "stripe_webhook_secret": "STRIPE_WEBHOOK_SECRET",
    "stripe_price_alerts_pro": "STRIPE_PRICE_ALERTS_PRO",
    "stripe_price_starter": "STRIPE_PRICE_STARTER",
    "stripe_price_pro": "STRIPE_PRICE_PRO",
    "stripe_price_pro_seat": "STRIPE_PRICE_PRO_SEAT",
    "stripe_price_business": "STRIPE_PRICE_BUSINESS",
    "stripe_price_enterprise": "STRIPE_PRICE_ENTERPRISE",
    "stripe_price_profile_enhanced": "STRIPE_PRICE_PROFILE_ENHANCED",
    "stripe_price_profile_premium": "STRIPE_PRICE_PROFILE_PREMIUM",
    "stripe_price_profile_sponsored": "STRIPE_PRICE_PROFILE_SPONSORED",
    "resend_api_key": "RESEND_API_KEY",
    "caregist_to_support_token": "CAREGIST_TO_SUPPORT_TOKEN",
    "support_internal_token": "SUPPORT_INTERNAL_TOKEN",
    "webhook_secret_key": "WEBHOOK_SECRET_KEY",
    "redis_url": "REDIS_URL",
}
SECRET_ENV_ALIASES = {
    "stripe_price_alerts_pro": ("STRIPE_PRICE_ALERTS_PRO_MONTHLY",),
    "stripe_price_starter": ("STRIPE_PRICE_DATA_STARTER_MONTHLY",),
    "stripe_price_pro": ("STRIPE_PRICE_DATA_PRO_MONTHLY",),
    "stripe_price_business": ("STRIPE_PRICE_DATA_BUSINESS_MONTHLY",),
    "stripe_price_profile_enhanced": ("STRIPE_PRICE_PROVIDER_ENHANCED_LISTING_MONTHLY",),
    "stripe_price_profile_premium": ("STRIPE_PRICE_PROVIDER_PRO_LISTING_MONTHLY",),
    "stripe_price_profile_sponsored": ("STRIPE_PRICE_SPONSORED_LISTING_MONTHLY",),
}
REQUIRED_PRODUCTION_SECRETS = (
    "database_url",
    "api_master_key",
    "support_internal_token",
    "stripe_secret_key",
    "stripe_webhook_secret",
)


class AwsSecretsManagerSecretLoader:
    """Load application secrets from one JSON secret in AWS Secrets Manager."""

    def __init__(self, secret_id: str, region_name: str | None = None):
        self.secret_id = secret_id
        self.region_name = region_name

    def load(self) -> dict[str, str]:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised only in incomplete deployments
            raise RuntimeError("boto3 is required to load production secrets from AWS Secrets Manager.") from exc

        client = boto3.client("secretsmanager", region_name=self.region_name)
        response = client.get_secret_value(SecretId=self.secret_id)
        raw_secret = response.get("SecretString")
        if raw_secret is None and response.get("SecretBinary") is not None:
            raw_secret = base64.b64decode(response["SecretBinary"]).decode("utf-8")
        if not raw_secret:
            raise RuntimeError(f"AWS secret {self.secret_id!r} is empty.")

        try:
            payload = json.loads(raw_secret)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"AWS secret {self.secret_id!r} must be a JSON object.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"AWS secret {self.secret_id!r} must be a JSON object.")

        return _normalize_secret_payload(payload)


def _is_production(environ: Mapping[str, str] | None = None) -> bool:
    env = environ or os.environ
    return env.get("NODE_ENV", "").lower() == "production"


def validate_cors_origins(cors_origins: str, *, production: bool) -> None:
    """Reject wildcard or malformed CORS origins when credentials are enabled."""
    origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    if not origins:
        raise RuntimeError("FATAL: CORS origins must include at least one explicit origin.")

    for origin in origins:
        parsed = urlparse(origin)
        if origin == "*" or "*" in origin:
            if production:
                raise RuntimeError("FATAL: CORS wildcard origins are not allowed in production.")
            continue
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.params or parsed.query or parsed.fragment:
            raise RuntimeError(f"FATAL: Invalid CORS origin: {origin!r}. Use explicit scheme://host[:port] origins.")


def _lookup_secret_value(payload: Mapping[str, Any], field_name: str, env_name: str) -> Any:
    for key in (env_name, *SECRET_ENV_ALIASES.get(field_name, ()), field_name):
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _normalize_secret_payload(payload: Mapping[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field_name, env_name in SECRET_ENV_NAMES.items():
        value = _lookup_secret_value(payload, field_name, env_name)
        if value is not None:
            values[field_name] = str(value)
    return values


def _load_dev_dotenv_secrets(dotenv_path: str | Path = ".env") -> dict[str, str]:
    path = Path(dotenv_path)
    if not path.exists():
        return {}
    try:
        from dotenv import dotenv_values
    except ImportError:
        return {}
    return _normalize_secret_payload(dotenv_values(path))


def _load_dev_env_secrets(environ: Mapping[str, str]) -> dict[str, str]:
    return _normalize_secret_payload(environ)


def load_application_secrets(
    *,
    environ: Mapping[str, str] | None = None,
    dotenv_path: str | Path = ".env",
    secret_loader_cls: type[AwsSecretsManagerSecretLoader] = AwsSecretsManagerSecretLoader,
) -> dict[str, str]:
    env = environ or os.environ
    is_production = _is_production(env)
    secret_id = env.get(AWS_SECRET_ID_ENV)

    if not secret_id and is_production:
        raise RuntimeError(f"FATAL: {AWS_SECRET_ID_ENV} must be set in production.")

    values: dict[str, str] = {}
    if not is_production:
        values.update(_load_dev_dotenv_secrets(dotenv_path))
        values.update(_load_dev_env_secrets(env))
    if secret_id:
        loader = secret_loader_cls(secret_id, env.get(AWS_REGION_ENV))
        values.update(loader.load())

    if is_production:
        missing = [name for name in REQUIRED_PRODUCTION_SECRETS if not values.get(name)]
        if missing:
            missing_env_names = ", ".join(SECRET_ENV_NAMES[name] for name in missing)
            raise RuntimeError(f"FATAL: Missing required production secrets in AWS Secrets Manager: {missing_env_names}")
        return {name: values.get(name, "") for name in SECRET_ENV_NAMES}

    return values


class Settings(BaseSettings):
    database_url: str = "postgresql://caregist:caregist_dev@localhost:5432/caregist"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_master_key: str = ""
    cors_origins: str = "http://localhost:3000"
    query_timeout_ms: int = 10000
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_alerts_pro: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_pro_seat: str = ""
    stripe_price_business: str = ""
    stripe_price_enterprise: str = ""
    stripe_price_profile_enhanced: str = ""
    stripe_price_profile_premium: str = ""
    stripe_price_profile_sponsored: str = ""
    default_page_size: int = 20
    app_url: str = "http://localhost:3000"
    resend_api_key: str = ""
    enquiry_from_email: str = ""
    sentry_dsn: str = ""
    support_platform_url: str = ""
    caregist_to_support_token: str = ""
    support_internal_token: str = ""
    # AES-GCM key for webhook secret encryption. Must be 32 bytes, base64-encoded.
    # If unset, webhook secrets are stored plaintext (dev/legacy mode).
    webhook_secret_key: str = ""
    # Optional Redis URL for shared burst rate limiting across workers.
    # When unset, burst limiting falls back to the process-local in-memory dict.
    redis_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def validate_production(self) -> None:
        validate_cors_origins(self.cors_origins, production="localhost" not in self.database_url)

        if "pytest" in sys.modules:
            return

        if not self.api_master_key:
            raise RuntimeError("FATAL: API_MASTER_KEY is required.")
        if not self.support_internal_token:
            raise RuntimeError("FATAL: SUPPORT_INTERNAL_TOKEN is required.")

        # Stripe environment guard: reject live keys in dev/test
        is_localhost = self.database_url == "postgresql://caregist:caregist_dev@localhost:5432/caregist"
        if self.stripe_secret_key.startswith("sk_live_") and is_localhost:
            raise RuntimeError(
                "FATAL: Live Stripe secret key (sk_live_) detected in local development environment. "
                "Use test credentials (sk_test_) for development. "
                "Live keys are only for production deployments."
            )


settings = Settings(**load_application_secrets())
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
        "exports_per_day": 3,
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
    "alerts-pro": {
        "rate": 5,
        "rate_window_seconds": 1,
        "daily": 200,
        "rolling_7d": 1400,
        "monthly": 5000,
        "page_size": 10,
        "fields": "standard",
        "nearby": False,
        "export": 500,
        "exports_per_day": 5,
        "compare": 3,
        "webhooks": False,
        "monitors": 50,
        "feed_rows": 0,
        "saved_filters": 0,
        "feed_digests": 0,
        "feed_api": False,
        "included_users": 1,
        "base_price_gbp": 49,
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
        "exports_per_day": 10,
        "compare": 3,
        "webhooks": False,
        "monitors": 15,
        "feed_rows": 25,
        "saved_filters": 3,
        "feed_digests": 1,
        "feed_api": True,
        "included_users": 1,
        "base_price_gbp": 99,
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
        "exports_per_day": 50,
        "compare": 5,
        "webhooks": False,
        "monitors": 100,
        "feed_rows": 50,
        "saved_filters": 20,
        "feed_digests": 10,
        "feed_api": True,
        "included_users": 3,
        "base_price_gbp": 199,
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
        "exports_per_day": 100,
        "compare": 10,
        "webhooks": True,
        "monitors": 500,
        "feed_rows": 100,
        "saved_filters": 100,
        "feed_digests": 100,
        "feed_api": True,
        "included_users": 10,
        "base_price_gbp": 499,
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
        "exports_per_day": 500,
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
        "exports_per_day": 99999,
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
