"""Internal token authentication for support-platform routes."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from api.config import settings

internal_token_header = APIKeyHeader(name="X-Internal-Token", auto_error=False)


async def validate_internal_token(token: str | None = Security(internal_token_header)) -> dict:
    if token and settings.support_internal_token and secrets.compare_digest(token, settings.support_internal_token):
        return {"scope": "internal", "actor": "support-platform"}

    hermes_token = getattr(settings, "hermes_internal_token", "")
    if token and hermes_token and secrets.compare_digest(token, hermes_token):
        return {"scope": "internal", "actor": "hermes"}

    raise HTTPException(status_code=401, detail="Invalid internal token.")
