#!/usr/bin/env python3
"""Normalize CI security scanner output into stable AI OS evidence.

The command intentionally separates evidence capture from gate enforcement:
security tools may write findings with a zero exit code so artifacts can be
published, then ``gate`` fails the job from the normalized evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BLOCKING = {"HIGH", "CRITICAL"}
SCHEMA_VERSION = "ai-os-security-evidence/v1"


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"input file missing: {path}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"unable to parse scanner JSON: {exc}"
    if not isinstance(value, dict):
        return None, "scanner JSON root is not an object"
    return value, None


def _base(kind: str, scope: str, source_file: Path) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": os.environ.get("AI_OS_EVIDENCE_SHA") or os.environ.get("GITHUB_SHA"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "kind": kind,
        "scope": scope,
        "source_file": str(source_file),
        "tool_error": None,
        "summary": {"critical": 0, "high": 0, "blocking": 0, "total": 0},
        "findings": [],
    }


def normalize_npm(source_file: Path, scope: str) -> dict[str, Any]:
    out = _base("npm-audit", scope, source_file)
    data, error = _read_json(source_file)
    if error:
        out["tool_error"] = error
        return out

    if data.get("error"):
        out["tool_error"] = data["error"]

    vulnerabilities = data.get("vulnerabilities", {})
    if isinstance(vulnerabilities, dict):
        for package, vuln in vulnerabilities.items():
            if not isinstance(vuln, dict):
                continue
            severity = str(vuln.get("severity", "UNKNOWN")).upper()
            advisories: list[dict[str, Any]] = []
            for via in vuln.get("via", []) if isinstance(vuln.get("via"), list) else []:
                if isinstance(via, dict):
                    advisories.append(
                        {
                            "id": via.get("source"),
                            "title": via.get("title"),
                            "url": via.get("url"),
                            "severity": str(via.get("severity", severity)).upper(),
                            "range": via.get("range"),
                        }
                    )

            fix_available = vuln.get("fixAvailable")
            fixed_version = fix_available.get("version") if isinstance(fix_available, dict) else None
            finding = {
                "id": advisories[0].get("id") if advisories else None,
                "package": package,
                "installed_version": None,
                "affected_range": vuln.get("range"),
                "fixed_version": fixed_version,
                "severity": severity,
                "direct": vuln.get("isDirect"),
                "fix_available": fix_available,
                "advisories": advisories,
            }
            out["findings"].append(finding)

    _finish(out)
    return out


def normalize_trivy(source_file: Path, scope: str) -> dict[str, Any]:
    out = _base("trivy", scope, source_file)
    data, error = _read_json(source_file)
    if error:
        out["tool_error"] = error
        return out

    for result in data.get("Results", []) if isinstance(data.get("Results"), list) else []:
        if not isinstance(result, dict):
            continue
        for vuln in result.get("Vulnerabilities", []) or []:
            if not isinstance(vuln, dict):
                continue
            out["findings"].append(
                {
                    "id": vuln.get("VulnerabilityID"),
                    "package": vuln.get("PkgName"),
                    "installed_version": vuln.get("InstalledVersion"),
                    "affected_range": None,
                    "fixed_version": vuln.get("FixedVersion") or None,
                    "severity": str(vuln.get("Severity", "UNKNOWN")).upper(),
                    "title": vuln.get("Title"),
                    "url": vuln.get("PrimaryURL"),
                    "target": result.get("Target"),
                    "class": result.get("Class"),
                    "type": result.get("Type"),
                }
            )

    _finish(out)
    return out


def _finish(out: dict[str, Any]) -> None:
    findings = out["findings"]
    findings.sort(key=lambda x: (x.get("severity") or "", x.get("package") or "", x.get("id") or ""))
    critical = sum(1 for finding in findings if finding.get("severity") == "CRITICAL")
    high = sum(1 for finding in findings if finding.get("severity") == "HIGH")
    out["summary"] = {
        "critical": critical,
        "high": high,
        "blocking": critical + high,
        "total": len(findings),
    }


def write_evidence(kind: str, source_file: Path, output_file: Path, scope: str) -> int:
    evidence = normalize_npm(source_file, scope) if kind == "npm" else normalize_trivy(source_file, scope)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = evidence["summary"]
    print(
        f"{scope}: blocking={summary['blocking']} critical={summary['critical']} "
        f"high={summary['high']} total={summary['total']} tool_error={bool(evidence['tool_error'])}"
    )
    return 0


def gate(files: list[Path]) -> int:
    failures: list[str] = []
    for path in files:
        data, error = _read_json(path)
        if error:
            failures.append(error)
            continue
        if data.get("schema") != SCHEMA_VERSION:
            failures.append(f"unexpected evidence schema in {path}")
            continue
        if data.get("tool_error"):
            failures.append(f"{data.get('scope', path)} scanner error: {data['tool_error']}")
        blocking = int(data.get("summary", {}).get("blocking", 0))
        if blocking:
            failures.append(f"{data.get('scope', path)} has {blocking} HIGH/CRITICAL findings")

    if failures:
        for failure in failures:
            print(f"SECURITY_GATE_FAIL: {failure}", file=sys.stderr)
        return 1
    print("SECURITY_GATE_PASS: no HIGH/CRITICAL findings and no scanner errors")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize")
    normalize.add_argument("--kind", choices=("npm", "trivy"), required=True)
    normalize.add_argument("--input", type=Path, required=True)
    normalize.add_argument("--output", type=Path, required=True)
    normalize.add_argument("--scope", required=True)

    gate_parser = subparsers.add_parser("gate")
    gate_parser.add_argument("files", nargs="+", type=Path)

    args = parser.parse_args()
    if args.command == "normalize":
        return write_evidence(args.kind, args.input, args.output, args.scope)
    return gate(args.files)


if __name__ == "__main__":
    raise SystemExit(main())
