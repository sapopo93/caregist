"""Shared analytics event logging utility."""

from __future__ import annotations

import logging

from api.database import get_connection

logger = logging.getLogger("caregist.analytics")


async def log_event(
    event_type: str,
    event_source: str,
    *,
    user_id: int | None = None,
    email: str | None = None,
    provider_id: str | None = None,
    meta: dict | None = None,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    """Insert an analytics event. Fails silently — never blocks the caller."""
    try:
        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO analytics_events
                    (event_type, event_source, user_id, email, provider_id, meta, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::inet, $8)
                """,
                event_type,
                event_source,
                user_id,
                email,
                provider_id,
                __import__("json").dumps(meta or {}),
                ip,
                ua,
            )
    except Exception as exc:
        logger.warning("Failed to log analytics event %s: %s", event_type, exc)
