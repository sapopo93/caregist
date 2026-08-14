"""Offline release checks must be deterministic and secret-safe."""

from __future__ import annotations

import json

from tools import verify_stripe_release as verifier


def valid_test_environment(*, mode: str = "test") -> dict[str, str]:
    values = {
        "STRIPE_SECRET_KEY": f"sk_{mode}_super_secret_value",
        "STRIPE_WEBHOOK_SECRET": "whsec_super_secret_value",
        "APP_URL": "https://caregist.example",
    }
    manifest = json.loads(verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    values.update(verifier.deployment_identifiers(manifest, mode))
    return values


def test_exact_repository_contract_passes_offline_verification():
    checks = verifier.run_checks(valid_test_environment(), mode="test")
    assert checks
    assert all(passed for _, passed, _ in checks)


def test_wrong_mode_duplicate_price_and_local_url_fail_closed():
    values = valid_test_environment()
    values["STRIPE_SECRET_KEY"] = "sk_live_wrong_mode"
    values["APP_URL"] = "https://localhost:3000"
    values["STRIPE_PRICE_RADAR_NATIONAL"] = values["STRIPE_PRICE_RADAR_REGIONAL"]

    failed = {name for name, passed, _ in verifier.run_checks(values, mode="test") if not passed}

    assert {"STRIPE_SECRET_KEY", "APP_URL", "STRIPE_PRICE_IDS_UNIQUE"} <= failed


def test_modified_manifest_fails_exact_approved_catalogue_check(tmp_path):
    manifest = json.loads(verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    manifest["products"]["radar-national"]["unit_amount"] = 1
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    checks = verifier.run_checks(valid_test_environment(), mode="test", manifest_path=manifest_path)

    assert (
        "APPROVED_CATALOGUE_MANIFEST",
        False,
        "exact approved catalogue 2026-08 and checkout enabled",
    ) in checks


def test_live_mode_requires_live_catalogue_ids():
    checks = verifier.run_checks(valid_test_environment(mode="live"), mode="live")

    assert all(passed for _, passed, _ in checks)


def test_embedded_enterprise_has_no_saleable_price():
    manifest = json.loads(verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    embedded = manifest["products"]["embedded-enterprise"]

    assert embedded["environment_price"] is None
    assert embedded["stripe"]["test"]["price_id"] is None
    assert embedded["stripe"]["live"]["price_id"] is None
    assert embedded["stripe"]["test"]["archived_price_ids"]
    assert embedded["stripe"]["live"]["archived_price_ids"]


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
