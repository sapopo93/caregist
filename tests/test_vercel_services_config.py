"""Deployment routing invariants for the Vercel Services topology."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_api_routes_reach_backend_before_frontend_catch_all():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]

    catch_all_index = rewrites.index({"source": "/(.*)", "destination": {"service": "frontend"}})
    backend_rules = [
        {"source": "/api/v1", "destination": {"service": "backend"}},
        {"source": "/api/v1/(.*)", "destination": {"service": "backend"}},
    ]
    for rule in backend_rules:
        assert rule in rewrites
        assert rewrites.index(rule) < catch_all_index

    assert rewrites[-1] == {
        "source": "/(.*)",
        "destination": {"service": "frontend"},
    }


def test_frontend_has_a_deployment_scoped_backend_binding():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    bindings = config["services"]["frontend"]["bindings"]

    assert {
        "type": "service",
        "service": "backend",
        "format": "url",
        "env": "CAREGIST_BACKEND_URL",
    } in bindings


def test_retired_product_routes_use_edge_level_permanent_redirects():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    redirects = {
        route["source"]: (route["destination"], route["permanent"])
        for route in config["redirects"]
    }

    assert redirects == {
        "/full-dataset": ("/intelligence-feed", True),
        "/lead-list": ("/pricing", True),
        "/groups": ("/search", True),
        "/groups/(.*)": ("/search", True),
        "/sample-report": ("/pricing", True),
        "/review-policy": ("/terms", True),
        "/api": ("/intelligence-feed", True),
    }
