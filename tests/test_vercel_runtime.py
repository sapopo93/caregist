"""Vercel Services runtime contracts for the FastAPI deployment."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest


def test_vercel_runtime_disables_background_drain_and_limits_pool():
    pytest.importorskip("multipart")
    from api.database import pool_limits
    from api.main import should_start_email_drain

    env = {"VERCEL": "1"}

    assert should_start_email_drain(env) is False
    assert pool_limits(env) == (1, 3)


def test_long_lived_runtime_keeps_background_drain_and_normal_pool():
    pytest.importorskip("multipart")
    from api.database import pool_limits
    from api.main import should_start_email_drain

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
    assert crons["/api/v1/cron/email-queue"] == "5 * * * *"
    assert crons["/api/v1/cron/feed-cycle"] == "15 * * * *"
    assert crons["/api/v1/cron/crm-maintenance"] == "25 9,11,13,15 * * *"
    assert crons["/api/v1/cron/crm-tps-automation"] == "35 9,11,13,15 * * *"

    ignore_rules = (Path(__file__).parents[1] / ".vercelignore").read_text(encoding="utf-8")
    for required_rule in (
        "!vercel.json",
        "!requirements.txt",
        "!api/**",
        "!tools/**",
        "!db/**",
    ):
        assert required_rule in ignore_rules


def test_recurring_workflow_schedules_match_evidence_gates():
    repo_root = Path(__file__).parents[1]
    expected_schedules = {
        ".github/workflows/freshness-watchdog.yml": 'cron: "10 */6 * * *"',
        ".github/workflows/cqc-signal-poll.yml": 'cron: "7,37 * * * *"',
        ".github/workflows/production-smoke.yml": 'cron: "50 */6 * * *"',
    }

    for relative_path, expected_schedule in expected_schedules.items():
        workflow = (repo_root / relative_path).read_text(encoding="utf-8")
        assert expected_schedule in workflow


def test_tps_staleness_window_exceeds_cron_cadence():
    """The CRM staleness gate must outlast the longest gap between TPS cron runs."""
    repo_root = Path(__file__).parents[1]
    config = json.loads((repo_root / "vercel.json").read_text(encoding="utf-8"))
    schedule = next(
        item["schedule"]
        for item in config["crons"]
        if item["path"] == "/api/v1/cron/crm-tps-automation"
    )
    hours = sorted(int(part.split("/")[0]) for part in schedule.split()[1].split(","))
    gaps = [
        following - current
        for current, following in zip(hours, hours[1:] + [hours[0] + 24], strict=True)
    ]

    source = (repo_root / "api/routers/health.py").read_text(encoding="utf-8")
    before_alias = source[: source.index("AS tps_stale_organizations")]
    value, unit = re.findall(r"INTERVAL '(\d+) (minutes|hours)'", before_alias)[-1]
    window = int(value) / 60 if unit == "minutes" else float(value)

    assert window > max(gaps), (
        f"tps staleness window {window}h is tighter than the {max(gaps)}h gap in "
        f"'{schedule}', so every enabled tenant would read as stale between runs"
    )


def test_explicit_vercel_cron_slots_land_inside_the_local_calling_window():
    """Vercel cron is always UTC, but calling only happens 09:00-17:00 UK.

    Slots written as local hours drift an hour through BST, which is how the
    maintenance sweep came to fire at 18:25. Assert the converted slot in both
    seasons rather than the expression itself.
    """
    repo_root = Path(__file__).parents[1]
    config = json.loads((repo_root / "vercel.json").read_text(encoding="utf-8"))
    london = ZoneInfo("Europe/London")

    for item in config["crons"]:
        minute, hour = item["schedule"].split()[:2]
        if hour == "*":
            continue
        for slot in (int(part) for part in hour.split(",")):
            for month in (1, 7):
                local = datetime(
                    2026, month, 15, slot, int(minute), tzinfo=timezone.utc
                ).astimezone(london)
                assert 9 <= local.hour < 17, (
                    f"{item['path']} fires at {local:%H:%M} local in month {month}: a slot "
                    "chosen in local time leaves the 09:00-17:00 calling window in one season"
                )
