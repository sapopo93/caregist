"""API key authentication middleware."""

from __future__ import annotations

import logging
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from api.config import get_max_users, get_tier_config, settings
from api.database import get_connection
from api.middleware.rate_limit import check_rate_limit

logger = logging.getLogger("caregist.auth")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(api_key: str | None = Security(api_key_header)) -> dict:
    """Validate API key, enforce rate limits, return key metadata with remaining counts."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Pass X-API-Key header.")

    # Master key
    if secrets.compare_digest(api_key, settings.api_master_key):
        tier = "admin"
        remaining = await check_rate_limit(api_key, tier)
        return {
            "key_id": None,
            "name": "master",
            "email": None,
            "user_id": None,
            "tier": tier,
            "remaining": remaining,
        }

    # Look up key in database
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT ak.id, ak.name, ak.email, ak.user_id, ak.tier, ak.is_active, ak.created_at,
                   COALESCE(u.is_verified, true) AS is_verified
            FROM api_keys ak
            LEFT JOIN users u ON u.id = ak.user_id
            WHERE ak.key = $1
            """,
            api_key,
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    row_data = dict(row)

    if not row_data.get("is_active", True):
        raise HTTPException(status_code=403, detail="API key is disabled.")

    user_id = row_data.get("user_id")
    if user_id:
        async with get_connection() as conn:
            seat_row = await conn.fetchrow(
                """
                SELECT
                  (SELECT COUNT(*) FROM api_keys WHERE user_id = $1 AND is_active = true) AS active_keys,
                  COALESCE(
                    (SELECT max_users
                     FROM subscriptions
                     WHERE user_id = $1
                     ORDER BY created_at DESC
                     LIMIT 1),
                    1
                  ) AS max_users
                """,
                user_id,
            )
            active_keys = int(seat_row["active_keys"] or 0) if seat_row else 0
            subscription_max = int(seat_row["max_users"] or 1) if seat_row else 1
            max_users = max(subscription_max, get_max_users(row_data.get("tier") or "free"))
            if active_keys > max_users:
                allowed_rows = await conn.fetch(
                    """
                    SELECT id
                    FROM api_keys
                    WHERE user_id = $1 AND is_active = true
                    ORDER BY created_at ASC
                    LIMIT $2
                    """,
                    user_id,
                    max_users,
                )
        if active_keys > max_users:
            allowed_ids = {int(row["id"]) for row in allowed_rows}
            if int(row_data["id"]) not in allowed_ids:
                raise HTTPException(
                    status_code=403,
                    detail="This access key is outside your plan seat limit. Revoke extra keys or upgrade your plan.",
                )

    tier = row_data.get("tier") or "free"
    remaining = await check_rate_limit(api_key, tier)

    # Update last_used_at
    try:
        async with get_connection() as conn:
            await conn.execute("UPDATE api_keys SET last_used_at = NOW() WHERE key = $1", api_key)
    except Exception as exc:
        logger.warning("Failed to update last_used_at: %s", exc)

    return {
        "key_id": row_data.get("id"),
        "name": row_data.get("name"),
        "email": row_data.get("email"),
        "user_id": user_id,
        "tier": tier,
        "is_verified": row_data.get("is_verified", True),
        "remaining": remaining,
    }
