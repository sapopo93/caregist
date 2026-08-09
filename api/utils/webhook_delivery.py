"""Outbound webhook delivery with HMAC-SHA256 signing and retry logic."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from collections.abc import Sequence
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from api.config import settings
from api.utils.crypto import maybe_decrypt

logger = logging.getLogger("caregist.webhook_delivery")

_RETRY_DELAYS = (1, 2, 4)  # seconds between attempts
_TIMEOUT = 10.0


def assert_public_webhook_url(url: str) -> None:
    """Reject webhook targets that currently resolve to non-public IP space."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Webhook URL must be an absolute HTTP(S) URL.")
    try:
        results = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Webhook URL hostname could not be resolved.") from exc

    for _, _, _, _, sockaddr in results:
        ip = ipaddress.ip_address(sockaddr[0])
        if not ip.is_global:
            raise ValueError("Webhook URL must resolve to public internet addresses.")


SIGNATURE_TOLERANCE_SECONDS = 300


def _sign_payload(secret: str, payload_json: str, timestamp: int | None = None) -> str:
    """Return the HMAC digest for a timestamped payload."""
    signed = payload_json if timestamp is None else f"{timestamp}.{payload_json}"
    return hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()  # type: ignore[attr-defined]


def verify_signature(
    secret: str | Sequence[str],
    payload_body: str | bytes,
    signature_header: str | None,
    *,
    now: int | None = None,
    tolerance_seconds: int = SIGNATURE_TOLERANCE_SECONDS,
) -> bool:
    """Verify an X-CareGist-Signature header against the raw request body.

    This is the consumer-side counterpart to our signing and is the reference
    implementation we publish to customers (F-43). Usage in a subscriber:

        body = await request.body()
        if not verify_signature(my_secret, body, request.headers.get("X-CareGist-Signature")):
            return 401

    The current header format is ``t=<unix>,v1=<hexdigest>`` over
    ``timestamp.body``. The legacy ``sha256=<hexdigest>`` format remains
    verifiable during the 90-day compatibility window.
    """
    if not signature_header:
        return False
    if isinstance(payload_body, bytes):
        payload_body = payload_body.decode("utf-8")
    secrets = (secret,) if isinstance(secret, str) else tuple(secret)
    if not secrets:
        return False
    if signature_header.startswith("sha256="):
        provided = signature_header.removeprefix("sha256=")
        return bool(provided) and any(
            hmac.compare_digest(_sign_payload(candidate, payload_body), provided)
            for candidate in secrets
        )

    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        key, separator, value = item.strip().partition("=")
        if separator and key and value:
            parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts["t"][0])
    except (KeyError, IndexError, ValueError):
        return False
    current = int(datetime.now(timezone.utc).timestamp()) if now is None else int(now)
    if abs(current - timestamp) > tolerance_seconds:
        return False
    provided_signatures = parts.get("v1", [])
    return any(
        hmac.compare_digest(_sign_payload(candidate, payload_body, timestamp), provided)
        for candidate in secrets
        for provided in provided_signatures
    )


async def deliver_webhook(
    url: str,
    secret: str | Sequence[str],
    payload: dict,
    *,
    return_metadata: bool = False,
):
    """
    Deliver a webhook payload to the given URL.

    Signs with HMAC-SHA256 (X-CareGist-Signature header).
    Retries up to 3 times with exponential backoff.
    Returns True on success, False if all attempts fail.
    When return_metadata=True, returns a tuple:
    `(success, attempts, response_status, error_message)`.
    """
    try:
        assert_public_webhook_url(url)
    except ValueError as exc:
        logger.warning("Blocked webhook delivery to non-public URL %s: %s", url, exc)
        if return_metadata:
            return False, 0, None, str(exc)
        return False

    payload_json = json.dumps(payload, default=str)
    signature_timestamp = int(datetime.now(timezone.utc).timestamp())
    secrets = (secret,) if isinstance(secret, str) else tuple(secret)
    if not secrets:
        if return_metadata:
            return False, 0, None, "delivery signing secret is missing"
        return False
    signatures = [
        _sign_payload(candidate, payload_json, signature_timestamp)
        for candidate in secrets
    ]
    headers = {
        "Content-Type": "application/json",
        "X-CareGist-Signature": ",".join(
            [f"t={signature_timestamp}", *(f"v1={signature}" for signature in signatures)]
        ),
        "X-CareGist-Event": payload.get("event", "provider.rating_changed"),
        "X-CareGist-Event-Id": str(payload.get("event_id") or payload.get("id") or ""),
        "User-Agent": "CareGist-Webhooks/1.0",
    }

    last_status_code: int | None = None
    last_error_message: str | None = None

    from api.metrics import observe_webhook_delivery

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
            try:
                resp = await client.post(url, content=payload_json, headers=headers)
                last_status_code = resp.status_code
                if resp.status_code < 300:
                    logger.info("Webhook delivered to %s (attempt %d, status %d)", url, attempt, resp.status_code)
                    observe_webhook_delivery(True)
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
    observe_webhook_delivery(False)
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
