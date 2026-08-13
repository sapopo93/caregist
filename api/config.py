"""Application configuration via environment variables."""

from __future__ import annotations

import base64
import ipaddress
import json
import os
import sys
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic_settings import BaseSettings


AWS_SECRET_ID_ENV = "AWS_SECRETS_MANAGER_SECRET_ID"
AWS_REGION_ENV = "AWS_REGION"
CAREGIST_PREVIEW_DATABASE_URL_ENV = "CAREGIST_PREVIEW_DATABASE_URL"

SECRET_ENV_NAMES = {
    "database_url": "DATABASE_URL",
    "api_master_key": "API_MASTER_KEY",
    "api_master_key_previous": "API_MASTER_KEY_PREVIOUS",
    "stripe_secret_key": "STRIPE_SECRET_KEY",
    "stripe_webhook_secret": "STRIPE_WEBHOOK_SECRET",
    "stripe_price_alerts_pro": "STRIPE_PRICE_ALERTS_PRO",
    "stripe_price_starter": "STRIPE_PRICE_STARTER",
    "stripe_price_pro": "STRIPE_PRICE_PRO",
    "stripe_price_pro_seat": "STRIPE_PRICE_PRO_SEAT",
    "stripe_price_business": "STRIPE_PRICE_BUSINESS",
    "stripe_price_full_dataset": "STRIPE_PRICE_FULL_DATASET",
    "stripe_price_enterprise": "STRIPE_PRICE_ENTERPRISE",
    "stripe_price_profile_enhanced": "STRIPE_PRICE_PROFILE_ENHANCED",
    "stripe_price_profile_premium": "STRIPE_PRICE_PROFILE_PREMIUM",
    "stripe_price_profile_sponsored": "STRIPE_PRICE_PROFILE_SPONSORED",
    "stripe_price_radar_regional": "STRIPE_PRICE_RADAR_REGIONAL",
    "stripe_price_radar_national": "STRIPE_PRICE_RADAR_NATIONAL",
    "stripe_price_intelligence_feed": "STRIPE_PRICE_INTELLIGENCE_FEED",
    "resend_api_key": "RESEND_API_KEY",
    "resend_webhook_secret": "RESEND_WEBHOOK_SECRET",
    "caregist_to_support_token": "CAREGIST_TO_SUPPORT_TOKEN",
    "support_internal_token": "SUPPORT_INTERNAL_TOKEN",
    "hermes_internal_token": "HERMES_INTERNAL_TOKEN",
    "webhook_secret_key": "WEBHOOK_SECRET_KEY",
    "redis_url": "REDIS_URL",
    "cron_secret": "CRON_SECRET",
    "twilio_account_sid": "TWILIO_ACCOUNT_SID",
    "twilio_api_key_sid": "TWILIO_API_KEY_SID",
    "twilio_api_key_secret": "TWILIO_API_KEY_SECRET",
    "twilio_auth_token": "TWILIO_AUTH_TOKEN",
    "crm_recording_s3_access_key_id": "CRM_RECORDING_S3_ACCESS_KEY_ID",
    "crm_recording_s3_secret_access_key": "CRM_RECORDING_S3_SECRET_ACCESS_KEY",
    "crm_screening_hash_key": "CRM_SCREENING_HASH_KEY",
    "crm_tpscheck_api_key": "CRM_TPSCHECK_API_KEY",
    "crm_ai_api_key": "CRM_AI_API_KEY",
    "crm_ai_pseudonym_key": "CRM_AI_PSEUDONYM_KEY",
}
SECRET_ENV_ALIASES = {
    "api_master_key": ("API_KEY",),
    "stripe_price_alerts_pro": ("STRIPE_PRICE_ALERTS_PRO_MONTHLY",),
    "stripe_price_starter": ("STRIPE_PRICE_DATA_STARTER_MONTHLY",),
    "stripe_price_pro": ("STRIPE_PRICE_DATA_PRO_MONTHLY",),
    "stripe_price_business": ("STRIPE_PRICE_DATA_BUSINESS_MONTHLY",),
    "stripe_price_profile_enhanced": ("STRIPE_PRICE_PROVIDER_ENHANCED_LISTING_MONTHLY",),
    "stripe_price_profile_premium": ("STRIPE_PRICE_PROVIDER_PRO_LISTING_MONTHLY",),
    "stripe_price_profile_sponsored": ("STRIPE_PRICE_SPONSORED_LISTING_MONTHLY",),
}


