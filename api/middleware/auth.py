"""API key authentication middleware."""

from __future__ import annotations

import logging
import hashlib
import secrets

from fastapi import Cookie, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from api.config import get_max_users, get_tier_config, settings
from api.database import get_connection
from api.middleware.rate_limit import check_rate_limit

logger = logging.getLogger("caregist.auth")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def api_key_prefix(api_key: str) -> str:
    return api_key[:10]


def _row_value(row, key: str, default=None):
    try:
        return row[key]
    except (KeyError, TypeError):
        return default


def _client_identifier(request: Request) -> str:
    """Build a stable identifier for anonymous traffic rate limiting."""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


async def _update_last_used(api_key_hash: str, api_key: str) -> None:
    """Fire-and-forget: update last_used_at without blocking the request."""
    try:
        async with get_connection() as conn:
            await conn.execute("UPDATE api_keys SET last_used_at = NOW() WHERE key_hash = $1 OR key = $2", api_key_hash, api_key)
    except Exception as exc:
        logger.warning("Failed to update last_used_at: %s", exc)


async def _update_session_last_seen(session_token_hash: str) -> None:
    try:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE user_sessions SET last_seen_at = NOW() WHERE token_hash = $1",
                session_token_hash,
            )
    except Exception as exc:
        logger.warning("Failed to update session last_seen_at: %s", exc)


async def _auth_from_key_row(row, *, rate_limit_key: str, api_key: str | None = None) -> dict:
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="API key is disabled.")

    user_id = row["user_id"]
    tier = row["tier"] or "free"

    if user_id and not row["is_verified"]:
        raise HTTPException(status_code=403, detail="Verify your email before using the API.")

    if user_id:
        active_keys = int(row["active_keys"] or 0)
        subscription_max = int(row["subscription_max_users"] or 1)
        max_users = max(subscription_max, get_max_users(tier))
        if active_keys > max_users:
            async with get_connection() as conn:
                allowed_rows = await conn.fetch(
                    """
                    SELECT id FROM api_keys
                    WHERE user_id = $1 AND is_active = true
                    ORDER BY created_at ASC LIMIT $2
                    """,
                    user_id,
                    max_users,
                )
            allowed_ids = {int(r["id"]) for r in allowed_rows}
            if int(row["id"]) not in allowed_ids:
                raise HTTPException(
                    status_code=403,
                    detail="This access key is outside your plan seat limit. Revoke extra keys or upgrade your plan.",
                )

    remaining = await check_rate_limit(rate_limit_key, tier)

    import asyncio
    asyncio.create_task(_update_last_used(row["key_hash"] or "", api_key or ""))

    return {
        "key_id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "user_id": user_id,
        "tier": tier,
        "is_verified": row["is_verified"],
        "api_key": api_key,
        "remaining": remaining,
    }


async def _validate_key(api_key: str) -> dict:
    """Core key validation logic — shared by header and cookie auth paths."""
    api_key_hash = hash_api_key(api_key)

    # Master key
    if secrets.compare_digest(api_key, settings.api_master_key):
        tier = "admin"
        remaining = await check_rate_limit(api_key_hash, tier)
        return {
            "key_id": None,
            "name": "master",
            "email": None,
            "user_id": None,
            "tier": tier,
            "api_key": api_key,
            "remaining": remaining,
        }

    # Single query: key lookup + user verification + seat count
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                ak.id,
                ak.key,
                ak.key_hash,
                ak.name,
                ak.email,
                ak.user_id,
                ak.tier,
                ak.is_active,
                COALESCE(u.is_verified, true) AS is_verified,
                (
                    SELECT COUNT(*)
                    FROM api_keys ak2
                    WHERE ak2.user_id = ak.user_id AND ak2.is_active = true
                ) AS active_keys,
                COALESCE(
                    (SELECT s.max_users
                     FROM subscriptions s
                     WHERE s.user_id = ak.user_id
                     ORDER BY s.created_at DESC
                     LIMIT 1),
                    1
                ) AS subscription_max_users
            FROM api_keys ak
            LEFT JOIN users u ON u.id = ak.user_id
            WHERE ak.key_hash = $1 OR ak.key = $2
            """,
            api_key_hash,
            api_key,
        )

    if not row:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    stored_hash = _row_value(row, "key_hash")
    stored_key = _row_value(row, "key")
    if stored_hash:
        if not secrets.compare_digest(stored_hash, api_key_hash):
            raise HTTPException(status_code=401, detail="Invalid API key.")
    elif not stored_key or not secrets.compare_digest(stored_key, api_key):
        raise HTTPException(status_code=401, detail="Invalid API key.")

    return await _auth_from_key_row(row, rate_limit_key=api_key_hash, api_key=api_key)


async def _validate_session(session_token: str) -> dict:
    session_token_hash = hash_api_key(session_token)
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                ak.id,
                ak.key,
                ak.key_hash,
                ak.name,
                ak.email,
                ak.user_id,
                ak.tier,
                ak.is_active,
                COALESCE(u.is_verified, true) AS is_verified,
                (
                    SELECT COUNT(*)
                    FROM api_keys ak2
                    WHERE ak2.user_id = ak.user_id AND ak2.is_active = true
                ) AS active_keys,
                COALESCE(
                    (SELECT s.max_users
                     FROM subscriptions s
                     WHERE s.user_id = ak.user_id
                     ORDER BY s.created_at DESC
                     LIMIT 1),
                    1
                ) AS subscription_max_users
            FROM user_sessions us
            JOIN api_keys ak ON ak.id = us.api_key_id
            LEFT JOIN users u ON u.id = us.user_id
            WHERE us.token_hash = $1
              AND us.revoked_at IS NULL
              AND us.expires_at > NOW()
            """,
            session_token_hash,
        )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    import asyncio
    asyncio.create_task(_update_session_last_seen(session_token_hash))
    return await _auth_from_key_row(row, rate_limit_key=session_token_hash)


async def validate_api_key(
    api_key: str | None = Security(api_key_header),
    caregist_session: str | None = Cookie(default=None),
) -> dict:
    """Validate API key from X-API-Key header or caregist_session cookie."""
    if api_key:
        return await _validate_key(api_key)
    if caregist_session:
        return await _validate_session(caregist_session)
    if not api_key and not caregist_session:
        raise HTTPException(status_code=401, detail="Missing API key. Pass X-API-Key header or log in.")


async def validate_optional_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
    caregist_session: str | None = Cookie(default=None),
) -> dict:
    """Return authenticated metadata when a key is present, else a free guest tier."""
    if api_key:
        return await _validate_key(api_key)
    if caregist_session:
        return await _validate_session(caregist_session)

    guest_key = f"guest:{_client_identifier(request)}"
    remaining = await check_rate_limit(guest_key, "free")
    return {
        "key_id": None,
        "name": "guest",
        "email": None,
        "user_id": None,
        "tier": "free",
        "is_verified": True,
        "api_key": None,
        "remaining": remaining,
    }
