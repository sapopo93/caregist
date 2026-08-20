from pathlib import Path

import yaml


def _workflow(name: str) -> tuple[dict, str]:
    source = Path(".github/workflows", name).read_text(encoding="utf-8")
    return yaml.load(source, Loader=yaml.BaseLoader), source


def test_freshness_watchdog_uses_available_database_secret_and_module_execution():
    workflow, source = _workflow("freshness-watchdog.yml")
    step = workflow["jobs"]["freshness"]["steps"][-1]

    assert step["env"]["DATABASE_URL"] == "${{ secrets.DATABASE_URL }}"
    assert "python -m tools.check_new_registration_pipeline" in source
    assert "python tools/check_new_registration_pipeline.py" not in source
    assert step["env"]["WATCHDOG_NOTIFICATIONS_ENABLED"] == (
        "${{ vars.FRESHNESS_WATCHDOG_NOTIFICATIONS_ENABLED || 'false' }}"
    )
    assert 'case "$WATCHDOG_NOTIFICATIONS_ENABLED"' in source
    assert 'test -n "$RESEND_API_KEY"' in source
    assert 'test -n "$ENQUIRY_FROM_EMAIL"' in source


def test_production_smoke_requires_independent_release_identities():
    workflow, source = _workflow("production-smoke.yml")
    step = workflow["jobs"]["smoke"]["steps"][-1]
    env = step["env"]

    assert env["CAREGIST_EXPECTED_FRONTEND_GIT_SHA"] == (
        "${{ vars.CAREGIST_PRODUCTION_FRONTEND_SHA }}"
    )
    assert env["CAREGIST_EXPECTED_BACKEND_GIT_SHA"] == (
        "${{ vars.CAREGIST_PRODUCTION_BACKEND_SHA }}"
    )
    assert env["CAREGIST_REQUIRE_RELEASE_IDENTITY"] == "true"
    assert "CAREGIST_EXPECTED_GIT_SHA: ${{ github.sha }}" not in source


def test_radar_release_uses_available_database_secret_and_real_constraint():
    workflow, source = _workflow("radar-checkout-release.yml")
    steps = workflow["jobs"]["migrate"]["steps"]
    apply_step = next(step for step in steps if step.get("name") == "Apply forward-only production migrations")
    verify_step = next(step for step in steps if step.get("name") == "Verify Radar checkout schema")

    assert apply_step["env"]["PROD_DATABASE_URL"] == "${{ secrets.DATABASE_URL }}"
    assert verify_step["env"]["PROD_DATABASE_URL"] == "${{ secrets.DATABASE_URL }}"
    assert "secrets.PROD_DATABASE_URL" not in source
    assert "users_signup_purchase_intent_valid" in source
    assert "chk_users_signup_intent_type" not in source
    assert "conrelid = 'public.users'::regclass" in source
    assert "APPLY-RADAR-SCHEMA" in source
    assert "this does not enable checkout" in source
    assert "ENABLE-RADAR-CHECKOUT" not in source


def test_retired_render_contract_cannot_restore_legacy_checkout_catalogue():
    source = Path("render.yaml").read_text(encoding="utf-8")
    manifest = yaml.load(source, Loader=yaml.BaseLoader)
    web = next(service for service in manifest["services"] if service["type"] == "web")
    env = {entry["key"]: entry for entry in web["envVars"]}

    assert "RETIRED / NON-OPERATIVE" in source
    for current_name in (
        "STRIPE_PRODUCT_RADAR_REGIONAL",
        "STRIPE_PRICE_RADAR_REGIONAL",
        "STRIPE_PRODUCT_RADAR_NATIONAL",
        "STRIPE_PRICE_RADAR_NATIONAL",
        "STRIPE_PRODUCT_INTELLIGENCE_FEED",
        "STRIPE_PRICE_INTELLIGENCE_FEED",
    ):
        assert current_name in env
    for gate in (
        "BILLING_CHECKOUT_ENABLED",
        "RADAR_CHECKOUT_ENABLED",
        "RADAR_DELIVERY_ENABLED",
    ):
        assert env[gate]["value"] == "false"
    assert not any(
        retired in source
        for retired in (
            "STRIPE_PRICE_ALERTS_PRO",
            "STRIPE_PRICE_STARTER",
            "STRIPE_PRICE_PRO_SEAT",
            "STRIPE_PRICE_BUSINESS",
            "STRIPE_PRICE_PROFILE_ENHANCED",
            "STRIPE_PRICE_PROFILE_PREMIUM",
            "STRIPE_PRICE_PROFILE_SPONSORED",
        )
    )
