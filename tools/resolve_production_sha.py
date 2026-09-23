"""Resolve the commit SHA of the newest successfully deployed Production release.

Production Smoke used to compare against hand-pinned repo variables
(``CAREGIST_PRODUCTION_{FRONTEND,BACKEND}_SHA``). Those go stale on every
merge, since nothing updates them automatically. This resolves the expected
SHA directly from GitHub's deployment history instead: the newest deployment
to the ``Production`` environment whose latest status is ``success``.

Never falls back to ``main`` HEAD — main can be ahead of what is actually
deployed. No successful deployment found is a hard failure (fail closed).
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_API_ROOT = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_json(url: str, *, token: str):
    request = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve(fetch_json_fn) -> str:
    """Return the newest successfully deployed Production SHA, or raise."""
    deployments = fetch_json_fn(
        "/deployments?environment=Production&per_page=20"
    )
    if not isinstance(deployments, list):
        raise ValueError("unexpected deployments response shape")

    for deployment in deployments:
        deployment_id = deployment.get("id")
        sha = deployment.get("sha")
        if deployment_id is None or not sha:
            continue
        statuses = fetch_json_fn(f"/deployments/{deployment_id}/statuses?per_page=1")
        if not isinstance(statuses, list) or not statuses:
            continue
        if statuses[0].get("state") != "success":
            continue
        if not isinstance(sha, str) or not _SHA_RE.match(sha):
            raise ValueError(f"deployment {deployment_id} has an invalid sha: {sha!r}")
        return sha

    raise ValueError("no successful Production deployment found")


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN and GITHUB_REPOSITORY must both be set", file=sys.stderr)
        return 1

    def _fetch(path: str):
        return fetch_json(f"{_API_ROOT}/repos/{repo}{path}", token=token)

    try:
        sha = resolve(_fetch)
    except Exception as exc:  # noqa: BLE001 - report and fail closed
        print(f"resolve_production_sha: {exc}", file=sys.stderr)
        return 1

    print(sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
