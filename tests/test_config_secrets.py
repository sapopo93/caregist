"""Tests for application secret resolution."""

import pytest

from api.config import (
    Settings,
    _normalize_secret_payload,
    load_application_secrets,
    runtime_requires_production_secrets,
    validate_app_url,
    validate_cors_origins,
)


class FakeSecretLoader:
    payload = {}

    def __init__(self, secret_id, region_name=None):
        self.secret_id = secret_id
        self.region_name = region_name

    def load(self):
        return _normalize_secret_payload(self.payload)


PUBLIC_STRIPE_PRICE_FIELDS = {
    "stripe_price_alerts_pro": "price_alerts",
    "stripe_price_starter": "price_starter",
    "stripe_price_pro": "price_pro",
    "stripe_price_pro_seat": "price_seat",
    "stripe_price_business": "price_business",
    "stripe_price_profile_enhanced": "price_profile_enhanced",
    "stripe_price_profile_sponsored": "price_profile_sponsored",
}

PUBLIC_STRIPE_PRICE_ENV = {
    "STRIPE_PRICE_ALERTS_PRO": "price_alerts",
    "STRIPE_PRICE_STARTER": "price_starter",
    "STRIPE_PRICE_PRO": "price_pro",
    "STRIPE_PRICE_PRO_SEAT": "price_seat",
    "STRIPE_PRICE_BUSINESS": "price_business",
    "STRIPE_PRICE_PROFILE_ENHANCED": "price_profile_enhanced",
    "STRIPE_PRICE_PROFILE_SPONSORED": "price_profile_sponsored",
}


def test_successful_secret_resolution_from_aws():
    FakeSecretLoader.payload = {
        "database_url": "postgresql://prod",
        "api_master_key": "master",
        "support_internal_token": "support",
        "stripe_secret_key": "sk_live_123",
        "stripe_webhook_secret": "whsec_123",
        **PUBLIC_STRIPE_PRICE_FIELDS,
    }

    secrets = load_application_secrets(
        environ={
            "NODE_ENV": "production",
            "AWS_SECRETS_MANAGER_SECRET_ID": "caregist/prod/api",
            "AWS_REGION": "eu-west-2",
        },
        secret_loader_cls=FakeSecretLoader,
    )

    assert secrets["database_url"] == "postgresql://prod"
    assert secrets["api_master_key"] == "master"
    assert secrets["support_internal_token"] == "support"
    assert secrets["stripe_secret_key"] == "sk_live_123"
    assert secrets["stripe_webhook_secret"] == "whsec_123"


def test_secret_resolution_includes_stripe_price_aliases_from_aws():
    FakeSecretLoader.payload = {
        "DATABASE_URL": "postgresql://prod",
        "API_MASTER_KEY": "master",
        "SUPPORT_INTERNAL_TOKEN": "support",
        "STRIPE_SECRET_KEY": "sk_live_123",
        "STRIPE_WEBHOOK_SECRET": "whsec_123",
        "STRIPE_PRICE_ALERTS_PRO_MONTHLY": "price_alerts",
        "STRIPE_PRICE_DATA_STARTER_MONTHLY": "price_starter",
        "STRIPE_PRICE_DATA_PRO_MONTHLY": "price_pro",
        "STRIPE_PRICE_DATA_BUSINESS_MONTHLY": "price_business",
        "STRIPE_PRICE_PROVIDER_ENHANCED_LISTING_MONTHLY": "price_profile_enhanced",
        "STRIPE_PRICE_PROVIDER_PRO_LISTING_MONTHLY": "price_profile_premium",
        "STRIPE_PRICE_SPONSORED_LISTING_MONTHLY": "price_profile_sponsored",
        "STRIPE_PRICE_PRO_SEAT": "price_seat",
    }

    secrets = load_application_secrets(
        environ={
            "NODE_ENV": "production",
            "AWS_SECRETS_MANAGER_SECRET_ID": "caregist/prod/api",
        },
        secret_loader_cls=FakeSecretLoader,
    )

    assert secrets["stripe_price_alerts_pro"] == "price_alerts"
    assert secrets["stripe_price_starter"] == "price_starter"
    assert secrets["stripe_price_pro"] == "price_pro"
    assert secrets["stripe_price_business"] == "price_business"
    assert secrets["stripe_price_profile_enhanced"] == "price_profile_enhanced"
    assert secrets["stripe_price_profile_premium"] == "price_profile_premium"
    assert secrets["stripe_price_profile_sponsored"] == "price_profile_sponsored"
    assert secrets["stripe_price_pro_seat"] == "price_seat"


def test_missing_required_secret_in_production_fails_startup():
    FakeSecretLoader.payload = {
        "database_url": "postgresql://prod",
        "api_master_key": "master",
        "support_internal_token": "support",
        "stripe_secret_key": "sk_live_123",
        **PUBLIC_STRIPE_PRICE_FIELDS,
    }

    with pytest.raises(RuntimeError, match="STRIPE_WEBHOOK_SECRET"):
        load_application_secrets(
            environ={
                "NODE_ENV": "production",
                "AWS_SECRETS_MANAGER_SECRET_ID": "caregist/prod/api",
            },
            secret_loader_cls=FakeSecretLoader,
        )


