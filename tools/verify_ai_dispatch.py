#!/usr/bin/env python3
"""Fail-closed validation for the AI OS repair dispatch contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".ai-os" / "dispatch-contract.json"
WORKFLOW = ROOT / ".github" / "workflows" / "ai-os-repair-dispatch.yml"


def check(condition: bool, name: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL DISPATCH_CONTRACT: {exc}")
        return 1

    route = contract.get("default_route", {})
    check(contract.get("schema_version") == 1, "DISPATCH_SCHEMA", failures)
    check(contract.get("source") == "github_issue", "DISPATCH_SOURCE", failures)
    check(contract.get("eligible_label") == "ai-os-repair", "DISPATCH_LABEL", failures)
    check(contract.get("ready_marker") == "AI_OS_DISPATCH", "DISPATCH_MARKER", failures)
    check(route.get("orchestrator") == "hermes:ai-company-governed", "DISPATCH_HERMES", failures)
    check(route.get("worker_profile") == "coder", "DISPATCH_WORKER", failures)
    check(route.get("provider") == "openai-codex", "DISPATCH_PROVIDER", failures)
    check(route.get("status") == "READY", "DISPATCH_READY_STATE", failures)

    try:
        workflow = WORKFLOW.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL DISPATCH_WORKFLOW: {exc}")
        return 1

    required_tokens = [
        "issues:",
        "ai-os-repair",
        "AI_OS_DISPATCH",
        "AWAITING_APPROVAL",
        "hermes:ai-company-governed",
        "openai-codex",
    ]
    for token in required_tokens:
        check(token in workflow, f"DISPATCH_WORKFLOW_{token}", failures)

    if failures:
        print(f"RESULT: FAIL ({len(failures)} dispatch checks failed)")
        return 1
    print("RESULT: PASS (AI OS repair dispatch contract validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
