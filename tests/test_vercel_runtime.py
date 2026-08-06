"""Vercel Services runtime contracts for the FastAPI deployment."""

from __future__ import annotations

import json
from pathlib import Path

from api.database import pool_limits
from api.main import should_start_email_drain


def test_vercel_runtime_disables_background_drain_and_limits_pool():
    env = {"VERCEL": "1"}

    assert should_start_email_drain(env) is False
    assert pool_limits(env) == (1, 3)


def test_long_lived_runtime_keeps_background_drain_and_normal_pool():
    assert should_start_email_drain({}) is True
    assert pool_limits({}) == (2, 20)


def test_vercel_services_route_backend_paths_to_fastapi():
    config_path = Path(__file__).parents[1] / "vercel.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["services"]["frontend"]["root"] == "frontend/"
    assert config["services"]["frontend"]["framework"] == "nextjs"
    assert config["services"]["frontend"]["bindings"] == [
        {
            "type": "service",
            "service": "backend",
            "format": "url",
            "env": "CAREGIST_BACKEND_URL",
        }
    ]
    assert config["services"]["backend"]["root"] == "."
    assert config["services"]["backend"]["framework"] == "fastapi"
    assert config["services"]["backend"]["entrypoint"] == "api.main:app"
    rewrites = {
        item["source"]: item["destination"]["service"]
        for item in config["rewrites"]
    }
    assert rewrites["/api/health/directory"] == "frontend"
    assert rewrites["/api/export"] == "frontend"
    assert rewrites["/api/leads/request"] == "frontend"
    assert rewrites["/api/v1/(.*)"] == "backend"
    assert rewrites["/internal/(.*)"] == "backend"
    assert rewrites["/metrics"] == "backend"
    assert rewrites["/(.*)"] == "frontend"

    crons = {item["path"]: item["schedule"] for item in config["crons"]}
    assert crons["/api/v1/cron/email-queue"] == "*/5 * * * *"
    assert crons["/api/v1/cron/feed-cycle"] == "15 * * * *"

    ignore_rules = (Path(__file__).parents[1] / ".vercelignore").read_text(encoding="utf-8")
    for required_rule in (
        "!vercel.json",
        "!requirements.txt",
        "!api/**",
        "!tools/**",
        "!db/**",
    ):
        assert required_rule in ignore_rules