def runtime_requires_production_secrets(
    database_url: str,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether startup must enforce production-only secret gates.

    Vercel previews are protected, non-production environments and may use a
    preview database without live billing or outbound credentials. Production
    remains fail-closed even if its database URL is misconfigured.
    """
    env = environ or os.environ
    vercel_env = env.get("VERCEL_ENV", "").lower()
    if vercel_env == "production":
        return True
    if vercel_env in {"preview", "development"}:
        return False
    return "localhost" not in database_url


REQUIRED_PUBLIC_STRIPE_PRICE_FIELDS = (
    "stripe_price_alerts_pro",
    "stripe_price_starter",
    "stripe_price_pro",
    "stripe_price_pro_seat",
    "stripe_price_business",
    "stripe_price_full_dataset",
    "stripe_price_profile_enhanced",
    "stripe_price_profile_sponsored",
    "stripe_price_radar_regional",
    "stripe_price_radar_national",
    "stripe_price_intelligence_feed",
)


REQUIRED_PRODUCTION_SECRETS = (
    "database_url",
    "api_master_key",
    "support_internal_token",
    "stripe_secret_key",
    "stripe_webhook_secret",
    "webhook_secret_key",
    "redis_url",
)


def validate_public_stripe_price_ids(values: Mapping[str, Any]) -> None:
    configured = {
        field: str(values.get(field) or "").strip()
        for field in REQUIRED_PUBLIC_STRIPE_PRICE_FIELDS
    }
    malformed = [field for field, value in configured.items() if value and not value.startswith("price_")]
    if malformed:
        names = ", ".join(SECRET_ENV_NAMES[field] for field in malformed)
        raise RuntimeError(f"FATAL: Stripe Price IDs must start with 'price_': {names}")
    reverse: dict[str, list[str]] = {}
    for field, value in configured.items():
        if value:
            reverse.setdefault(value, []).append(field)
    duplicates = [fields for fields in reverse.values() if len(fields) > 1]
    if duplicates:
        names = ", ".join(
            "/".join(SECRET_ENV_NAMES[field] for field in fields)
            for fields in duplicates
        )
        raise RuntimeError(f"FATAL: Public Stripe plans must use unique Price IDs: {names}")


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


def redis_required_in_production(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether production must have shared Redis configured.

    Vercel can use the existing durable database quota path when Redis is not
    attached; its process-local limiter still protects short burst windows.
    """
    env = environ or os.environ
    return env.get("VERCEL") != "1" and not env.get("VERCEL_ENV")


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


def validate_app_url(app_url: str, *, production: bool) -> None:
    """Require a public HTTPS application origin for production billing redirects."""
    if not production:
        return

    parsed = urlparse(app_url.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(
            "FATAL: APP_URL must be a public HTTPS origin without a path, query, or credentials in production."
        )

    if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
        raise RuntimeError("FATAL: APP_URL must not use a local hostname in production.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname:
            raise RuntimeError("FATAL: APP_URL must use a public hostname in production.")
    else:
        if not address.is_global:
            raise RuntimeError("FATAL: APP_URL must not use a local or private address in production.")


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
    is_vercel = env.get("VERCEL") == "1" or bool(env.get("VERCEL_ENV"))
    is_vercel_production = env.get("VERCEL_ENV", "").lower() == "production"
    requires_production_secrets = is_production and (not is_vercel or is_vercel_production)
    secret_id = env.get(AWS_SECRET_ID_ENV)

    if not secret_id and requires_production_secrets and not is_vercel:
        raise RuntimeError(f"FATAL: {AWS_SECRET_ID_ENV} must be set in production.")

    values: dict[str, str] = {}
    if not is_production:
        values.update(_load_dev_dotenv_secrets(dotenv_path))
        values.update(_load_dev_env_secrets(env))
    elif is_vercel:
        # Vercel injects environment values directly into each service. Preview
        # deployments may intentionally omit live billing/outbound credentials;
        # those features then fail closed at their own API boundary.
        values.update(_load_dev_env_secrets(env))
        if env.get("VERCEL_ENV", "").lower() == "preview" and env.get(CAREGIST_PREVIEW_DATABASE_URL_ENV):
            # A separately provisioned preview resource must take precedence
            # over the legacy project-wide DATABASE_URL. The prefixed variable
            # can be connected to Preview only and is ignored in production.
            values["database_url"] = env[CAREGIST_PREVIEW_DATABASE_URL_ENV]
        elif env.get("PROD_DATABASE_URL"):
            values["database_url"] = env["PROD_DATABASE_URL"]
    # Vercel is the authoritative runtime now. Ignore the retired AWS secret
    # identifier if it still exists in project metadata; trying to resolve it
    # would make every serverless invocation fail before the app can start.
    if secret_id and not is_vercel:
        loader = secret_loader_cls(secret_id, env.get(AWS_REGION_ENV))
        values.update(loader.load())

    if requires_production_secrets:
        required_secrets = REQUIRED_PRODUCTION_SECRETS
        if is_vercel:
            # Quotas already use the durable DB fallback when Redis is absent.
            # Redis remains recommended, but must not prevent a Vercel function
            # from starting before a managed Redis integration is attached.
            required_secrets = tuple(name for name in required_secrets if name != "redis_url")
        missing = [name for name in required_secrets if not values.get(name)]
        if missing:
            missing_env_names = ", ".join(SECRET_ENV_NAMES[name] for name in missing)
            source = "Vercel environment" if is_vercel else "AWS Secrets Manager"
            raise RuntimeError(f"FATAL: Missing required production secrets in {source}: {missing_env_names}")
        validate_public_stripe_price_ids(values)
        return {name: values.get(name, "") for name in SECRET_ENV_NAMES}

    return values


class Settings(BaseSettings):
    database_url: str = "postgresql://caregist:caregist_dev@localhost:5432/caregist"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_master_key: str = ""
    # Optional comma-separated additional master keys, valid during a rotation
    # window so a new key can be deployed before the old one is revoked (F-18).
    api_master_key_previous: str = ""

    def master_keys(self) -> tuple[str, ...]:
        """All currently-valid master keys (primary + rotation overlap)."""
        keys = [self.api_master_key]
        keys.extend(part.strip() for part in self.api_master_key_previous.split(",") if part.strip())
        return tuple(key for key in keys if key)
    cors_origins: str = "http://localhost:3000"
    query_timeout_ms: int = 10000
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_alerts_pro: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_pro_seat: str = ""
    stripe_price_business: str = ""
    stripe_price_full_dataset: str = ""
    stripe_price_enterprise: str = ""
    stripe_price_profile_enhanced: str = ""
    stripe_price_profile_premium: str = ""
    stripe_price_profile_sponsored: str = ""
    # New catalogue. These remain optional until the corresponding readiness
    # gate is enabled; legacy price IDs stay loadable for subscription replay.
    stripe_price_radar_regional: str = ""
    stripe_price_radar_national: str = ""
    stripe_price_intelligence_feed: str = ""
    # Exact solicitor-approved B2B terms version accepted at paid checkout.
    # Empty means no self-service checkout can proceed even if its feature flag is enabled.
    b2b_terms_version: str = ""
    b2b_terms_sha256: str = ""
    b2b_evidence_hash_key: str = ""
    # Exact approved digital-content terms accepted in Stripe Checkout.
    digital_content_terms_version: str = ""
    digital_content_terms_sha256: str = ""
    default_page_size: int = 20
    app_url: str = "http://localhost:3000"
    resend_api_key: str = ""
    enquiry_from_email: str = ""
    sentry_dsn: str = ""
    support_platform_url: str = ""
    caregist_to_support_token: str = ""
    support_internal_token: str = ""
    # Optional separate token for Hermes. When unset, Hermes cannot authenticate
    # as its own actor and must not share the support-platform token.
    hermes_internal_token: str = ""
    # AES-GCM key for webhook secret encryption. Must be 32 bytes, base64-encoded.
    # If unset, webhook secrets are stored plaintext (dev/legacy mode).
    webhook_secret_key: str = ""
    # Optional Redis URL for shared burst rate limiting across workers.
    # When unset, burst limiting falls back to the process-local in-memory dict.
    redis_url: str = ""
    # Vercel Cron sends this value as an Authorization bearer token.
    cron_secret: str = ""
    # Human Gate control: provider claims remain disabled until identity,
    # authority, moderation, privacy, and operational approvals are recorded.
    provider_claims_enabled: bool = False
    # Personal-data intake and user-controlled remote media remain fail-closed
    # until the associated Human Gate privacy/moderation decisions are approved.
    enquiries_enabled: bool = False
    review_submissions_enabled: bool = False
    remote_provider_media_enabled: bool = False
    # Commercial mutations remain disabled until Human Gate 1 plus the
    # applicable finance/legal approvals are recorded. Stripe webhook intake
    # remains available so already-created state can still be reconciled.
    billing_checkout_enabled: bool = False
    outbound_communications_enabled: bool = False
    monitoring_activation_enabled: bool = False
    outbound_delivery_enabled: bool = False
    directory_export_delivery_enabled: bool = False
    full_dataset_checkout_enabled: bool = False
    review_publication_enabled: bool = False
    # Independent signal-intelligence kill switches. Defaults are deliberately
    # fail-closed; workflows opt collectors into shadow mode explicitly.
    radar_checkout_enabled: bool = False
    cqc_location_index_poll_enabled: bool = False
    cqc_report_poll_enabled: bool = False
    radar_explanations_enabled: bool = False
    radar_delivery_enabled: bool = False
    # CRM is an isolated internal workspace. Calling needs both this CRM gate
    # and the global outbound-communications gate so it cannot be enabled by a
    # partial deployment.
    crm_enabled: bool = False
    crm_calling_enabled: bool = False
    crm_pilot_mode: bool = True
    crm_recording_enabled: bool = False
    crm_recording_retention_days: int = 30
    crm_recording_notice_version: str = ""
    crm_recording_s3_endpoint_url: str = ""
    crm_recording_s3_region: str = "auto"
    crm_recording_s3_bucket: str = ""
    crm_recording_s3_access_key_id: str = ""
    crm_recording_s3_secret_access_key: str = ""
    crm_email_campaigns_enabled: bool = False
    crm_email_sender_postal_address: str = ""
    crm_screening_hash_key: str = ""
    crm_tps_automation_enabled: bool = False
    crm_tpscheck_api_key: str = ""
    crm_tpscheck_base_url: str = "https://api.tpscheck.uk"
    # Text messaging is deliberately absent from the UK CRM. South African
    # messaging will be implemented as a separate regional capability.
    crm_uk_sms_enabled: bool = False
    crm_ai_enabled: bool = False
    # Transcription runs only in the separate local worker. Model loading in a
    # serverless request would make retention and availability depend on a web
    # timeout, and remote transcription would expose unredacted call audio.
    crm_transcription_model: str = "small.en"
    crm_transcription_device: str = "cpu"
    crm_transcription_compute_type: str = "int8"
    crm_transcription_cpu_threads: int = 4
    crm_transcription_timeout_seconds: int = 900
    crm_ai_base_url: str = "https://api.deepseek.com/v1"
    crm_ai_api_key: str = ""
    crm_ai_model: str = "deepseek-v4-flash"
    crm_ai_pseudonym_key: str = ""
    crm_ai_monthly_cap_usd: Decimal = Decimal("10.00")
    # Current DeepSeek V4 Flash cache-miss prices. These are configurable so a
    # price change can fail closed without a code release.
    crm_ai_input_price_usd_per_million: Decimal = Decimal("0.14")
    crm_ai_cache_hit_price_usd_per_million: Decimal = Decimal("0.0028")
    crm_ai_output_price_usd_per_million: Decimal = Decimal("0.28")
    resend_webhook_secret: str = ""
    crm_allowed_test_numbers: str = ""
    twilio_account_sid: str = ""
    twilio_api_key_sid: str = ""
    twilio_api_key_secret: str = ""
    twilio_auth_token: str = ""
    twilio_twiml_app_sid: str = ""
    twilio_phone_number: str = ""
    twilio_region: str = "ie1"
    twilio_edge: str = "dublin"
    twilio_webhook_base_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def validate_production(self) -> None:
        production = runtime_requires_production_secrets(self.database_url)
        validate_cors_origins(self.cors_origins, production=production)
        validate_app_url(self.app_url, production=production)

        # CRM safety gates are environment-independent invariants. Keep them
        # active in tests and previews so a partial configuration cannot be
        # promoted into a callable deployment.
        if self.crm_recording_retention_days != 30:
            raise RuntimeError("FATAL: CRM recording retention must match the approved 30-day policy.")
        if self.crm_uk_sms_enabled:
            raise RuntimeError("FATAL: UK SMS is outside the approved CareGist CRM scope.")
        if self.crm_tps_automation_enabled:
            if not self.crm_enabled:
                raise RuntimeError("FATAL: TPS automation requires CRM_ENABLED.")
            if len(self.crm_screening_hash_key) < 32:
                raise RuntimeError(
                    "FATAL: TPS automation requires CRM_SCREENING_HASH_KEY with at least 32 characters."
                )
            if not self.crm_tpscheck_api_key:
                raise RuntimeError("FATAL: TPS automation requires CRM_TPSCHECK_API_KEY.")
            tps_url = urlparse(self.crm_tpscheck_base_url)
            if (
                tps_url.scheme != "https"
                or tps_url.hostname != "api.tpscheck.uk"
                or tps_url.username
                or tps_url.password
                or tps_url.query
                or tps_url.fragment
                or tps_url.path.rstrip("/")
            ):
                raise RuntimeError(
                    "FATAL: CRM_TPSCHECK_BASE_URL must be the approved TPSCheck HTTPS origin."
                )
        if self.crm_recording_enabled:
            if not self.crm_calling_enabled:
                raise RuntimeError("FATAL: CRM recording requires CRM_CALLING_ENABLED.")
            required_recording = {
                "CRM_RECORDING_NOTICE_VERSION": self.crm_recording_notice_version,
                "CRM_RECORDING_S3_ENDPOINT_URL": self.crm_recording_s3_endpoint_url,
                "CRM_RECORDING_S3_BUCKET": self.crm_recording_s3_bucket,
                "CRM_RECORDING_S3_ACCESS_KEY_ID": self.crm_recording_s3_access_key_id,
                "CRM_RECORDING_S3_SECRET_ACCESS_KEY": self.crm_recording_s3_secret_access_key,
            }
            missing_recording = [name for name, value in required_recording.items() if not value]
            if missing_recording:
                raise RuntimeError(
                    "FATAL: CRM recording is enabled without approved notice and private storage: "
                    + ", ".join(missing_recording)
                )
        if self.crm_email_campaigns_enabled and (
            not self.crm_enabled
            or not self.outbound_communications_enabled
            or not self.resend_api_key
            or not self.resend_webhook_secret
            or not self.crm_email_sender_postal_address.strip()
        ):
            raise RuntimeError(
                "FATAL: CRM email campaigns require CRM_ENABLED, OUTBOUND_COMMUNICATIONS_ENABLED, "
                "RESEND_API_KEY, RESEND_WEBHOOK_SECRET, and CRM_EMAIL_SENDER_POSTAL_ADDRESS."
            )
        if self.crm_ai_enabled:
            required_ai = {
                "CRM_AI_API_KEY": self.crm_ai_api_key,
                "CRM_AI_PSEUDONYM_KEY": self.crm_ai_pseudonym_key,
            }
            missing_ai = [name for name, value in required_ai.items() if not value]
            if missing_ai:
                raise RuntimeError("FATAL: CRM AI is enabled without " + ", ".join(missing_ai) + ".")
            if not self.crm_recording_enabled:
                raise RuntimeError("FATAL: CRM AI requires CRM_RECORDING_ENABLED.")
            if len(self.crm_ai_pseudonym_key) < 32:
                raise RuntimeError("FATAL: CRM_AI_PSEUDONYM_KEY must contain at least 32 characters.")
            if (
                self.crm_transcription_model != "small.en"
                or self.crm_transcription_device != "cpu"
                or self.crm_transcription_compute_type != "int8"
            ):
                raise RuntimeError(
                    "FATAL: CRM transcription must use local small.en on CPU with int8."
                )
            if self.crm_ai_model != "deepseek-v4-flash":
                raise RuntimeError("FATAL: CRM routine AI must use deepseek-v4-flash.")
            ai_url = urlparse(self.crm_ai_base_url)
            if (
                ai_url.scheme != "https"
                or ai_url.hostname != "api.deepseek.com"
                or ai_url.username
                or ai_url.password
                or ai_url.query
                or ai_url.fragment
                or ai_url.path.rstrip("/") not in {"", "/v1"}
            ):
                raise RuntimeError(
                    "FATAL: CRM_AI_BASE_URL must be the approved HTTPS DeepSeek API origin."
                )
            if self.crm_ai_monthly_cap_usd <= 0:
                raise RuntimeError("FATAL: CRM_AI_MONTHLY_CAP_USD must be greater than zero.")
            if (
                self.crm_ai_input_price_usd_per_million <= 0
                or self.crm_ai_cache_hit_price_usd_per_million <= 0
                or self.crm_ai_output_price_usd_per_million <= 0
            ):
                raise RuntimeError("FATAL: CRM AI token prices must be greater than zero.")
        if self.crm_calling_enabled:
            if not self.crm_enabled or not self.outbound_communications_enabled:
                raise RuntimeError(
                    "FATAL: CRM calling requires CRM_ENABLED and OUTBOUND_COMMUNICATIONS_ENABLED."
                )
            required_twilio = {
                "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
                "TWILIO_API_KEY_SID": self.twilio_api_key_sid,
                "TWILIO_API_KEY_SECRET": self.twilio_api_key_secret,
                "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
                "TWILIO_TWIML_APP_SID": self.twilio_twiml_app_sid,
                "TWILIO_PHONE_NUMBER": self.twilio_phone_number,
                "TWILIO_WEBHOOK_BASE_URL": self.twilio_webhook_base_url,
            }
            if self.crm_pilot_mode:
                required_twilio["CRM_ALLOWED_TEST_NUMBERS"] = self.crm_allowed_test_numbers
            else:
                required_twilio["CRM_SCREENING_HASH_KEY"] = self.crm_screening_hash_key
            missing_twilio = [name for name, value in required_twilio.items() if not value]
            if missing_twilio:
                raise RuntimeError(
                    "FATAL: CRM calling is enabled without required settings: "
                    + ", ".join(missing_twilio)
                )
            if not self.crm_pilot_mode and len(self.crm_screening_hash_key) < 32:
                raise RuntimeError("FATAL: CRM_SCREENING_HASH_KEY must contain at least 32 characters.")

        if "pytest" in sys.modules:
            return

        if not production:
            return

        if not self.api_master_key:
            raise RuntimeError("FATAL: API_MASTER_KEY is required.")
        if not self.support_internal_token:
            raise RuntimeError("FATAL: SUPPORT_INTERNAL_TOKEN is required.")

        is_localhost = self.database_url == "postgresql://caregist:caregist_dev@localhost:5432/caregist"
        is_production_db = "localhost" not in self.database_url
        if is_production_db:
            if not self.webhook_secret_key:
                raise RuntimeError("FATAL: WEBHOOK_SECRET_KEY is required in production.")
            if not self.redis_url and redis_required_in_production():
                raise RuntimeError("FATAL: REDIS_URL is required in production.")

        # Stripe environment guard: reject live keys in dev/test
        if self.stripe_secret_key.startswith("sk_live_") and is_localhost:
            raise RuntimeError(
                "FATAL: Live Stripe secret key (sk_live_) detected in local development environment. "
                "Use test credentials (sk_test_) for development. "
                "Live keys are only for production deployments."
            )

        if self.radar_checkout_enabled:
            if not self.billing_checkout_enabled:
                raise RuntimeError(
                    "FATAL: RADAR_CHECKOUT_ENABLED requires BILLING_CHECKOUT_ENABLED."
                )
            required_checkout_values = {
                "STRIPE_PRICE_RADAR_REGIONAL": self.stripe_price_radar_regional,
                "STRIPE_PRICE_RADAR_NATIONAL": self.stripe_price_radar_national,
                "B2B_TERMS_VERSION": self.b2b_terms_version,
                "B2B_TERMS_SHA256": self.b2b_terms_sha256,
            }
            missing = [name for name, value in required_checkout_values.items() if not value]
            if missing:
                raise RuntimeError(
                    f"FATAL: Radar checkout is enabled without {', '.join(missing)}."
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
        "export": 0,
        "exports_per_day": 0,
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
        "next_tier": "radar-regional",
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
        "export": 0,
        "exports_per_day": 0,
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
    "radar-regional": {
        "rate": 25,
        "rate_window_seconds": 1,
        "daily": 2000,
        "rolling_7d": 14000,
        "monthly": 50000,
        "page_size": 100,
        "fields": "standard",
        "nearby": True,
        "export": 5000,
        "exports_per_day": 20,
        "compare": 5,
        "webhooks": False,
        "monitors": 100,
        "feed_rows": 100,
        "saved_filters": 10,
        "feed_digests": 10,
        "feed_api": False,
        "included_users": 2,
        "base_price_gbp": 299,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "region_limit": 1,
        "history_days": 90,
        "next_tier": "radar-national",
    },
    "radar-national": {
        "rate": 40,
        "rate_window_seconds": 1,
        "daily": 5000,
        "rolling_7d": 35000,
        "monthly": 100000,
        "page_size": 250,
        "fields": "standard",
        "nearby": True,
        "export": 25000,
        "exports_per_day": 50,
        "compare": 10,
        "webhooks": False,
        "monitors": 500,
        "feed_rows": 250,
        "saved_filters": 50,
        "feed_digests": 50,
        "feed_api": False,
        "included_users": 5,
        "base_price_gbp": 799,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "region_limit": None,
        "history_days": 365,
        "next_tier": "intelligence-feed",
    },
    "intelligence-feed": {
        "rate": 60,
        "rate_window_seconds": 1,
        "daily": 10000,
        "rolling_7d": 70000,
        "monthly": 250000,
        "page_size": 250,
        "fields": "full",
        "nearby": True,
        "export": 50000,
        "exports_per_day": 100,
        "compare": 10,
        "webhooks": True,
        "monitors": 1000,
        "feed_rows": 250,
        "saved_filters": 100,
        "feed_digests": 100,
        "feed_api": True,
        "included_users": 5,
        "base_price_gbp": 6000,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "region_limit": 1,
        "history_days": 365,
        "next_tier": "embedded-enterprise",
    },
    "embedded-enterprise": {
        "rate": 200,
        "rate_window_seconds": 1,
        "daily": 50000,
        "rolling_7d": 350000,
        "monthly": 1500000,
        "page_size": 500,
        "fields": "full",
        "nearby": True,
        "export": 100000,
        "exports_per_day": 500,
        "compare": 20,
        "webhooks": True,
        "monitors": 5000,
        "feed_rows": 500,
        "saved_filters": 500,
        "feed_digests": 500,
        "feed_api": True,
        "included_users": 10,
        "base_price_gbp": 0,
        "seat_price_gbp": 0,
        "extra_seat_min_tier": None,
        "region_limit": None,
        "history_days": 730,
        "next_tier": None,
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
    "specialisms", "number_of_beds", "data_completeness_score", "data_completeness_tier",
    "last_inspection_date", "inspection_report_url",
]

BASIC_FIELDS = [
    "id", "name", "slug", "type", "status", "town", "county", "postcode",
    "region", "local_authority", "overall_rating", "service_types",
    "specialisms", "number_of_beds", "data_completeness_score", "data_completeness_tier",
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
    "alerts-pro": 1,
    "starter": 2,
    "pro": 3,
    "business": 4,
    "radar-regional": 5,
    "radar-national": 6,
    "intelligence-feed": 7,
    "embedded-enterprise": 8,
    "enterprise": 8,
    "admin": 9,
}


def get_tier_config(tier: str) -> dict:
    """Get config for a tier, defaulting to free."""
    normalized = (tier or "free").lower()
    if normalized in TIERS:
        return TIERS[normalized]
    if normalized.startswith("enterprise") or normalized == "embedded-enterprise":
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
