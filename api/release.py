"""Public, non-secret release identity for deployment verification."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping


_SHA_RE = re.compile(r"^[0-9a-f]{7,64}$", re.IGNORECASE)
# Platform deploy SHA wins over a pinned CAREGIST_RELEASE_SHA so a stale
# project env cannot hide the commit that is actually running.
_SHA_ENV_KEYS = (
    "VERCEL_GIT_COMMIT_SHA",
    "GITHUB_SHA",
    "RENDER_GIT_COMMIT",
    "SOURCE_VERSION",
    "CAREGIST_RELEASE_SHA",
)


def release_git_sha(environ: Mapping[str, str] | None = None) -> str:
    """Return a validated deployed Git SHA, or ``unknown`` when not injected.

    Invalid values are never reflected into a public response.
    """
    env = os.environ if environ is None else environ
    for key in _SHA_ENV_KEYS:
        value = env.get(key, "").strip()
        if value and _SHA_RE.fullmatch(value):
            return value.lower()
    return "unknown"


def release_metadata(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    return {"git_sha": release_git_sha(environ)}
