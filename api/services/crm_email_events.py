"""Verified Resend delivery events for CRM marketing email evidence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from api.config import settings


MAX_WEBHOOK_BYTES = 256 * 1024
HANDLED_EMAIL_EVENTS = frozenset(
    {
        "email.sent",
        "email.delivered",
        "email.delivery_delayed",
        "email.failed",
        "email.bounced",
        "email.complained",
        "email.suppressed",
    }
)


def verify_resend_webhook(payload: bytes, headers: Mapping[str, str]) -> tuple[str, dict[str, Any]]:
    if not settings.resend_webhook_secret:
        raise RuntimeError("Resend webhook verification is not configured.")
    if not payload or len(payload) > MAX_WEBHOOK_BYTES:
        raise ValueError("Resend webhook payload is invalid.")
    event_id = (headers.get("svix-id") or "").strip()
    timestamp = (headers.get("svix-timestamp") or "").strip()
    signature = (headers.get("svix-signature") or "").strip()
    if not event_id or len(event_id) > 255 or not timestamp or not signature:
        raise ValueError("Resend webhook signature headers are missing.")
    try:
        from svix.webhooks import Webhook

        event = Webhook(settings.resend_webhook_secret).verify(
            payload,
            {
                "svix-id": event_id,
                "svix-timestamp": timestamp,
                "svix-signature": signature,
            },
        )
    except Exception as exc:
        raise ValueError("Resend webhook signature is invalid.") from exc
    if not isinstance(event, dict) or not isinstance(event.get("data"), dict):
        raise ValueError("Resend webhook event is malformed.")
    return event_id, event


def resend_event_occurred_at(event: Mapping[str, Any]) -> datetime:
    """Parse provider time as evidence; never silently substitute receipt time."""
    raw = event.get("created_at")
    if not isinstance(raw, str) or not raw or len(raw) > 80:
        raise ValueError("Resend webhook event timestamp is missing.")
    try:
        occurred_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Resend webhook event timestamp is invalid.") from exc
    if occurred_at.tzinfo is None:
        raise ValueError("Resend webhook event timestamp must include a timezone.")
    occurred_at = occurred_at.astimezone(UTC)
    if occurred_at > datetime.now(UTC) + timedelta(minutes=5):
        raise ValueError("Resend webhook event timestamp is in the future.")
    return occurred_at
