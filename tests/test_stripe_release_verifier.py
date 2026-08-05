"""Offline release checks must be deterministic and secret-safe."""

from __future__ import annotations

import json

from tools import verify_stripe_release as verifier


def valid_test_environment() -> dict[str, str]:
    values = {
        "STRIPE_SECRET_KEY": "sk_test_super_secret_value",
        "STRIPE_WEBHOOK_SECRET": "whsec_super_secret_value",
        "APP_URL": "https://caregist.example",
    }
    for index, name in enumerate(verifier.EXPECTED_MANIFEST["prices"], start=1):
        values[name] = f"price_offline_{index}"
    return values


def test_exact_repository_contract_passes_offline_verification():
    checks = verifier.run_checks(valid_test_environment(), mode="test")
    assert checks
    assert all(passed for _, passed, _ in checks)


def test_wrong_mode_duplicate_price_and_local_url_fail_closed():
    values = valid_test_environment()
    values["STRIPE_SECRET_KEY"] = "sk_live_wrong_mode"
    values["APP_URL"] = "https://localhost:3000"
    values["STRIPE_PRICE_PRO"] = values["STRIPE_PRICE_STARTER"]

    failed = {name for name, passed, _ in verifier.run_checks(values, mode="test") if not passed}

    assert {"STRIPE_SECRET_KEY", "APP_URL", "STRIPE_PRICE_IDS_UNIQUE"} <= failed


def test_modified_manifest_fails_exact_approved_amount_check(tmp_path):
    manifest = json.loads(verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    manifest["prices"]["STRIPE_PRICE_PRO"]["unit_amount"] = 1
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    checks = verifier.run_checks(valid_test_environment(), mode="test", manifest_path=manifest_path)

    assert ("APPROVED_PRICE_MANIFEST", False, "exact approved GBP monthly amounts") in checks


def test_cli_output_never_prints_environment_values(capsys):
    values = valid_test_environment()

    result = verifier.main(["--mode", "test"], environ=values)

    output = capsys.readouterr().out
    assert result == 0
    for value in values.values():
        assert value not in output
    assert "RESULT:" in output


def test_missing_environment_fails_without_exposing_values(capsys):
    result = verifier.main(["--mode", "test"], environ={})

    output = capsys.readouterr().out
    assert result == 1
    assert "FAIL STRIPE_SECRET_KEY" in output
    assert "FAIL STRIPE_WEBHOOK_SECRET" in output
    assert "FAIL APP_URL" in output


def test_webhook_coverage_requires_real_event_type_branches(tmp_path):
    billing_source = tmp_path / "billing.py"
    billing_source.write_text(
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/billing")
@router.post("/webhook")
async def stripe_webhook():
    """checkout.session.completed is only documentation, not a handled branch."""
    if event_type == "checkout.session.expired":
        pass
''',
        encoding="utf-8",
    )

    route_ok, events = verifier.inspect_billing_source(billing_source)

    assert route_ok is True
    assert events == {"checkout.session.expired"}
    assert "checkout.session.completed" not in events
