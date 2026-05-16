"""Tests for external-dependency checks in /api/v1/health/readiness."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# App bootstrap — provide minimal stubs so importing health.py succeeds
# without a live DB or real settings object.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_imports(monkeypatch):
    """Stub heavy dependencies before the app is imported."""
    import sys

    # Stub api.config.settings
    fake_settings = MagicMock()
    fake_settings.sentry_dsn = "https://fake@sentry.io/123"
    fake_settings.resend_api_key = "re_test_fake"
    fake_settings.database_url = "postgresql://localhost/caregist"
    fake_settings.cors_origins = "http://localhost:3000"

    config_mod = MagicMock()
    config_mod.settings = fake_settings
    monkeypatch.setitem(sys.modules, "api.config", config_mod)

    # Stub api.database
    db_mod = MagicMock()
    db_mod.get_connection = AsyncMock()
    monkeypatch.setitem(sys.modules, "api.database", db_mod)

    # Stub api.services.pipeline_health
    ph_mod = MagicMock()
    ph_mod.get_pipeline_health = AsyncMock(
        return_value={"readiness_ok": True, "feed_fresh": True, "checks": {}}
    )
    monkeypatch.setitem(sys.modules, "api.services.pipeline_health", ph_mod)


# ---------------------------------------------------------------------------
# Helpers to build the ASGI app from the router under test
# ---------------------------------------------------------------------------


def _build_client(stripe_ok: bool = True, resend_ok: bool = True, sentry_dsn: str = "set"):
    """Import health router fresh (cache cleared) and wrap in a test app."""
    import importlib
    import sys

    # Remove cached module so patched imports are honoured fresh each call
    sys.modules.pop("api.routers.health", None)

    # Patch settings for this call
    sys.modules["api.config"].settings.sentry_dsn = sentry_dsn if sentry_dsn else ""
    sys.modules["api.config"].settings.resend_api_key = "re_test"

    from fastapi import FastAPI

    app = FastAPI()

    # Re-import after clearing cache
    health_mod = importlib.import_module("api.routers.health")
    # Reset the in-module cache
    health_mod._cache.clear()

    app.include_router(health_mod.router)

    # Patch stripe
    stripe_mock = MagicMock()
    if stripe_ok:
        stripe_mock.Customer.list.return_value = MagicMock()
    else:
        stripe_mock.Customer.list.side_effect = Exception("Stripe unreachable")
    health_mod.stripe = stripe_mock

    # Patch httpx for Resend
    resend_resp = MagicMock()
    resend_resp.status_code = 200 if resend_ok else 503

    httpx_mock = MagicMock()
    if resend_ok:
        httpx_mock.get.return_value = resend_resp
    else:
        httpx_mock.get.side_effect = Exception("Resend unreachable")
    health_mod.httpx = httpx_mock

    return TestClient(app, raise_server_exceptions=False), health_mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReadinessAllHealthy:
    def test_200_when_all_ok(self):
        client, _ = _build_client(stripe_ok=True, resend_ok=True, sentry_dsn="set")
        resp = client.get("/api/v1/health/readiness")
        assert resp.status_code == 200
        body = resp.json()
        assert body["stripe"] == "ok"
        assert body["resend"] == "ok"
        assert body["sentry"] == "ok"
        assert body["db"] == "ok"
        assert body["overall"] == "ok"


class TestReadinessStripeDown:
    def test_503_when_stripe_fails(self):
        client, _ = _build_client(stripe_ok=False, resend_ok=True, sentry_dsn="set")
        resp = client.get("/api/v1/health/readiness")
        assert resp.status_code == 503
        body = resp.json()
        assert body["stripe"] == "down"
        assert body["overall"] == "down"


class TestReadinessResendDown:
    def test_503_when_resend_fails(self):
        client, _ = _build_client(stripe_ok=True, resend_ok=False, sentry_dsn="set")
        resp = client.get("/api/v1/health/readiness")
        assert resp.status_code == 503
        body = resp.json()
        assert body["resend"] == "down"
        assert body["overall"] == "down"


class TestReadinessSentryMissing:
    def test_503_when_sentry_dsn_missing(self):
        client, _ = _build_client(stripe_ok=True, resend_ok=True, sentry_dsn="")
        resp = client.get("/api/v1/health/readiness")
        # sentry missing counts as degraded -> 503
        assert resp.status_code == 503
        body = resp.json()
        assert body["sentry"] == "missing"
        assert body["overall"] == "degraded"


class TestReadinessBothExternalDown:
    def test_503_overall_down_when_both_fail(self):
        client, _ = _build_client(stripe_ok=False, resend_ok=False, sentry_dsn="set")
        resp = client.get("/api/v1/health/readiness")
        assert resp.status_code == 503
        assert resp.json()["overall"] == "down"


class TestCaching:
    def test_stripe_not_called_twice_within_ttl(self):
        client, health_mod = _build_client(stripe_ok=True, resend_ok=True, sentry_dsn="set")

        # First call — probe fires
        client.get("/api/v1/health/readiness")
        assert health_mod.stripe.Customer.list.call_count == 1

        # Second call within 30 s — should use cache
        client.get("/api/v1/health/readiness")
        assert health_mod.stripe.Customer.list.call_count == 1, (
            "Stripe should NOT be probed again within the 30 s TTL"
        )

    def test_resend_not_called_twice_within_ttl(self):
        client, health_mod = _build_client(stripe_ok=True, resend_ok=True, sentry_dsn="set")

        client.get("/api/v1/health/readiness")
        assert health_mod.httpx.get.call_count == 1

        client.get("/api/v1/health/readiness")
        assert health_mod.httpx.get.call_count == 1, (
            "Resend should NOT be probed again within the 30 s TTL"
        )

    def test_cache_expires_after_ttl(self):
        client, health_mod = _build_client(stripe_ok=True, resend_ok=True, sentry_dsn="set")

        # Seed cache
        client.get("/api/v1/health/readiness")
        first_count = health_mod.stripe.Customer.list.call_count

        # Manually expire cache entries
        health_mod._cache.clear()

        # Next call should re-probe
        client.get("/api/v1/health/readiness")
        assert health_mod.stripe.Customer.list.call_count == first_count + 1


class TestNoRedis:
    """Redis is excluded per Cinder PR #2 — readiness response must never reference it."""

    def test_no_redis_key_in_response(self):
        client, _ = _build_client()
        body = client.get("/api/v1/health/readiness").json()
        assert "redis" not in body
