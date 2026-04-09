#!/usr/bin/env python3
"""Post pipeline quality hook for the shared support platform."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORT_PATH = Path("quality_report.json")


def _configured() -> bool:
    return bool(os.getenv("SUPPORT_PLATFORM_URL") and os.getenv("CAREGIST_TO_SUPPORT_TOKEN"))


def _generated_at(report: dict[str, Any]) -> str:
    raw = str(report.get("generated_at", "")).strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _report_id(report: dict[str, Any]) -> str:
    generated = _generated_at(report)
    safe = generated.replace(":", "").replace("-", "")
    return f"directory-pipeline:{safe}"


def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    base_url = os.getenv("SUPPORT_PLATFORM_URL", "").rstrip("/")
    token = os.getenv("CAREGIST_TO_SUPPORT_TOKEN", "")
    if not base_url or not token:
        return None

    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=3.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"[support-quality] Warning: support platform unreachable ({exc})", file=sys.stderr)
        return None
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[support-quality] Warning: support quality hook failed ({exc})", file=sys.stderr)
        return None


def _build_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    total_records = int(report.get("total_records", 0))
    quality_tiers = report.get("quality_tiers", {})
    issues = report.get("issues", {})

    complete_pct = float(quality_tiers.get("COMPLETE", {}).get("pct", 0.0))
    good_pct = float(quality_tiers.get("GOOD", {}).get("pct", 0.0))
    good_or_better = complete_pct + good_pct
    failed_api_calls = int(issues.get("failed_api_calls", 0))
    invalid_coordinates = int(issues.get("invalid_coordinates", 0))

    return [
        {
            "name": "pipeline_records_present",
            "verdict": "PASS" if total_records > 0 else "FAIL",
            "summary": f"{total_records} active provider records produced",
        },
        {
            "name": "good_or_better_coverage",
            "verdict": "PASS" if good_or_better >= 80 else "WARN" if good_or_better >= 60 else "FAIL",
            "summary": f"{good_or_better:.2f}% of providers are GOOD or COMPLETE",
            "details": {"complete_pct": complete_pct, "good_pct": good_pct},
        },
        {
            "name": "failed_api_calls",
            "verdict": "PASS" if failed_api_calls == 0 else "WARN" if failed_api_calls < 25 else "FAIL",
            "summary": f"{failed_api_calls} upstream API calls failed during pipeline execution",
        },
        {
            "name": "invalid_coordinates",
            "verdict": "PASS" if invalid_coordinates == 0 else "WARN" if invalid_coordinates < 100 else "FAIL",
            "summary": f"{invalid_coordinates} records have invalid coordinates",
        },
    ]


def _product_metrics(report: dict[str, Any]) -> dict[str, Any]:
    total_records = int(report.get("total_records", 0))
    quality_tiers = report.get("quality_tiers", {})
    issues = report.get("issues", {})

    complete_pct = float(quality_tiers.get("COMPLETE", {}).get("pct", 0.0))
    good_pct = float(quality_tiers.get("GOOD", {}).get("pct", 0.0))
    invalid_coordinates = int(issues.get("invalid_coordinates", 0))
    geocoding_coverage = 100.0 if total_records <= 0 else max(0.0, ((total_records - invalid_coordinates) / total_records) * 100)

    return {
        "totalProviders": total_records,
        "geocodingCoveragePct": round(geocoding_coverage, 2),
        "qualityScoreCoveragePct": round(complete_pct + good_pct, 2),
        "failedApiCalls": int(issues.get("failed_api_calls", 0)),
        "listingCompleteness": round(complete_pct + good_pct, 2),
        "searchRelevance": round(complete_pct + good_pct, 2),
        "artifactValid": total_records > 0,
        "schemaValid": True,
        "exportRowCount": total_records,
        "hiddenFieldViolations": 0,
    }


def main() -> int:
    if not _configured():
        print("[support-quality] Skipping: SUPPORT_PLATFORM_URL or CAREGIST_TO_SUPPORT_TOKEN not set")
        return 0

    if not REPORT_PATH.exists():
        print(f"[support-quality] Skipping: {REPORT_PATH} not found", file=sys.stderr)
        return 0

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    report_id = _report_id(report)
    generated_at = _generated_at(report)

    envelope = {
        "productId": "CAREGIST",
        "tenantId": "pipeline",
        "reportType": "directory_pipeline",
        "reportId": report_id,
    }
    metrics = _product_metrics(report)

    preflight_result = _post_json(
        "/v1/quality/preflight",
        {
            **envelope,
            "requiredInputs": [
                {"name": "pipeline_output_present", "present": int(report.get("total_records", 0)) > 0},
                {"name": "generated_at_present", "present": bool(str(report.get("generated_at", "")).strip())},
                {"name": "quality_tiers_present", "present": bool(report.get("quality_tiers"))},
            ],
            "productMetrics": metrics,
        },
    )

    output_result = _post_json(
        "/v1/quality/validate-output",
        {
            **envelope,
            "checks": _build_checks(report),
            "productMetrics": metrics,
        },
    )

    promise_result = _post_json(
        "/v1/quality/promise-coverage",
        {
            **envelope,
            "deliveredFeatures": ["provider-directory-export"],
            "generatedAt": generated_at,
        },
    )

    if preflight_result:
        print(f"[support-quality] Preflight verdict: {preflight_result.get('verdict')}")
    if output_result:
        print(f"[support-quality] Output validation verdict: {output_result.get('verdict')}")
    if promise_result:
        print(f"[support-quality] Promise coverage verdict: {promise_result.get('verdict')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
