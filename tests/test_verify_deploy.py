from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import Mock

import pytest


def _load_verifier():
    path = Path(__file__).resolve().parents[1] / "tools" / "verify-deploy.py"
    spec = importlib.util.spec_from_file_location(f"caregist_verify_deploy_{uuid.uuid4().hex}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def verifier():
    return _load_verifier()


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
    verifier.EXPECTED_FRONTEND_GIT_SHA = "a" * 40
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(200, {"content-type": "application/json"}, json.dumps(_healthy_payload("b" * 40))),
    )

    with pytest.raises(verifier.SmokeFailure, match="did not match expected SHA"):
        verifier.verify_health()


def test_health_accepts_exact_deployed_sha(verifier, monkeypatch):
    verifier.EXPECTED_FRONTEND_GIT_SHA = "a" * 40
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(200, {"content-type": "application/json"}, json.dumps(_healthy_payload("a" * 40))),
    )

    verifier.verify_health()


def test_health_accepts_read_only_fallback_with_writes_fail_closed(verifier, monkeypatch):
    verifier.EXPECTED_FRONTEND_GIT_SHA = "a" * 40
    payload = {
        "status": "degraded",
        "release": {"gitSha": "a" * 40},
        "capabilities": {
            "operatingMode": "fallback",
            "readMode": "full-dataset-fallback",
            "writeMode": "unavailable",
            "notificationMode": "log-only",
            "databaseAvailable": False,
            "databaseReason": "not_configured",
        },
    }
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(
            200,
            {"content-type": "application/json"},
            json.dumps(payload),
        ),
    )

    assert verifier.verify_health() == "fallback"


def test_health_rejects_contradictory_fallback_capabilities(verifier, monkeypatch):
    payload = {
        "status": "ok",
        "release": {"gitSha": "a" * 40},
        "capabilities": {
            "operatingMode": "fallback",
            "readMode": "database",
            "writeMode": "database",
            "notificationMode": "email",
            "databaseAvailable": True,
            "databaseReason": None,
        },
    }
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(
            200,
            {"content-type": "application/json"},
            json.dumps(payload),
        ),
    )

    with pytest.raises(verifier.SmokeFailure, match="fallback status"):
        verifier.verify_health()


def test_main_skips_backend_only_paths_when_frontend_is_in_fallback_mode(verifier, monkeypatch):
    calls = []
    monkeypatch.setattr(verifier, "ATTEMPTS", 1)
    monkeypatch.setattr(verifier, "SKIP_BACKEND_PATHS", False)
    monkeypatch.setattr(verifier, "verify_health", lambda: "fallback")
    monkeypatch.setattr(verifier, "verify_data_status", lambda: calls.append("data-status"))
    monkeypatch.setattr(
        verifier,
        "verify_backend_binding",
        lambda: pytest.fail("fallback smoke must not claim to verify the unavailable backend"),
    )
    monkeypatch.setattr(
        verifier,
        "verify_provider_sitemap",
        lambda _count: pytest.fail("fallback smoke must not claim to verify backend sitemap"),
    )
    monkeypatch.setattr(verifier, "verify_search", lambda _count: calls.append("search"))
    monkeypatch.setattr(verifier, "verify_provider_page", lambda _count: calls.append("provider"))
    monkeypatch.setattr(
        verifier,
        "verify_export_requires_token",
        lambda: calls.append("export") or False,
    )

    assert verifier.main() == 0
    assert calls == ["data-status", "search", "provider", "export"]


def test_required_identity_verifies_backend_during_frontend_fallback(verifier, monkeypatch):
    calls = []
    verifier.REQUIRE_RELEASE_IDENTITY = True
    verifier.EXPECTED_FRONTEND_GIT_SHA = "a" * 40
    verifier.EXPECTED_BACKEND_GIT_SHA = "b" * 40
    verifier.SKIP_BACKEND_PATHS = False
    verifier.ATTEMPTS = 1
    monkeypatch.setattr(verifier, "verify_health", lambda: "fallback")
    monkeypatch.setattr(verifier, "verify_data_status", lambda: calls.append("data-status"))
    monkeypatch.setattr(
        verifier, "verify_backend_binding", lambda: calls.append("backend-binding") or 123
    )
    monkeypatch.setattr(
        verifier,
        "verify_provider_sitemap",
        lambda _count: pytest.fail("fallback must not claim backend sitemap availability"),
    )
    monkeypatch.setattr(verifier, "verify_search", lambda count: calls.append(("search", count)))
    monkeypatch.setattr(
        verifier, "verify_provider_page", lambda count: calls.append(("provider", count))
    )
    monkeypatch.setattr(verifier, "verify_export_requires_token", lambda: False)

    assert verifier.main() == 0
    assert calls == [
        "data-status",
        "backend-binding",
        ("search", None),
        ("provider", None),
    ]


