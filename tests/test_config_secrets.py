"""Tests for application secret resolution."""

import pytest

from api.config import Settings, load_application_secrets, validate_cors_origins


class FakeSecretLoader:
    payload = {}

    def __init__(self, secret_id, region_name=None):
        self.secret_id = secret_id
        self.region_name = region_name

    def load(self):
        return self.payload


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
