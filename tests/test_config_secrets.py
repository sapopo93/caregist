"""Tests for application secret resolution."""

import pytest

from api.config import Settings, _normalize_secret_payload, load_application_secrets, validate_cors_origins


class FakeSecretLoader:
    payload = {}

    def __init__(self, secret_id, region_name=None):
        self.secret_id = secret_id
        self.region_name = region_name

    def load(self):
        return _normalize_secret_payload(self.payload)


def test_successful_secret_resolution_from_aws():
    FakeSecretLoader.payload = {
        "database_url": "postgresql://prod",
        "api_master_key": "master",
        "support_internal_token": "support",
        "stripe_secret_key": "sk_live_123",
        "stripe_webhook_secret": "whsec_123",
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
    assert secrets["stripe_price_profile_premium"] == "price_profile_premium"
    assert secrets["stripe_price_profile_sponsored"] == "price_profile_sponsored"
    assert secrets["stripe_price_pro_seat"] == "price_seat"


def test_missing_required_secret_in_production_fails_startup():
    FakeSecretLoader.payload = {
        "database_url": "postgresql://prod",
        "api_master_key": "master",
        "support_internal_token": "support",
        "stripe_secret_key": "sk_live_123",
    }

    with pytest.raises(RuntimeError, match="STRIPE_WEBHOOK_SECRET"):
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


def test_valid_explicit_cors_origins_pass():
    validate_cors_origins("https://caregist.co.uk, https://app.caregist.co.uk", production=True)
    validate_cors_origins("http://localhost:3000", production=False)

    Settings(
        database_url="postgresql://prod",
        api_master_key="master",
        support_internal_token="support",
        cors_origins="https://caregist.co.uk,https://app.caregist.co.uk",
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
