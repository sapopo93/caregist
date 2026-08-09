#!/usr/bin/env python3
"""Offline Stripe release checks. This module never imports or calls Stripe."""

from __future__ import annotations

import argparse
import ast
import hashlib
import ipaddress
import json
import os
import sys
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "deploy" / "stripe-price-manifest.json"
MIGRATION = REPO_ROOT / "db" / "migrations" / "046_billing_operations.sql"
BILLING_SOURCE = REPO_ROOT / "api" / "routers" / "billing.py"
MAIN_SOURCE = REPO_ROOT / "api" / "main.py"

EXPECTED_WEBHOOK_EVENTS = {
    "checkout.session.completed",
    "checkout.session.expired",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}
EXPECTED_MANIFEST_SHA256 = "bec531624f71c0a688bb19396544b63734836aeeacefd61285644419de1c8930"
EXPECTED_PRODUCT_KEYS = {
    "radar-regional",
    "radar-national",
    "intelligence-feed",
    "embedded-enterprise",
}


def canonical_manifest_sha256(manifest: object) -> str:
    """Return a stable digest for the human-approved catalogue manifest."""
    canonical = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def deployment_identifiers(manifest: Mapping[str, object], mode: str) -> dict[str, str]:
    """Return the non-secret Product and Price IDs required for one Stripe mode."""
    identifiers: dict[str, str] = {}
    products = manifest.get("products")
    if not isinstance(products, Mapping):
        return identifiers

    for product in products.values():
        if not isinstance(product, Mapping):
            continue
        stripe_modes = product.get("stripe")
        mode_objects = stripe_modes.get(mode) if isinstance(stripe_modes, Mapping) else None
        if not isinstance(mode_objects, Mapping):
            continue

        product_env = product.get("environment_product")
        product_id = mode_objects.get("product_id")
        if isinstance(product_env, str) and isinstance(product_id, str):
            identifiers[product_env] = product_id

        price_env = product.get("environment_price")
        price_id = mode_objects.get("price_id")
        if isinstance(price_env, str) and isinstance(price_id, str):
            identifiers[price_env] = price_id

    return identifiers


def read_dotenv(path: Path | None) -> dict[str, str]:
    """Parse simple KEY=VALUE entries without evaluating shell syntax."""
    if path is None:
        return {}
    if not path.is_file():
        raise ValueError(f"Environment file does not exist: {path}")

    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"Invalid environment entry at line {number}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def merged_environment(file_values: Mapping[str, str], environ: Mapping[str, str]) -> dict[str, str]:
    """Use process values as explicit overrides without mutating either source."""
    values = dict(file_values)
    values.update(environ)
    return values


def is_public_https_origin(value: str) -> bool:
    parsed = urlparse(value.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or hostname == "localhost"
        or hostname.endswith((".localhost", ".local"))
    ):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return "." in hostname
    return address.is_global


