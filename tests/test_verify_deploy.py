from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def verifier():
    path = Path(__file__).resolve().parents[1] / "tools" / "verify-deploy.py"
    spec = importlib.util.spec_from_file_location("caregist_verify_deploy", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _healthy_payload(sha: str) -> dict:
    return {
        "status": "ok",
        "release": {"gitSha": sha},
        "capabilities": {
            "operatingMode": "database",
            "readMode": "database",
            "writeMode": "database",
            "notificationMode": "email",
            "databaseAvailable": True,
            "databaseReason": None,
        },
    }


def test_health_rejects_deploy_drift(verifier, monkeypatch):
    verifier.EXPECTED_GIT_SHA = "a" * 40
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(200, {"content-type": "application/json"}, json.dumps(_healthy_payload("b" * 40))),
    )

    with pytest.raises(verifier.SmokeFailure, match="did not match tested SHA"):
        verifier.verify_health()


def test_health_accepts_exact_deployed_sha(verifier, monkeypatch):
    verifier.EXPECTED_GIT_SHA = "a" * 40
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(200, {"content-type": "application/json"}, json.dumps(_healthy_payload("a" * 40))),
    )

    verifier.verify_health()


def test_provider_sitemap_requires_xml_index(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(200, {"content-type": "application/xml"}, "<sitemapindex></sitemapindex>"),
    )

    verifier.verify_provider_sitemap()


def test_binding_failure_retains_request_diagnostics(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(503, {"x-vercel-id": "iad1::abc"}, "Provider sitemap index unavailable"),
    )

    with pytest.raises(verifier.SmokeFailure, match="iad1::abc.*Provider sitemap index unavailable"):
        verifier.verify_provider_sitemap()


def test_backend_binding_accepts_stale_signal_for_observability(verifier, monkeypatch):
    verifier.EXPECTED_GIT_SHA = "a" * 40
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(
            503,
            {"content-type": "application/json"},
            json.dumps({"status": "stale", "release": {"git_sha": "a" * 40}}),
        ),
    )

    verifier.verify_backend_binding()


def test_export_guard_accepts_governance_disabled_state(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(503, {"content-type": "application/json"}, "Export delivery is awaiting Human Gate approval."),
    )

    assert verifier.verify_export_requires_token() is False


def test_export_guard_reports_enabled_token_boundary(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(401, {"content-type": "application/json"}, "Export token required"),
    )

    assert verifier.verify_export_requires_token() is True


def test_lead_smoke_accepts_human_gate_redirect(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda *_args, **_kwargs: verifier.Response(
            303,
            {"location": "http://caregist.test/lead-list?hold=human-gate"},
            "",
        ),
    )

    verifier.verify_lead_capture_and_export()
