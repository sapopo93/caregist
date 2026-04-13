"""Webhook subscription management endpoints (Business+ tier)."""

from __future__ import annotations

import ipaddress
import logging
import json
import secrets
import socket
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from api.config import get_tier_config
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.services.new_registration_feed import coerce_json_object

logger = logging.getLogger("caregist.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fd00::/8"),
]


def _assert_public_url(url: str) -> None:
    """Raise HTTPException if the webhook URL resolves to a private/reserved IP (SSRF guard)."""
    hostname = urlparse(url).hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid webhook URL.")
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Webhook URL hostname could not be resolved.")
    for _, _, _, _, sockaddr in results:
        ip = ipaddress.ip_address(sockaddr[0])
        if any(ip in net for net in _PRIVATE_NETWORKS):
            raise HTTPException(
                status_code=400,
                detail="Webhook URL must be a public internet address.",
            )

_WEBHOOK_TIERS = {"business", "enterprise", "admin"}

SUPPORTED_EVENTS = ["provider.rating_changed", "feed.new_registration"]


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: list[str] = Field(default_factory=lambda: ["provider.rating_changed"])
    filters: dict[str, str] = Field(default_factory=dict)


def _require_webhook_access(auth: dict) -> dict:
    tier = auth.get("tier", "free")
    config = get_tier_config(tier)
    if not config.get("webhooks"):
        raise HTTPException(
            status_code=403,
            detail="Webhooks are available on the Business plan and above. Upgrade at caregist.co.uk/pricing",
        )
    return auth


@router.post("", status_code=201)
async def register_webhook(
    body: WebhookCreate,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Register a webhook URL. Returns the signing secret — store it securely, it is shown once."""
    _require_webhook_access(_auth)

    invalid = [e for e in body.events if e not in SUPPORTED_EVENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unsupported event(s): {invalid}. Supported: {SUPPORTED_EVENTS}")

    user_id = _auth["user_id"]
    url = str(body.url)
    _assert_public_url(url)
    secret = secrets.token_hex(32)

    async with get_connection() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM webhook_subscriptions WHERE user_id = $1 AND url = $2",
            user_id, url,
        )
        if existing:
            raise HTTPException(status_code=409, detail="A webhook for this URL already exists.")

        row = await conn.fetchrow(
            """
            INSERT INTO webhook_subscriptions (user_id, url, secret, events, filter_config)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            RETURNING id, created_at
            """,
            user_id, url, secret, body.events, json.dumps(body.filters),
        )

    logger.info("Webhook registered for user %d: %s", user_id, url)
    try:
        from api.utils.analytics import log_event
        await log_event("webhook_configured", "webhook_api", user_id=user_id, meta={"events": body.events, "url": url})
    except Exception:
        pass
    return {
        "id": row["id"],
        "url": url,
        "events": body.events,
        "filters": body.filters,
        "secret": secret,
        "note": "Store this secret securely — it will not be shown again. Use it to verify the X-CareGist-Signature header on incoming requests.",
        "created_at": row["created_at"].isoformat(),
    }


@router.get("")
async def list_webhooks(_auth: dict = Depends(validate_api_key)) -> dict:
    """List active webhook subscriptions for the authenticated user."""
    _require_webhook_access(_auth)

    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, url, events, active, created_at, last_delivery_at, delivery_failures, filter_config
            FROM webhook_subscriptions
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            _auth["user_id"],
        )

    return {
        "webhooks": [
            {
                "id": r["id"],
                "url": r["url"],
                "events": r["events"],
                "active": r["active"],
                "created_at": r["created_at"].isoformat(),
                "last_delivery_at": r["last_delivery_at"].isoformat() if r["last_delivery_at"] else None,
                "delivery_failures": r["delivery_failures"],
                "filters": coerce_json_object(r["filter_config"]),
            }
            for r in rows
        ]
    }


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Deactivate a webhook subscription."""
    _require_webhook_access(_auth)

    async with get_connection() as conn:
        result = await conn.execute(
            "UPDATE webhook_subscriptions SET active = FALSE WHERE id = $1 AND user_id = $2",
            webhook_id, _auth["user_id"],
        )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Webhook not found.")
    return {"deleted": True}