def test_duplicate_public_stripe_price_ids_fail_production_startup():
    FakeSecretLoader.payload = {
        "database_url": "postgresql://prod",
        "api_master_key": "master",
        "support_internal_token": "support",
        "stripe_secret_key": "sk_live_123",
        "stripe_webhook_secret": "whsec_123",
        **PUBLIC_STRIPE_PRICE_FIELDS,
        "stripe_price_pro": "price_starter",
    }

    with pytest.raises(RuntimeError, match="unique Price IDs"):
        load_application_secrets(
            environ={
                "NODE_ENV": "production",
                "AWS_SECRETS_MANAGER_SECRET_ID": "caregist/prod/api",
            },
            secret_loader_cls=FakeSecretLoader,
        )


def test_malformed_public_stripe_price_id_fails_production_startup():
    FakeSecretLoader.payload = {
        "database_url": "postgresql://prod",
        "api_master_key": "master",
        "support_internal_token": "support",
        "stripe_secret_key": "sk_live_123",
        "stripe_webhook_secret": "whsec_123",
        **PUBLIC_STRIPE_PRICE_FIELDS,
        "stripe_price_pro": "prod_not_a_price",
    }

    with pytest.raises(RuntimeError, match="must start with 'price_'"):
        load_application_secrets(
            environ={
                "NODE_ENV": "production",
                "AWS_SECRETS_MANAGER_SECRET_ID": "caregist/prod/api",
            },
            secret_loader_cls=FakeSecretLoader,
        )


def test_dev_fallback_works_only_outside_production():
    dev_secrets = load_application_secrets(
        environ={
            "NODE_ENV": "development",
            "API_MASTER_KEY": "dev-master",
            "SUPPORT_INTERNAL_TOKEN": "dev-support",
        },
        dotenv_path="/tmp/caregist-missing-test-env",
        secret_loader_cls=FakeSecretLoader,
    )

    assert dev_secrets["api_master_key"] == "dev-master"
    assert dev_secrets["support_internal_token"] == "dev-support"

    with pytest.raises(RuntimeError, match="AWS_SECRETS_MANAGER_SECRET_ID"):
        load_application_secrets(
            environ={
                "NODE_ENV": "production",
                "API_MASTER_KEY": "prod-env-master",
                "SUPPORT_INTERNAL_TOKEN": "prod-env-support",
            },
            dotenv_path="/tmp/caregist-missing-test-env",
            secret_loader_cls=FakeSecretLoader,
        )


def test_api_key_alias_is_accepted_for_preview_identity():
    secrets = load_application_secrets(
        environ={
            "NODE_ENV": "development",
            "API_KEY": "preview-master",
        },
        dotenv_path="/tmp/caregist-missing-test-env",
        secret_loader_cls=FakeSecretLoader,
    )

    assert secrets["api_master_key"] == "preview-master"


def test_vercel_preview_does_not_require_live_production_secrets():
    assert runtime_requires_production_secrets(
        "postgresql://preview-db",
        {"VERCEL_ENV": "preview"},
    ) is False


def test_vercel_production_always_requires_production_secrets():
    assert runtime_requires_production_secrets(
        "postgresql://caregist:caregist_dev@localhost:5432/caregist",
        {"VERCEL_ENV": "production"},
    ) is True


def test_vercel_preview_loads_direct_env_without_live_billing_secrets():
    secrets = load_application_secrets(
        environ={
            "NODE_ENV": "production",
            "VERCEL": "1",
            "VERCEL_ENV": "preview",
            "DATABASE_URL": "postgresql://preview",
            "API_KEY": "preview-master",
        },
        secret_loader_cls=FakeSecretLoader,
    )

    assert secrets["database_url"] == "postgresql://preview"
    assert secrets["api_master_key"] == "preview-master"
    assert "stripe_secret_key" not in secrets


def test_vercel_preview_prefers_isolated_preview_database():
    secrets = load_application_secrets(
        environ={
            "NODE_ENV": "production",
            "VERCEL": "1",
            "VERCEL_ENV": "preview",
            "DATABASE_URL": "postgresql://legacy-preview",
            "CAREGIST_PREVIEW_DATABASE_URL": "postgresql://isolated-preview",
            "API_KEY": "preview-master",
        },
        secret_loader_cls=FakeSecretLoader,
    )

    assert secrets["database_url"] == "postgresql://isolated-preview"


