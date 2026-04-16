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

from api.config import settings
from api.utils.crypto import maybe_decrypt

logger = logging.getLogger("caregist.webhook_delivery")

_RETRY_DELAYS = (1, 2, 4)  # seconds between attempts
_TIMEOUT = 10.0


def _sign_payload(secret: str, payload_json: str) -> str:
    """Return HMAC-SHA256 hex digest of the JSON payload."""
    return hmac.new(secret.encode(), payload_json.encode(), hashlib.sha256).hexdigest()  # type: ignore[attr-defined]


async def deliver_webhook(url: str, secret: str, payload: dict, *, return_metadata: bool = False):
    """
    Deliver a webhook payload to the given URL.

    Signs with HMAC-SHA256 (X-CareGist-Signature header).
    Retries up to 3 times with exponential backoff.
    Returns True on success, False if all attempts fail.
    When return_metadata=True, returns a tuple:
    `(success, attempts, response_status, error_message)`.
    """
    payload_json = json.dumps(payload, default=str)
    signature = _sign_payload(secret, payload_json)
    headers = {
        "Content-Type": "application/json",
        "X-CareGist-Signature": f"sha256={signature}",
        "X-CareGist-Event": payload.get("event", "provider.rating_changed"),
        "User-Agent": "CareGist-Webhooks/1.0",
    }

    last_status_code: int | None = None
    last_error_message: str | None = None

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
            try:
                resp = await client.post(url, content=payload_json, headers=headers)
                last_status_code = resp.status_code
                if resp.status_code < 300:
                    logger.info("Webhook delivered to %s (attempt %d, status %d)", url, attempt, resp.status_code)
                    if return_metadata:
                        return True, attempt, resp.status_code, None
                    return True
                logger.warning(
                    "Webhook to %s returned %d on attempt %d",
                    url, resp.status_code, attempt,
                )
                last_error_message = f"HTTP {resp.status_code}"
            except Exception as exc:
                logger.warning("Webhook to %s failed on attempt %d: %s", url, attempt, exc)
                last_error_message = str(exc)

            if delay is not None:
                await asyncio.sleep(delay)

    logger.error("Webhook to %s failed after %d attempts", url, len(_RETRY_DELAYS) + 1)
    if return_metadata:
        return False, len(_RETRY_DELAYS) + 1, last_status_code, last_error_message
    return False


_FAILURE_DISABLE_THRESHOLD = 10


async def record_delivery_failure(conn, subscription_id: int, url: str) -> None:
    """
    Increment delivery_failures. If the threshold is reached, disable the subscription
    and queue a notification email to the owner.
    """
    row = await conn.fetchrow(
        """
        UPDATE webhook_subscriptions
        SET delivery_failures = delivery_failures + 1,
            active = CASE WHEN delivery_failures + 1 >= $2 THEN FALSE ELSE active END
        WHERE id = $1
        RETURNING active, delivery_failures,
                  (SELECT u.email FROM users u WHERE u.id = webhook_subscriptions.user_id) AS owner_email
        """,
        subscription_id,
        _FAILURE_DISABLE_THRESHOLD,
    )
    if row and not row["active"] and row["delivery_failures"] >= _FAILURE_DISABLE_THRESHOLD:
        owner_email = row["owner_email"]
        if owner_email:
            from api.utils.email_queue import queue_email  # local import to avoid circular
            html = (
                f"<p>Your webhook endpoint <strong>{url}</strong> has been automatically disabled "
                f"after {_FAILURE_DISABLE_THRESHOLD} consecutive delivery failures.</p>"
                "<p>Please check that the endpoint is reachable and returning a 2xx response, "
                "then re-enable it from your dashboard.</p>"
            )
            await queue_email(owner_email, "CareGist webhook disabled after repeated failures", html)
        logger.warning(
            "Webhook subscription %d disabled after %d consecutive failures (url=%s)",
            subscription_id,
            _FAILURE_DISABLE_THRESHOLD,
            url,
        )


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
        secret = maybe_decrypt(row["secret"], settings.webhook_secret_key)
        success = await deliver_webhook(row["url"], secret, full_payload)
        if success:
            await conn.execute(
                "UPDATE webhook_subscriptions SET last_delivery_at = $1, delivery_failures = 0 WHERE id = $2",
                now, row["id"],
            )
        else:
            await record_delivery_failure(conn, row["id"], row["url"])
