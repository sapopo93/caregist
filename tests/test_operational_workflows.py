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


def test_ci_uses_real_worker_dependencies_non_superuser_rls_and_image_scans():
    workflow, source = _workflow("ci.yml")

    backend_steps = workflow["jobs"]["backend"]["steps"]
    backend_install = next(
        step for step in backend_steps if step.get("name") == "Install backend dependencies"
    )
    assert "requirements-worker.txt" in backend_install["run"]
    assert "--no-deps --require-hashes -r requirements-worker-model.txt" in backend_install["run"]

    migration_steps = workflow["jobs"]["migrations"]["steps"]
    role_step = next(
        step for step in migration_steps if step.get("name") == "Create non-superuser integration role"
    )
    assert "NOCREATEDB NOSUPERUSER NOBYPASSRLS" in role_step["run"]
    replay_step = next(
        step
        for step in migration_steps
        if step.get("name") == "Replay init.sql + every migration, assert invariants"
    )
    assert "caregist_test" in replay_step["env"]["CAREGIST_TEST_DATABASE_URL"]
    assert "caregist:caregist" in replay_step["env"]["CAREGIST_TEST_ADMIN_DATABASE_URL"]
    assert "ffmpeg" in source

    scan_steps = workflow["jobs"]["container-scan"]["steps"]
    scans = [step for step in scan_steps if step.get("name", "").startswith("Scan ")]
    assert {step["with"]["image-ref"] for step in scans} == {
        "caregist-api:ci",
        "caregist-worker:ci",
    }
    assert all(step["with"]["exit-code"] == "1" for step in scans)
    assert all(step["with"]["ignore-unfixed"] == "false" for step in scans)
    assert all(step["with"]["severity"] == "HIGH,CRITICAL" for step in scans)
    assert all(
        step["uses"]
        == "aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25"
        for step in scans
    )

    api_dockerfile = Path("Dockerfile").read_text()
    worker_dockerfile = Path("Dockerfile.worker").read_text()
    assert "python:3.12-alpine@sha256:" in api_dockerfile
    assert "ubuntu:24.04@sha256:" in worker_dockerfile
    assert "python3-venv" in worker_dockerfile

    model_requirement = Path("requirements-worker-model.txt").read_text(encoding="utf-8")
    assert "--hash=sha256:1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85" in (
        model_requirement
    )
    assert "requirements-worker-model.txt" in Path("Dockerfile.worker").read_text()
    assert "--no-deps --require-hashes -r requirements-worker-model.txt" in (
        Path("Dockerfile.worker").read_text()
    )


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
