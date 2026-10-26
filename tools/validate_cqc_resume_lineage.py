"""Reject a changed-code reconciliation resume before touching the database.

The database's immutable manifest and single-wave guards remain authoritative.
This preflight makes the common run/SHA mismatch actionable without opening a
resume wave or uploading a misleading recovery manifest.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.request import Request, urlopen


def validate_source_run(run: dict, *, repository: str, release_sha: str) -> None:
    if run.get("repository", {}).get("full_name") != repository:
        raise ValueError("Resume source run belongs to another repository")
    if str(run.get("path", "")).split("@", 1)[0] != ".github/workflows/cqc-reconciliation.yml":
        raise ValueError("Resume source run is not the CQC reconciliation workflow")
    if run.get("head_branch") != "main" or run.get("status") != "completed":
        raise ValueError("Resume source must be a completed main-branch run")
    if str(run.get("head_sha", "")).lower() != release_sha.lower():
        raise ValueError(
            "Resume refused: main has changed since the source run. Do not replace "
            "the recorded SHA or reuse its manifest with different code. Review the "
            "failed batch and arrange a new main-branch reconciliation, or use an "
            "independently reviewed same-code recovery. No resume write was attempted."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", required=True, type=int)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    if args.source_run_id < 1:
        parser.error("source run ID must be positive")
    token = os.environ.get("GH_TOKEN")
    if not token:
        parser.error("GH_TOKEN is required for read-only source-run verification")
    request = Request(
        f"https://api.github.com/repos/{args.repository}/actions/runs/{args.source_run_id}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            run = json.load(response)
        validate_source_run(run, repository=args.repository, release_sha=args.release_sha)
    except (ValueError, OSError) as exc:
        print(f"Resume lineage preflight failed: {exc}")
        return 1
    print("Source-run repository, workflow and code SHA match; database guards still apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
