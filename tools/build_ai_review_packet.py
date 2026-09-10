#!/usr/bin/env python3
"""Build a deterministic, provider-neutral independent-review packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / ".ai-os" / "tasks"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def build_packet() -> str:
    task_paths = sorted(TASKS_DIR.glob("*.json"))
    tasks = [load_json(path) for path in task_paths]
    reviewable = [
        task
        for task in tasks
        if task.get("status") in {"IMPLEMENTED", "REVIEW_REQUESTED", "PASS", "FAIL"}
        and task.get("status") != "COMPLETE"
    ]

    lines = [
        "<!-- ai-os-independent-review-request -->",
        "# AI OS independent review request",
        "",
        "This packet is generated from the repository task ledger. The reviewer must be a different model or agent from the implementation agent.",
        "Do not approve from the task description alone. Inspect the changed files, CI results and claimed evidence.",
        "",
    ]

    if not reviewable:
        lines.extend(["No task currently requires independent review.", ""])
        return "\n".join(lines)

    for task in reviewable:
        lines.extend(
            [
                f"## {task['id']}: {task['title']}",
                "",
                f"**Current state:** `{task['status']}`",
                "",
                f"**Goal:** {task['goal']}",
                "",
                "### Definition of done",
                bullets(task.get("definition_of_done", [])),
                "",
                "### Required tests",
                bullets(task.get("tests", [])),
                "",
                "### Claimed implementation evidence",
            ]
        )
        for evidence in task.get("evidence", []):
            if isinstance(evidence, dict):
                lines.append(f"- {evidence.get('type', 'evidence')}: `{evidence.get('ref', '')}`")
        lines.extend(
            [
                "",
                "### Reviewer instructions",
                "1. Confirm the code implements the stated goal without weakening existing fail-closed controls.",
                "2. Confirm the definition of done is actually evidenced, not merely asserted.",
                "3. Confirm tests and CI cover the changed behaviour and note any missing end-to-end proof.",
                "4. Confirm no production, live Stripe, deployment or customer-delivery change occurred unless the task explicitly carries founder approval evidence.",
                "5. Return FAIL for any material unverified claim, unsafe bypass, configuration drift or missing evidence.",
                "",
                "### Required reply format",
                "```text",
                "AI_OS_REVIEW",
                f"task: {task['id']}",
                "verdict: PASS|FAIL",
                "reviewer_model: <model/provider>",
                "commit: <reviewed commit SHA>",
                "evidence_checked:",
                "- <CI run, diff, preview, output or other inspected evidence>",
                "findings:",
                "- <finding or 'none'>",
                "END_AI_OS_REVIEW",
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    packet = build_packet()
    if args.output:
        args.output.write_text(packet + "\n", encoding="utf-8")
    else:
        print(packet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
