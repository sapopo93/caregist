"""API key authentication middleware."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from api.config import get_tier_config, settings
from api.database import get_connection
from api.middleware.rate_limit import check_rate_limit

logger = logging.getLogger("caregist.auth")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(api_key: str | None = Security(api_key_header)) -> dict:
    """Validate API key, enforce rate limits, return key metadata with remaining counts."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Pass X-API-Key header.")

    # Master key
    if api_key == settings.api_master_key:
        tier = "admin"
        remaining = check_rate_limit(api_key, tier)
        return {"name": "master", "tier": tier, "remaining": remaining}

    # Look up key in database
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT name, tier, is_active FROM api_keys WHERE key = $1",
            api_key,
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="API key is disabled.")

    tier = row["tier"] or "free"
    remaining = check_rate_limit(api_key, tier)

    # Update last_used_at
    try:
        async with get_connection() as conn:
            await conn.execute("UPDATE api_keys SET last_used_at = NOW() WHERE key = $1", api_key)
    except Exception as exc:
        logger.warning("Failed to update last_used_at: %s", exc)

    return {"name": row["name"], "tier": tier, "remaining": remaining}
