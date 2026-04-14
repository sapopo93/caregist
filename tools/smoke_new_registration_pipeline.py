#!/usr/bin/env python3
"""Smoke-check the new-registration wedge through its live HTTP surfaces."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key and key not in os.environ:
            os.environ[key.strip()] = value.strip()


def _get_json(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    req = urllib_request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib_error.HTTPError as exc:
        payload = exc.read().decode() if exc.fp else "{}"
        try:
            return exc.code, json.loads(payload)
        except Exception:
            return exc.code, {"detail": payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-check the CareGist new-registration wedge")
    parser.add_argument("--base-url", default=os.environ.get("APP_URL", "https://caregist.co.uk"))
    parser.add_argument("--api-key", default=os.environ.get("API_MASTER_KEY"))
    parser.add_argument("--internal-token", default=os.environ.get("SUPPORT_INTERNAL_TOKEN"))
    parser.add_argument("--region", default="London")
    return parser.parse_args()


def main() -> int:
    _load_env_file()
    args = parse_args()

    if not args.api_key:
        print("ERROR: API key not provided. Use --api-key or set API_MASTER_KEY.", file=sys.stderr)
        return 1

    failures: list[str] = []
    base_url = args.base_url.rstrip("/")

    checks = [
        ("health", f"{base_url}/api/v1/health", {}),
        ("readiness", f"{base_url}/api/v1/health/readiness", {}),
        ("freshness", f"{base_url}/api/v1/health/freshness", {}),
        (
            "feed",
            f"{base_url}/api/v1/feed/new-registrations?{urllib_parse.urlencode({'per_page': 5, 'region': args.region})}",
            {"X-API-Key": args.api_key},
        ),
    ]

    if args.internal_token:
        checks.append(
            (
                "internal_pipeline",
                f"{base_url}/internal/pipeline",
                {"X-Internal-Token": args.internal_token},
            )
        )

    for name, url, headers in checks:
        status, payload = _get_json(url, headers)
        print(f"[{name}] status={status}")
        print(json.dumps(payload, indent=2)[:1200])

        if name in {"readiness", "freshness"} and status != 200:
            failures.append(f"{name} returned {status}")
        elif name == "feed":
            if status != 200:
                failures.append(f"feed returned {status}")
            elif not isinstance(payload.get("data"), list):
                failures.append("feed payload missing data[]")
        elif status >= 500:
            failures.append(f"{name} returned {status}")

    if failures:
        print("\nSMOKE FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nSMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
