"""Least-privilege configuration for the read-only monitoring path.

``api.config`` builds the full application ``Settings`` object and calls
``validate_production()`` at import time. In production that import demands
privileged runtime credentials (``API_MASTER_KEY``, ``SUPPORT_INTERNAL_TOKEN``,
``WEBHOOK_SECRET_KEY``, ``REDIS_URL``) which a read-only freshness monitor has
no need for and must not be granted.

This module exposes only the flags the monitoring snapshot actually reads. It
imports nothing from ``api.config`` so the monitor cannot transitively pull in
production secret validation. The application runtime keeps using
``api.config.settings`` and its full fail-closed validation unchanged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Mirrors pydantic's bool coercion so the monitor and the application agree on
# the same environment value. Anything else is rejected rather than guessed.
_TRUE = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSE = frozenset({"0", "false", "f", "no", "n", "off"})


def _as_bool(raw: str | None, *, name: str, default: bool) -> bool:
    if raw is None or raw == "":
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"{name} must be a boolean value, got {raw!r}")


@dataclass
class MonitoringSettings:
    """The only configuration the read-only monitoring path may read."""

    radar_delivery_enabled: bool = False

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "MonitoringSettings":
        env = os.environ if environ is None else environ
        return cls(
            radar_delivery_enabled=_as_bool(
                env.get("RADAR_DELIVERY_ENABLED"),
                name="RADAR_DELIVERY_ENABLED",
                default=False,
            ),
        )


monitoring_settings = MonitoringSettings.from_env()