def test_vercel_production_ignores_preview_database_override():
    secrets = load_application_secrets(
        environ={
            "NODE_ENV": "production",
            "VERCEL": "1",
            "VERCEL_ENV": "production",
            "DATABASE_URL": "postgresql://legacy",
            "PROD_DATABASE_URL": "postgresql://production",
            "CAREGIST_PREVIEW_DATABASE_URL": "postgresql://isolated-preview",
            "API_KEY": "production-master",
            "SUPPORT_INTERNAL_TOKEN": "support",
            "STRIPE_SECRET_KEY": "sk_live_123",
            "STRIPE_WEBHOOK_SECRET": "whsec_123",
            **PUBLIC_STRIPE_PRICE_ENV,
        },
        secret_loader_cls=FakeSecretLoader,
    )

    assert secrets["database_url"] == "postgresql://production"


def test_vercel_production_loads_direct_env_and_requires_all_secrets():
    secrets = load_application_secrets(
        environ={
            "NODE_ENV": "production",
            "VERCEL": "1",
            "VERCEL_ENV": "production",
            "DATABASE_URL": "postgresql://legacy",
            "PROD_DATABASE_URL": "postgresql://production",
            "API_KEY": "production-master",
            "SUPPORT_INTERNAL_TOKEN": "support",
            "STRIPE_SECRET_KEY": "sk_live_123",
            "STRIPE_WEBHOOK_SECRET": "whsec_123",
            **PUBLIC_STRIPE_PRICE_ENV,
        },
        secret_loader_cls=FakeSecretLoader,
    )

    assert secrets["database_url"] == "postgresql://production"
    assert secrets["api_master_key"] == "production-master"

    with pytest.raises(RuntimeError, match="STRIPE_WEBHOOK_SECRET"):
        load_application_secrets(
            environ={
                "NODE_ENV": "production",
                "VERCEL": "1",
                "VERCEL_ENV": "production",
                "DATABASE_URL": "postgresql://production",
                "API_KEY": "production-master",
                "SUPPORT_INTERNAL_TOKEN": "support",
                "STRIPE_SECRET_KEY": "sk_live_123",
                **PUBLIC_STRIPE_PRICE_ENV,
            },
            secret_loader_cls=FakeSecretLoader,
        )


@pytest.mark.parametrize("missing_env_name", sorted(PUBLIC_STRIPE_PRICE_ENV))
def test_vercel_production_fails_closed_when_a_public_checkout_price_is_missing(missing_env_name):
    environ = {
        "NODE_ENV": "production",
        "VERCEL": "1",
        "VERCEL_ENV": "production",
        "PROD_DATABASE_URL": "postgresql://production",
        "API_KEY": "production-master",
        "SUPPORT_INTERNAL_TOKEN": "support",
        "STRIPE_SECRET_KEY": "sk_live_123",
        "STRIPE_WEBHOOK_SECRET": "whsec_123",
        **PUBLIC_STRIPE_PRICE_ENV,
    }
    del environ[missing_env_name]

    with pytest.raises(RuntimeError, match=missing_env_name):
        load_application_secrets(
            environ=environ,
            secret_loader_cls=FakeSecretLoader,
        )


def test_valid_explicit_cors_origins_pass():
    validate_cors_origins("https://caregist.co.uk, https://app.caregist.co.uk", production=True)
    validate_cors_origins("http://localhost:3000", production=False)

    Settings(
        database_url="postgresql://prod",
        api_master_key="master",
        support_internal_token="support",
        cors_origins="https://caregist.co.uk,https://app.caregist.co.uk",
        app_url="https://caregist.co.uk",
    ).validate_production()


@pytest.mark.parametrize(
    "cors_origins",
    [
        "*",
        "https://caregist.co.uk,*",
        "https://*.caregist.co.uk",
        "caregist.co.uk",
        "https://caregist.co.uk/path",
        "javascript:alert(1)",
        "",
    ],
)
def test_wildcard_or_malformed_production_cors_config_fails(cors_origins):
    with pytest.raises(RuntimeError, match="CORS|Invalid CORS"):
        validate_cors_origins(cors_origins, production=True)


def test_wildcard_production_cors_config_fails_startup_validation():
    settings = Settings(
        database_url="postgresql://prod",
        api_master_key="master",
        support_internal_token="support",
        cors_origins="*",
    )

    with pytest.raises(RuntimeError, match="CORS wildcard"):
        settings.validate_production()


@pytest.mark.parametrize(
    "app_url",
    [
        "http://caregist.co.uk",
        "https://localhost:3000",
        "https://127.0.0.1",
        "https://10.0.0.5",
        "https://caregist.local",
        "https://caregist.co.uk/checkout",
        "https://caregist.co.uk?next=checkout",
        "https://caregist",
        "",
    ],
)
def test_non_public_production_app_url_fails(app_url):
    with pytest.raises(RuntimeError, match="APP_URL"):
        validate_app_url(app_url, production=True)


def test_public_https_production_app_url_passes():
    validate_app_url("https://caregist.co.uk", production=True)
    validate_app_url("https://www.caregist.co.uk/", production=True)


def test_local_development_app_url_remains_allowed():
    validate_app_url("http://localhost:3000", production=False)
