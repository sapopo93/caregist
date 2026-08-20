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