def inspect_billing_source(path: Path) -> tuple[bool, set[str]]:
    """Return whether the webhook route exists and the events it branches on."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prefix_ok = False
    webhook_route_ok = False
    events: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "router"
            for target in node.targets
        ):
            if isinstance(node.value, ast.Call):
                prefix_ok = any(
                    keyword.arg == "prefix"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value == "/api/v1/billing"
                    for keyword in node.value.keywords
                )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "stripe_webhook":
            webhook_route_ok = any(
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "router"
                and decorator.func.attr == "post"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and decorator.args[0].value == "/webhook"
                for decorator in node.decorator_list
            )
        if (
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == "event_type"
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and isinstance(node.comparators[0].value, str)
        ):
            events.add(node.comparators[0].value)

    return prefix_ok and webhook_route_ok, events


def run_checks(
    values: Mapping[str, str],
    *,
    mode: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    migration_path: Path = MIGRATION,
    billing_source: Path = BILLING_SOURCE,
    main_source: Path = MAIN_SOURCE,
) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    secret_prefix = "sk_test_" if mode == "test" else "sk_live_"
    checks.append(
        (
            "STRIPE_SECRET_KEY",
            values.get("STRIPE_SECRET_KEY", "").startswith(secret_prefix),
            f"present with {mode} prefix",
        )
    )
    checks.append(
        (
            "STRIPE_WEBHOOK_SECRET",
            values.get("STRIPE_WEBHOOK_SECRET", "").startswith("whsec_"),
            "present with signing-secret prefix",
        )
    )
    checks.append(("APP_URL", is_public_https_origin(values.get("APP_URL", "")), "public HTTPS origin"))

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = None
    approved_manifest = (
        isinstance(manifest, Mapping)
        and manifest.get("schema_version") == 2
        and manifest.get("catalog_version") == "2026-08"
        and manifest.get("currency") == "gbp"
        and manifest.get("checkout_enabled") is False
        and isinstance(manifest.get("products"), Mapping)
        and set(manifest["products"]) == EXPECTED_PRODUCT_KEYS
        and canonical_manifest_sha256(manifest) == EXPECTED_MANIFEST_SHA256
    )
    checks.append(
        (
            "APPROVED_CATALOGUE_MANIFEST",
            approved_manifest,
            "exact approved catalogue 2026-08 and checkout disabled",
        )
    )

    identifiers = deployment_identifiers(manifest, mode) if isinstance(manifest, Mapping) else {}
    product_values: list[str] = []
    price_values: list[str] = []
    for name, expected in identifiers.items():
        value = values.get(name, "")
        prefix = "prod_" if name.startswith("STRIPE_PRODUCT_") else "price_"
        checks.append(
            (
                name,
                value == expected and value.startswith(prefix),
                f"matches approved {mode} catalogue object",
            )
        )
        if prefix == "prod_":
            product_values.append(value)
        else:
            price_values.append(value)

    expected_identifier_count = 7  # four Products; three saleable Prices.
    checks.append(
        (
            "STRIPE_DEPLOYMENT_IDS_COMPLETE",
            len(identifiers) == expected_identifier_count,
            "four Product IDs and three Price IDs are declared",
        )
    )
    checks.append(
        (
            "STRIPE_PRODUCT_IDS_UNIQUE",
            len(product_values) == 4
            and len(product_values) == len(set(product_values))
            and all(product_values),
            "all required Product IDs are distinct",
        )
    )
    checks.append(
        (
            "STRIPE_PRICE_IDS_UNIQUE",
            len(price_values) == 3
            and len(price_values) == len(set(price_values))
            and all(price_values),
            "all saleable Price IDs are distinct",
        )
    )

    migration_ok = False
    try:
        migration = migration_path.read_text(encoding="utf-8")
        migration_ok = (
            "CREATE TABLE IF NOT EXISTS billing_operations" in migration
            and "uq_billing_operations_pending_owner" in migration
        )
    except OSError:
        pass
    checks.append(("MIGRATION_046", migration_ok, "billing operation table and pending-owner index"))

    try:
        webhook_route_ok, handled_events = inspect_billing_source(billing_source)
        main_text = main_source.read_text(encoding="utf-8")
    except (OSError, SyntaxError):
        webhook_route_ok = False
        handled_events = set()
        main_text = ""
    route_ok = webhook_route_ok and "app.include_router(billing.router)" in main_text
    checks.append(("WEBHOOK_ROUTE", route_ok, "/api/v1/billing/webhook is mounted"))
    checks.append(("WEBHOOK_EVENTS", EXPECTED_WEBHOOK_EVENTS <= handled_events, "required event branches are present"))

    return checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify Stripe release configuration without network access")
    parser.add_argument("--mode", choices=("test", "live"), default="test")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional dotenv file; process environment overrides it",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser


def main(argv: list[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        file_values = read_dotenv(args.env_file)
    except ValueError as exc:
        print(f"FAIL ENV_FILE: {exc}", file=sys.stderr)
        return 1

    values = merged_environment(file_values, os.environ if environ is None else environ)
    checks = run_checks(values, mode=args.mode, manifest_path=args.manifest)
    for name, passed, description in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {description}")
    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"RESULT: {passed}/{len(checks)} offline checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
