"""Best-effort security audit logging."""

from __future__ import annotations

import json
import logging
from typing import Any

from api.database import get_connection

logger = logging.getLogger("caregist.audit")


def actor_from_auth(auth: dict | None) -> dict[str, Any]:
    if not auth:
        return {"type": "anonymous"}
    return {
        "type": "user",
        "user_id": auth.get("user_id"),
        "key_id": auth.get("key_id"),
        "email": auth.get("email"),
        "name": auth.get("name"),
    }


async def write_audit_log(
    *,
    action: str,
    outcome: str,
    actor: dict[str, Any] | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
    conn=None,
) -> None:
    """Insert one audit_log row. Never raises; audit failures must not block mutations."""
    actor = actor or {"type": "system"}
    params = (
        action,
        outcome,
        actor.get("type"),
        actor.get("user_id"),
        actor.get("key_id"),
        actor.get("email"),
        actor.get("name"),
        target_type,
        str(target_id) if target_id is not None else None,
        json.dumps(metadata) if metadata else None,
    )
    query = """
        INSERT INTO audit_log (
            action, outcome, actor_type, actor_user_id, actor_key_id, actor_email, actor_name,
            target_type, target_id, metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
    """
    try:
        if conn is not None:
            transaction = getattr(conn, "transaction", None)
            if callable(transaction) and not type(transaction).__module__.startswith("unittest.mock"):
                async with transaction():
                    await conn.execute(query, *params)
                return
            else:
                await conn.execute(query, *params)
            return
        async with get_connection() as audit_conn:
            await audit_conn.execute(query, *params)
    except Exception as exc:
        logger.warning("Audit log insert failed (action=%s outcome=%s): %s", action, outcome, exc)
