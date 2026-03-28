"""API key authentication middleware."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from api.config import settings
from api.database import get_connection
from api.middleware.rate_limit import check_rate_limit

logger = logging.getLogger("caregist.auth")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(api_key: str | None = Security(api_key_header)) -> dict:
    """Validate API key, enforce rate limit, return key metadata."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Pass X-API-Key header.")

    # Allow master key for admin access
    if api_key == settings.api_master_key:
        meta = {"name": "master", "tier": "admin", "rate_limit": 10000}
        check_rate_limit(api_key, meta["rate_limit"])
        return meta

    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT name, tier, rate_limit, is_active FROM api_keys WHERE key = $1",
            api_key,
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="API key is disabled.")

    meta = {"name": row["name"], "tier": row["tier"], "rate_limit": row["rate_limit"]}
    check_rate_limit(api_key, meta["rate_limit"])

    # Update last_used_at (fire and forget, log failures)
    try:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE key = $1",
                api_key,
            )
    except Exception as exc:
        logger.warning("Failed to update last_used_at for key %s: %s", meta["name"], exc)

    return meta