def test_required_identity_propagates_backend_drift_during_fallback(verifier, monkeypatch):
    verifier.REQUIRE_RELEASE_IDENTITY = True
    verifier.EXPECTED_FRONTEND_GIT_SHA = "a" * 40
    verifier.EXPECTED_BACKEND_GIT_SHA = "b" * 40
    verifier.SKIP_BACKEND_PATHS = False
    verifier.ATTEMPTS = 1
    monkeypatch.setattr(verifier, "verify_health", lambda: "fallback")
    monkeypatch.setattr(verifier, "verify_data_status", lambda: None)
    monkeypatch.setattr(
        verifier,
        "verify_backend_binding",
        Mock(side_effect=verifier.SmokeFailure("backend Git SHA drift")),
    )

    assert verifier.main() == 1


def test_required_identity_rejects_backend_skip_before_requests(verifier, monkeypatch):
    verifier.REQUIRE_RELEASE_IDENTITY = True
    verifier.EXPECTED_FRONTEND_GIT_SHA = "a" * 40
    verifier.EXPECTED_BACKEND_GIT_SHA = "b" * 40
    verifier.SKIP_BACKEND_PATHS = True
    fetch = Mock()
    monkeypatch.setattr(verifier, "fetch", fetch)

    assert verifier.main() == 1
    fetch.assert_not_called()


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
    verifier.EXPECTED_BACKEND_GIT_SHA = "a" * 40
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
                    "totalSourceLocations": 0,
                }
            ),
        ),
    )

    assert verifier.verify_backend_binding() == 0


def test_split_frontend_and_backend_release_identities_are_verified(verifier, monkeypatch):
    verifier.EXPECTED_FRONTEND_GIT_SHA = "a" * 40
    verifier.EXPECTED_BACKEND_GIT_SHA = "b" * 40
    responses = {
        "/api/health/directory": verifier.Response(
            200,
            {"content-type": "application/json"},
            json.dumps(_healthy_payload("a" * 40)),
        ),
        "/api/v1/health/freshness": verifier.Response(
            503,
            {"content-type": "application/json"},
            json.dumps(
                {
                    "status": "partial",
                    "release": {"git_sha": "b" * 40},
                    "totalSourceLocations": None,
                }
            ),
        ),
    }
    monkeypatch.setattr(verifier, "fetch", responses.__getitem__)

    assert verifier.verify_health() == "database"
    assert verifier.verify_backend_binding() is None


def test_required_release_identity_fails_before_live_requests(verifier, monkeypatch):
    verifier.REQUIRE_RELEASE_IDENTITY = True
    verifier.EXPECTED_FRONTEND_GIT_SHA = ""
    verifier.EXPECTED_BACKEND_GIT_SHA = ""
    fetch = Mock()
    monkeypatch.setattr(verifier, "fetch", fetch)

    assert verifier.main() == 1
    fetch.assert_not_called()


def test_required_release_identity_rejects_malformed_pin_before_requests(verifier, monkeypatch):
    verifier.REQUIRE_RELEASE_IDENTITY = True
    verifier.EXPECTED_FRONTEND_GIT_SHA = "not-a-sha"
    verifier.EXPECTED_BACKEND_GIT_SHA = "b" * 40
    fetch = Mock()
    monkeypatch.setattr(verifier, "fetch", fetch)

    assert verifier.main() == 1
    fetch.assert_not_called()


def test_legacy_expected_sha_remains_compatible_for_preview_and_ci(monkeypatch):
    monkeypatch.setenv("CAREGIST_EXPECTED_GIT_SHA", "c" * 40)
    monkeypatch.delenv("CAREGIST_EXPECTED_FRONTEND_GIT_SHA", raising=False)
    monkeypatch.delenv("CAREGIST_EXPECTED_BACKEND_GIT_SHA", raising=False)

    loaded = _load_verifier()

    assert loaded.EXPECTED_FRONTEND_GIT_SHA == "c" * 40
    assert loaded.EXPECTED_BACKEND_GIT_SHA == "c" * 40


def test_backend_release_drift_is_rejected_independently(verifier, monkeypatch):
    verifier.EXPECTED_BACKEND_GIT_SHA = "a" * 40
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda _path: verifier.Response(
            503,
            {"content-type": "application/json"},
            json.dumps(
                {
                    "status": "partial",
                    "release": {"git_sha": "b" * 40},
                    "totalSourceLocations": None,
                }
            ),
        ),
    )

    with pytest.raises(verifier.SmokeFailure, match="backend Git SHA"):
        verifier.verify_backend_binding()


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


def test_lead_smoke_accepts_explicitly_retired_product(verifier, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "fetch",
        lambda *_args, **_kwargs: verifier.Response(
            410,
            {"content-type": "application/json"},
            '{"error":"Filtered lead-list exports are no longer offered. Use CareGist Radar for verified change events."}',
        ),
    )

    verifier.verify_lead_capture_and_export()
