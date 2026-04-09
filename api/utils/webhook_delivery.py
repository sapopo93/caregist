"""Outbound webhook delivery with HMAC-SHA256 signing and retry logic."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("caregist.webhook_delivery")

_RETRY_DELAYS = (1, 2, 4)  # seconds between attempts
_TIMEOUT = 10.0


def _sign_payload(secret: str, payload_json: str) -> str:
    """Return HMAC-SHA256 hex digest of the JSON payload."""
    return hmac.new(secret.encode(), payload_json.encode(), hashlib.sha256).hexdigest()  # type: ignore[attr-defined]


async def deliver_webhook(url: str, secret: str, payload: dict) -> bool:
    """
    Deliver a webhook payload to the given URL.

    Signs with HMAC-SHA256 (X-CareGist-Signature header).
    Retries up to 3 times with exponential backoff.
    Returns True on success, False if all attempts fail.
    """
    payload_json = json.dumps(payload, default=str)
    signature = _sign_payload(secret, payload_json)
    headers = {
        "Content-Type": "application/json",
        "X-CareGist-Signature": f"sha256={signature}",
        "X-CareGist-Event": payload.get("event", "provider.rating_changed"),
        "User-Agent": "CareGist-Webhooks/1.0",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
            try:
                resp = await client.post(url, content=payload_json, headers=headers)
                if resp.status_code < 300:
                    logger.info("Webhook delivered to %s (attempt %d, status %d)", url, attempt, resp.status_code)
                    return True
                logger.warning(
                    "Webhook to %s returned %d on attempt %d",
                    url, resp.status_code, attempt,
                )
            except Exception as exc:
                logger.warning("Webhook to %s failed on attempt %d: %s", url, attempt, exc)

            if delay is not None:
                await asyncio.sleep(delay)

    logger.error("Webhook to %s failed after %d attempts", url, len(_RETRY_DELAYS) + 1)
    return False


async def deliver_to_subscriptions(
    conn,
    user_id: int,
    event: str,
    payload: dict,
) -> None:
    """
    Fetch active webhook subscriptions for a user and deliver the event payload.
    Updates last_delivery_at and delivery_failures in the DB.
    """
    rows = await conn.fetch(
        """
        SELECT id, url, secret
        FROM webhook_subscriptions
        WHERE user_id = $1 AND active = TRUE AND $2 = ANY(events)
        """,
        user_id,
        event,
    )
    if not rows:
        return

    now = datetime.now(timezone.utc)
    full_payload = {"event": event, "timestamp": now.isoformat(), **payload}

    for row in rows:
        success = await deliver_webhook(row["url"], row["secret"], full_payload)
        if success:
            await conn.execute(
                "UPDATE webhook_subscriptions SET last_delivery_at = $1, delivery_failures = 0 WHERE id = $2",
                now, row["id"],
            )
        else:
            await conn.execute(
                "UPDATE webhook_subscriptions SET delivery_failures = delivery_failures + 1 WHERE id = $1",
                row["id"],
            )
