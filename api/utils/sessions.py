"""Server-side opaque session management.

All cookie values are 32-byte URL-safe-base64 session IDs mapped in the
``sessions`` table. The bearer token (api_key) never appears in a cookie.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from api.config import settings
from api.database import get_connection


def _ttl_seconds() -> int:
    return int(getattr(settings, "session_ttl_seconds", 2592000))


async def create_session(
    user_id: int,
    user_agent: str | None = None,
    ip: str | None = None,
) -> str:
    """Insert a new session row and return the opaque session_id.

    The session_id is a 32-byte URL-safe-base64 random token (43 chars).
    It is the *only* value ever written into the caregist_session cookie.
    """
    session_id = secrets.token_urlsafe(32)
    ttl = _ttl_seconds()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (
                session_id, user_id, expires_at, user_agent, ip_address
            ) VALUES ($1, $2, $3, $4, $5::inet)
            """,
            session_id,
            user_id,
            expires_at,
            user_agent,
            ip,
        )
    return session_id


async def revoke_session(session_id: str) -> None:
    """Mark a session as revoked (soft-delete)."""
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE sessions
               SET revoked_at = NOW()
             WHERE session_id = $1
               AND revoked_at IS NULL
            """,
            session_id,
        )


async def touch_session(session_id: str) -> None:
    """Update last_used_at for a valid session (fire-and-forget)."""
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE sessions
               SET last_used_at = NOW()
             WHERE session_id = $1
               AND expires_at > NOW()
               AND revoked_at IS NULL
            """,
            session_id,
        )


async def validate_session(session_id: str) -> int | None:
    """Return user_id for an active non-revoked non-expired session, else None."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id
              FROM sessions
             WHERE session_id = $1
               AND expires_at > NOW()
               AND revoked_at IS NULL
            """,
            session_id,
        )
    return int(row["user_id"]) if row else None
