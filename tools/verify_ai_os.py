#!/usr/bin/env python3
"""Fail-closed AI OS governance checks.

This verifier uses only the Python standard library. It validates the completion
constitution, task state, evidence requirements and the public commercial
catalogue. It never calls external services and never mutates repository state.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION_PATH = ROOT / ".ai-os" / "constitution.json"
TASKS_DIR = ROOT / ".ai-os" / "tasks"
COMMERCIAL_CATALOG_PATH = ROOT / "deploy" / "commercial-catalog.json"
STERLING_AMOUNT = re.compile(r"£\s?\d[\d,]*(?:\.\d{2})?")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def non_empty_strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def check(condition: bool, name: str, detail: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS {name}: {detail}")
    else:
        print(f"FAIL {name}: {detail}")
        failures.append(name)


def validate_constitution(failures: list[str]) -> dict[str, Any]:
    try:
        constitution = load_json(CONSTITUTION_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        check(False, "AI_OS_CONSTITUTION", str(exc), failures)
        return {}

    states = constitution.get("states")
    transitions = constitution.get("transitions")
    check(
        constitution.get("schema_version") == 1,
        "AI_OS_CONSTITUTION_SCHEMA",
        "schema_version is 1",
        failures,
    )
    check(
        non_empty_strings(states),
        "AI_OS_STATES",
        "states are declared",
        failures,
    )
    check(
        isinstance(transitions, dict)
        and isinstance(states, list)
        and set(transitions) == set(states),
        "AI_OS_TRANSITIONS",
        "every state has an explicit transition rule",
        failures,
    )
    return constitution


def validate_task(path: Path, constitution: dict[str, Any], failures: list[str]) -> None:
    try:
        task = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        check(False, f"TASK_{path.name}", str(exc), failures)
        return

    prefix = f"TASK_{task.get('id', path.stem)}"
    states = set(constitution.get("states", []))
    status = task.get("status")
    definition = task.get("definition_of_done")
    tests = task.get("tests")
    evidence = task.get("evidence")
    review = task.get("independent_review")
    verification = task.get("verification")
    completion = task.get("completion")
    risk = task.get("risk")

    check(
        isinstance(task.get("id"), str) and bool(task["id"].strip()),
        f"{prefix}_ID",
        "task id is present",
        failures,
    )
    check(
        isinstance(task.get("title"), str) and bool(task["title"].strip()),
        f"{prefix}_TITLE",
        "title is present",
        failures,
    )
    check(
        isinstance(task.get("goal"), str) and bool(task["goal"].strip()),
        f"{prefix}_GOAL",
        "goal is present",
        failures,
    )
    check(status in states, f"{prefix}_STATUS", f"status {status!r} is constitutional", failures)
    check(non_empty_strings(definition), f"{prefix}_DOD", "definition of done is explicit", failures)
    check(non_empty_strings(tests), f"{prefix}_TESTS", "required tests are explicit", failures)
    check(
        isinstance(evidence, list) and bool(evidence),
        f"{prefix}_EVIDENCE",
        "implementation evidence references are present",
        failures,
    )
    check(
        isinstance(review, dict) and review.get("required") is True,
        f"{prefix}_INDEPENDENT_REVIEW",
        "independent review is required",
        failures,
    )
    check(
        isinstance(verification, dict),
        f"{prefix}_VERIFICATION",
        "verification contract is present",
        failures,
    )
    check(
        isinstance(completion, dict),
        f"{prefix}_COMPLETION",
        "completion claim is explicit",
        failures,
    )
    check(
        isinstance(risk, dict)
        and all(
            isinstance(risk.get(key), bool)
            for key in ("production_change", "live_billing_change", "customer_delivery")
        ),
        f"{prefix}_RISK",
        "production, billing and delivery risk flags are explicit booleans",
        failures,
    )

    if not isinstance(review, dict) or not isinstance(verification, dict) or not isinstance(completion, dict):
        return

    verdict = review.get("verdict")
    review_evidence = review.get("evidence_checked")
    reviewer_model = review.get("reviewer_model")

    if status == "PASS":
        check(verdict == "PASS", f"{prefix}_PASS_VERDICT", "PASS has an independent PASS verdict", failures)
        check(
            isinstance(reviewer_model, str) and bool(reviewer_model.strip()),
            f"{prefix}_PASS_REVIEWER",
            "PASS names the independent reviewer model",
            failures,
        )
        check(
            non_empty_strings(review_evidence),
            f"{prefix}_PASS_EVIDENCE",
            "PASS records evidence checked by the reviewer",
            failures,
        )

    if status == "FAIL":
        check(verdict == "FAIL", f"{prefix}_FAIL_VERDICT", "FAIL records an independent FAIL verdict", failures)

    if status in {"VERIFIED", "COMPLETE"}:
        check(verdict == "PASS", f"{prefix}_VERIFIED_REVIEW", "independent review has passed", failures)
        check(
            verification.get("status") == "VERIFIED",
            f"{prefix}_VERIFIED_STATUS",
            "end-to-end verification is VERIFIED",
            failures,
        )
        check(
            non_empty_strings(verification.get("evidence")),
            f"{prefix}_VERIFIED_EVIDENCE",
            "verification has inspectable evidence",
            failures,
        )

    if status == "COMPLETE":
        check(
            completion.get("claim") == "COMPLETE",
            f"{prefix}_COMPLETE_CLAIM",
            "COMPLETE is explicitly claimed only after all gates",
            failures,
        )

    if status not in {"VERIFIED", "COMPLETE"}:
        check(
            completion.get("claim") != "COMPLETE",
            f"{prefix}_NO_PREMATURE_COMPLETE",
            "task does not claim COMPLETE before verification",
            failures,
        )

    if isinstance(risk, dict) and (risk.get("production_change") or risk.get("live_billing_change")):
        approvals = task.get("approvals")
        check(
            isinstance(approvals, list) and any(
                isinstance(item, dict)
                and item.get("type") == "founder"
                and isinstance(item.get("evidence"), str)
                and bool(item["evidence"].strip())
                for item in approvals
            ),
            f"{prefix}_FOUNDER_APPROVAL",
            "production or live-billing risk has explicit founder approval evidence",
            failures,
        )


def validate_commercial_catalog(failures: list[str]) -> None:
    try:
        catalog = load_json(COMMERCIAL_CATALOG_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        check(False, "COMMERCIAL_CATALOG", str(exc), failures)
        return

    products = catalog.get("products")
    product = products.get("territory-opportunity-brief") if isinstance(products, dict) else None
    check(
        catalog.get("schema_version") == 1 and isinstance(product, dict),
        "COMMERCIAL_CATALOG_SCHEMA",
        "governed Territory Opportunity Brief catalogue exists",
        failures,
    )
    if not isinstance(product, dict):
        return

    unit_amount = product.get("unit_amount")
    price_label = product.get("price_label")
    expected_label = None
    if isinstance(unit_amount, int) and unit_amount >= 0 and unit_amount % 100 == 0:
        expected_label = f"£{unit_amount // 100:,}"
    check(
        isinstance(price_label, str) and price_label == expected_label,
        "COMMERCIAL_PRICE_CANONICAL",
        "price label is derived consistently from unit_amount",
        failures,
    )

    surfaces = product.get("public_surfaces")
    check(
        non_empty_strings(surfaces),
        "COMMERCIAL_SURFACES",
        "public price surfaces are explicitly declared",
        failures,
    )
    if not non_empty_strings(surfaces) or not isinstance(price_label, str):
        return

    product_name = str(product.get("name", "Territory Opportunity Brief"))
    normalized_label = price_label.replace(" ", "")
    for relative in surfaces:
        path = ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            check(False, f"COMMERCIAL_SURFACE_{relative}", str(exc), failures)
            continue

        positions = [match.start() for match in re.finditer(re.escape(product_name), text)]
        nearby_amounts: set[str] = set()
        for position in positions:
            window = text[max(0, position - 250) : position + 500]
            nearby_amounts.update(match.group(0).replace(" ", "") for match in STERLING_AMOUNT.finditer(window))

        check(
            bool(positions) and normalized_label in nearby_amounts,
            f"COMMERCIAL_SURFACE_{relative}",
            f"{product_name} exposes canonical {price_label}; nearby amounts={sorted(nearby_amounts)}",
            failures,
        )


def main() -> int:
    failures: list[str] = []
    constitution = validate_constitution(failures)

    task_paths = sorted(TASKS_DIR.glob("*.json")) if TASKS_DIR.is_dir() else []
    check(bool(task_paths), "AI_OS_TASK_LEDGER", "at least one governed task record exists", failures)
    for path in task_paths:
        validate_task(path, constitution, failures)

    validate_commercial_catalog(failures)

    if failures:
        print(f"RESULT: FAIL ({len(failures)} failed checks)")
        return 1
    print("RESULT: PASS (AI OS governance checks passed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
