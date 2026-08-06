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


def test_provider_sitemap_accepts_exact_fail_closed_response_for_empty_preview(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(503, {"content-type": "text/plain"}, "Provider sitemap index unavailable"),
    )

    verifier.verify_provider_sitemap(active_location_count=0)


def test_provider_sitemap_rejects_503_when_provider_data_exists(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(503, {"x-vercel-id": "iad1::abc"}, "Provider sitemap index unavailable"),
    )

    with pytest.raises(verifier.SmokeFailure, match="provider sitemap failed"):
        verifier.verify_provider_sitemap(active_location_count=1)


def test_provider_sitemap_rejects_unexpected_empty_preview_failure(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(503, {"x-vercel-id": "iad1::abc"}, "Database error"),
    )

    with pytest.raises(verifier.SmokeFailure, match="expected fail-closed sitemap response"):
        verifier.verify_provider_sitemap(active_location_count=0)


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
            json.dumps(
                {
                    "status": "stale",
                    "release": {"git_sha": "a" * 40},
                    "source": {"activeLocationCount": 0},
                }
            ),
        ),
    )

    assert verifier.verify_backend_binding() == 0


def test_search_accepts_explicit_zero_result_state_for_empty_preview(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(200, {"content-type": "text/html"}, "No providers matched this search."),
    )

    verifier.verify_search(active_location_count=0)


def test_search_rejects_zero_result_state_when_provider_data_exists(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(200, {"content-type": "text/html"}, "No providers matched this search."),
    )

    with pytest.raises(verifier.SmokeFailure, match="empty result set"):
        verifier.verify_search(active_location_count=1)


def test_provider_page_accepts_404_without_stale_content_for_empty_preview(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(404, {"content-type": "text/html"}, "Not found"),
    )

    verifier.verify_provider_page(active_location_count=0)


def test_provider_page_rejects_stale_content_for_empty_preview(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(404, {"content-type": "text/html"}, "London Care (East London)"),
    )

    with pytest.raises(verifier.SmokeFailure, match="stale provider data"):
        verifier.verify_provider_page(active_location_count=0)


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
