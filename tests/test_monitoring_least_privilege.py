"""The read-only freshness monitor must not require privileged app secrets.

``api.config`` runs ``settings.validate_production()`` at import time, which in
production demands API_MASTER_KEY, SUPPORT_INTERNAL_TOKEN, WEBHOOK_SECRET_KEY
and REDIS_URL. The freshness monitor performs a read-only query and is granted
none of those. These tests fail closed if the monitor import path ever reaches
``api.config`` again.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from api.monitoring_config import MonitoringSettings, monitoring_settings


MONITOR_MODULES = (
    "tools.check_new_registration_pipeline",
    "api.services.pipeline_health",
    "api.services.cqc_freshness",
)

PRIVILEGED_ENV = (
    "API_MASTER_KEY",
    "SUPPORT_INTERNAL_TOKEN",
    "WEBHOOK_SECRET_KEY",
    "REDIS_URL",
)


def _import_in_subprocess(module: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    # A subprocess is required: pytest is already in sys.modules in-process,
    # which makes api.config.validate_production() return early and would hide
    # the very regression this test exists to catch.
    script = textwrap.dedent(
        f"""
        import importlib, sys
        importlib.import_module({module!r})
        loaded = sorted(m for m in sys.modules if m == "api.config")
        print("API_CONFIG_LOADED" if loaded else "API_CONFIG_ABSENT")
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture
def production_env_without_privileged_secrets() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "ENVIRONMENT": "production",
        "PYTHONPATH": ".",
        # A non-localhost URL is what triggers the strictest production branch.
        "DATABASE_URL": "postgresql://monitor:monitor@db.example.invalid:5432/caregist",
    }


@pytest.mark.parametrize("module", MONITOR_MODULES)
def test_monitor_imports_without_privileged_secrets(
    module: str, production_env_without_privileged_secrets: dict[str, str]
) -> None:
    env = production_env_without_privileged_secrets
    for name in PRIVILEGED_ENV:
        assert name not in env

    result = _import_in_subprocess(module, env)

    assert result.returncode == 0, (
        f"{module} failed to import without privileged secrets.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    for name in PRIVILEGED_ENV:
        assert f"{name} is required" not in result.stderr


@pytest.mark.parametrize("module", MONITOR_MODULES)
def test_monitor_does_not_import_application_config(
    module: str, production_env_without_privileged_secrets: dict[str, str]
) -> None:
    result = _import_in_subprocess(module, production_env_without_privileged_secrets)
    assert result.returncode == 0, result.stderr
    assert "API_CONFIG_ABSENT" in result.stdout, (
        f"{module} transitively imports api.config, which re-introduces the "
        f"privileged production secret requirement. stdout: {result.stdout}"
    )


def test_application_config_still_fails_closed_in_production() -> None:
    """The least-privilege monitor must not have weakened the app's validation."""
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "ENVIRONMENT": "production",
        "PYTHONPATH": ".",
        "DATABASE_URL": "postgresql://app:app@db.example.invalid:5432/caregist",
        # Satisfy the earlier origin check so this test exercises the
        # privileged-secret gate it is actually asserting on.
        "APP_URL": "https://caregist.co.uk",
    }
    result = _import_in_subprocess("api.config", env)
    assert result.returncode != 0, (
        "api.config imported in production without API_MASTER_KEY; production "
        f"validation has been weakened. stdout: {result.stdout}"
    )
    assert "API_MASTER_KEY is required" in result.stderr


def test_monitoring_settings_bool_coercion_matches_application() -> None:
    for raw in ("1", "true", "TRUE", "yes", "on"):
        assert MonitoringSettings.from_env({"RADAR_DELIVERY_ENABLED": raw}).radar_delivery_enabled
    for raw in ("0", "false", "FALSE", "no", "off"):
        assert not MonitoringSettings.from_env({"RADAR_DELIVERY_ENABLED": raw}).radar_delivery_enabled
    assert not MonitoringSettings.from_env({}).radar_delivery_enabled
    with pytest.raises(ValueError):
        MonitoringSettings.from_env({"RADAR_DELIVERY_ENABLED": "maybe"})


def test_monitoring_settings_exposes_only_monitoring_flags() -> None:
    fields = set(vars(monitoring_settings))
    assert fields == {"radar_delivery_enabled"}, (
        "MonitoringSettings has grown beyond the read-only monitoring need; "
        "each added field widens what the monitor must be granted."
    )
