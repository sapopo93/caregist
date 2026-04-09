"""Stripe billing: checkout, webhooks, and subscription management."""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from api.middleware.auth import validate_api_key

from api.config import settings
from api.database import get_connection

logger = logging.getLogger("caregist.billing")
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

from api.config import get_tier_config

PRICE_TO_TIER = {}  # Populated at startup from settings


def init_stripe():
    """Initialize Stripe with API key and price mappings."""
    if not settings.stripe_secret_key:
        logger.warning("Stripe not configured — billing endpoints will fail")
        return
    stripe.api_key = settings.stripe_secret_key
    if settings.stripe_price_starter:
        PRICE_TO_TIER[settings.stripe_price_starter] = "starter"
    if settings.stripe_price_pro:
        PRICE_TO_TIER[settings.stripe_price_pro] = "pro"
    if settings.stripe_price_business:
        PRICE_TO_TIER[settings.stripe_price_business] = "business"


class CheckoutRequest(BaseModel):
    email: EmailStr
    tier: str  # "starter", "pro", or "business"


@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, _auth: dict = Depends(validate_api_key)) -> dict:
    """Create a Stripe Checkout session for upgrading."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    price_map = {
        "starter": settings.stripe_price_starter,
        "pro": settings.stripe_price_pro,
        "business": settings.stripe_price_business,
    }
    price_id = price_map.get(req.tier)
    if not price_id:
        if req.tier == "enterprise":
            raise HTTPException(
                status_code=422,
                detail="Enterprise plans require custom setup. Contact enterprise@caregist.co.uk to get started.",
            )
        raise HTTPException(status_code=400, detail=f"Invalid tier: {req.tier}. Choose 'starter', 'pro', or 'business'.")

    # Find or create Stripe customer
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id, stripe_customer_id FROM users WHERE email = $1", req.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found. Register first.")

    # Prevent double-charge: reject if user already has an active paid subscription
    async with get_connection() as conn:
        existing_sub = await conn.fetchrow(
            "SELECT tier, status FROM subscriptions WHERE user_id = $1 AND status = 'active' AND tier != 'free' ORDER BY created_at DESC LIMIT 1",
            user["id"],
        )
    if existing_sub:
        raise HTTPException(
            status_code=409,
            detail=f"You already have an active {existing_sub['tier']} subscription. Cancel it first to change plans.",
        )

    customer_id = user["stripe_customer_id"]
    if not customer_id:
        customer = stripe.Customer.create(email=req.email)
        customer_id = customer.id
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
                customer_id, user["id"],
            )

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.app_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url}/pricing",
        metadata={"user_id": str(user["id"]), "tier": req.tier},
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured.")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError) as e:
        logger.error("Webhook signature failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data)
    else:
        logger.info("Unhandled Stripe event: %s", event_type)

    return {"status": "ok"}


async def _handle_checkout_completed(session: dict) -> None:
    """Upgrade user after successful checkout."""
    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier", "starter")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    if not user_id:
        logger.error("Checkout completed without user_id in metadata")
        return

    rate_limit = get_tier_config(tier)["rate"]

    async with get_connection() as conn:
        # Update subscription
        await conn.execute(
            """INSERT INTO subscriptions (user_id, stripe_subscription_id, tier, status)
               VALUES ($1, $2, $3, 'active')
               ON CONFLICT (stripe_subscription_id) DO UPDATE SET tier = $3, status = 'active'""",
            int(user_id), subscription_id, tier,
        )

        # Upgrade API key tier
        await conn.execute(
            "UPDATE api_keys SET tier = $1, rate_limit = $2 WHERE user_id = $3 AND is_active = true",
            tier, rate_limit, int(user_id),
        )

        # Update Stripe customer ID
        if customer_id:
            await conn.execute(
                "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
                customer_id, int(user_id),
            )

    logger.info("User %s upgraded to %s (subscription: %s)", user_id, tier, subscription_id)


async def _handle_subscription_updated(subscription: dict) -> None:
    """Handle subscription changes (upgrade/downgrade)."""
    sub_id = subscription.get("id")
    status = subscription.get("status", "active")
    price_id = None
    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")

    tier = PRICE_TO_TIER.get(price_id, "starter") if price_id else "starter"
    rate_limit = get_tier_config(tier)["rate"]

    async with get_connection() as conn:
        sub_row = await conn.fetchrow(
            "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
        )
        if sub_row:
            await conn.execute(
                "UPDATE subscriptions SET tier = $1, status = $2 WHERE stripe_subscription_id = $3",
                tier, status, sub_id,
            )
            await conn.execute(
                "UPDATE api_keys SET tier = $1, rate_limit = $2 WHERE user_id = $3 AND is_active = true",
                tier, rate_limit, sub_row["user_id"],
            )

    logger.info("Subscription %s updated: tier=%s status=%s", sub_id, tier, status)


async def _handle_subscription_deleted(subscription: dict) -> None:
    """Downgrade to free on cancellation."""
    sub_id = subscription.get("id")

    async with get_connection() as conn:
        sub_row = await conn.fetchrow(
            "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
        )
        if sub_row:
            await conn.execute(
                "UPDATE subscriptions SET tier = 'free', status = 'canceled' WHERE stripe_subscription_id = $1",
                sub_id,
            )
            await conn.execute(
                "UPDATE api_keys SET tier = 'free', rate_limit = $1 WHERE user_id = $2 AND is_active = true",
                get_tier_config("free")["rate"], sub_row["user_id"],
            )

    logger.info("Subscription %s canceled, user downgraded to free", sub_id)
