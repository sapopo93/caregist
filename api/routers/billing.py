"""Stripe billing: checkout, webhooks, and subscription management."""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from api.middleware.auth import validate_api_key

from api.config import (
    allows_extra_seats,
    max_tier,
    get_subscription_entitlements,
    get_tier_config,
    settings,
)
from api.database import get_connection

logger = logging.getLogger("caregist.billing")
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

PRICE_TO_TIER = {}         # B2B data plan prices → tier name
PRICE_TO_PROFILE_TIER = {}  # Provider listing prices → profile tier name


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
    if settings.stripe_price_pro_seat:
        PRICE_TO_TIER[settings.stripe_price_pro_seat] = "pro-seat"
    if settings.stripe_price_business:
        PRICE_TO_TIER[settings.stripe_price_business] = "business"
    if settings.stripe_price_alerts_pro:
        PRICE_TO_TIER[settings.stripe_price_alerts_pro] = "alerts-pro"
    if settings.stripe_price_profile_enhanced:
        PRICE_TO_PROFILE_TIER[settings.stripe_price_profile_enhanced] = "enhanced"
    if settings.stripe_price_profile_premium:
        PRICE_TO_PROFILE_TIER[settings.stripe_price_profile_premium] = "premium"
    if settings.stripe_price_profile_sponsored:
        PRICE_TO_PROFILE_TIER[settings.stripe_price_profile_sponsored] = "sponsored"


def _is_base_plan_price(price_id: str | None) -> bool:
    return PRICE_TO_TIER.get(price_id) in {"starter", "pro", "business"}


class CheckoutRequest(BaseModel):
    email: EmailStr
    tier: str  # "starter", "pro", or "business"
    extra_seats: int = Field(0, ge=0, le=50)


def _normalize_extra_seats(tier: str, extra_seats: int) -> int:
    if extra_seats <= 0:
        return 0
    if not allows_extra_seats(tier):
        raise HTTPException(status_code=422, detail=f"Extra seats are not available on the {tier.title()} plan.")
    if not settings.stripe_price_pro_seat:
        raise HTTPException(status_code=503, detail="Seat add-on checkout is not configured yet. Contact support to add users.")
    return extra_seats


async def _persist_subscription_state(
    conn,
    user_id: int,
    subscription_id: str | None,
    tier: str,
    status: str,
    *,
    stripe_price_id: str | None = None,
    extra_seats: int = 0,
) -> None:
    entitlements = get_subscription_entitlements(tier, extra_seats)
    rate_limit = get_tier_config(tier)["rate"]
    await conn.execute(
        """
        INSERT INTO subscriptions (
            user_id, stripe_subscription_id, stripe_price_id, tier, status,
            included_users, extra_seats, max_users, seat_price_gbp
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (stripe_subscription_id) DO UPDATE SET
            stripe_price_id = EXCLUDED.stripe_price_id,
            tier = EXCLUDED.tier,
            status = EXCLUDED.status,
            included_users = EXCLUDED.included_users,
            extra_seats = EXCLUDED.extra_seats,
            max_users = EXCLUDED.max_users,
            seat_price_gbp = EXCLUDED.seat_price_gbp
        """,
        user_id,
        subscription_id,
        stripe_price_id,
        tier,
        status,
        entitlements["included_users"],
        entitlements["extra_seats"],
        entitlements["max_users"],
        entitlements["seat_price_gbp"],
    )
    await conn.execute(
        "UPDATE api_keys SET tier = $1, rate_limit = $2 WHERE user_id = $3 AND is_active = true",
        tier, rate_limit, user_id,
    )


@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, _auth: dict = Depends(validate_api_key)) -> dict:
    """Create a Stripe Checkout session for upgrading."""
    if not _auth.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before starting billing.")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    price_map = {
        "alerts-pro": settings.stripe_price_alerts_pro,
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
        raise HTTPException(status_code=400, detail=f"Invalid tier: {req.tier}. Choose 'alerts-pro', 'starter', 'pro', or 'business'.")

    extra_seats = _normalize_extra_seats(req.tier, req.extra_seats)

    # Find or create Stripe customer
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id, stripe_customer_id FROM users WHERE email = $1", req.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found. Register first.")

    # Prevent double-charge: reject if user already has an active paid subscription
    async with get_connection() as conn:
        existing_sub = await conn.fetchrow(
            """
            SELECT tier, status, stripe_subscription_id, extra_seats
            FROM subscriptions
            WHERE user_id = $1 AND status = 'active' AND tier != 'free'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user["id"],
        )
    if existing_sub:
        subscription_id = existing_sub["stripe_subscription_id"]
        if not subscription_id:
            raise HTTPException(
                status_code=409,
                detail=f"Your account already has an active {existing_sub['tier']} subscription. Contact support to change plans.",
            )
        subscription = stripe.Subscription.retrieve(subscription_id)
        items = subscription.get("items", {}).get("data", [])
        base_item = next((item for item in items if _is_base_plan_price(item.get("price", {}).get("id"))), None)
        seat_item = next((item for item in items if PRICE_TO_TIER.get(item.get("price", {}).get("id")) == "pro-seat"), None)

        updated_items: list[dict] = []
        if base_item:
            updated_items.append({"id": base_item["id"], "price": price_id, "quantity": 1})
        else:
            updated_items.append({"price": price_id, "quantity": 1})

        if seat_item and extra_seats <= 0:
            updated_items.append({"id": seat_item["id"], "deleted": True})
        elif seat_item and extra_seats > 0:
            updated_items.append({"id": seat_item["id"], "price": settings.stripe_price_pro_seat, "quantity": extra_seats})
        elif extra_seats > 0:
            updated_items.append({"price": settings.stripe_price_pro_seat, "quantity": extra_seats})

        stripe.Subscription.modify(
            subscription_id,
            items=updated_items,
            proration_behavior="create_prorations",
            metadata={"user_id": str(user["id"]), "tier": req.tier, "extra_seats": str(extra_seats)},
        )
        async with get_connection() as conn:
            await _persist_subscription_state(
                conn,
                int(user["id"]),
                subscription_id,
                req.tier,
                "active",
                stripe_price_id=price_id,
                extra_seats=extra_seats,
            )
        return {"updated": True, "tier": req.tier, "extra_seats": extra_seats}

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
        line_items=[
            {"price": price_id, "quantity": 1},
            *([{"price": settings.stripe_price_pro_seat, "quantity": extra_seats}] if extra_seats else []),
        ],
        mode="subscription",
        success_url=f"{settings.app_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url}/pricing",
        metadata={"user_id": str(user["id"]), "tier": req.tier, "extra_seats": str(extra_seats), "price_id": price_id},
    )

    stripe_mode = "test" if settings.stripe_secret_key.startswith("sk_test_") else "live"
    return {"checkout_url": session.url, "session_id": session.id, "stripe_mode": stripe_mode}


_PROFILE_TIERS = {"enhanced", "premium", "sponsored"}


class ProfileCheckoutRequest(BaseModel):
    slug: str
    tier: str
    email: EmailStr


@router.post("/profile-checkout")
async def create_profile_checkout(
    req: ProfileCheckoutRequest,
    _auth: dict = Depends(validate_api_key),
) -> dict:
    """Create a Stripe Checkout session for a provider listing tier upgrade."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    if req.tier not in _PROFILE_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid profile tier: {req.tier}. Choose from {sorted(_PROFILE_TIERS)}.")

    price_map = {
        "enhanced": settings.stripe_price_profile_enhanced,
        "premium": settings.stripe_price_profile_premium,
        "sponsored": settings.stripe_price_profile_sponsored,
    }
    price_id = price_map[req.tier]
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Checkout for the {req.tier} profile tier is not yet configured.")

    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id, stripe_customer_id FROM users WHERE email = $1", req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Register first.")

    async with get_connection() as conn:
        provider = await conn.fetchrow(
            """
            SELECT id, is_claimed, profile_tier
            FROM care_providers
            WHERE slug = $1 OR id = $1
            ORDER BY CASE WHEN slug = $1 THEN 0 ELSE 1 END
            LIMIT 1
            """,
            req.slug,
        )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if not provider["is_claimed"]:
        raise HTTPException(status_code=403, detail="Provider must be claimed before upgrading the listing.")

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
        success_url=f"{settings.app_url}/provider-dashboard/{req.slug}?upgraded=1",
        cancel_url=f"{settings.app_url}/provider-dashboard/{req.slug}",
        metadata={
            "type": "profile",
            "slug": req.slug,
            "provider_id": str(provider["id"]),
            "tier": req.tier,
        },
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/subscription")
async def get_subscription(_auth: dict = Depends(validate_api_key)) -> dict:
    """Return the active subscription and plan entitlements for the authenticated user."""
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")

    async with get_connection() as conn:
        sub = await conn.fetchrow(
            """
            SELECT tier, status, included_users, extra_seats, max_users, seat_price_gbp, stripe_subscription_id
            FROM subscriptions
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
        )

    stored_tier = sub["tier"] if sub else None
    effective_tier = max_tier(_auth.get("tier", "free"), stored_tier)
    extra_seats = int(sub["extra_seats"] or 0) if sub else 0
    entitlements = get_subscription_entitlements(effective_tier, extra_seats)
    return {
        "tier": effective_tier,
        "status": sub["status"] if sub else "active",
        "stripe_subscription_id": sub["stripe_subscription_id"] if sub else None,
        "entitlements": entitlements,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events.

    Atomicity guarantee: the event is marked as processed inside the same DB
    transaction that mutates subscription state. If the handler raises, the
    transaction rolls back and the event_id is NOT recorded, so Stripe's retry
    will re-deliver and the handler will run again cleanly.
    """
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

    event_id = event["id"]
    event_type = event["type"]
    data = event["data"]["object"]

    async with get_connection() as conn:
        async with conn.transaction():
            # Dedup check inside the transaction — concurrent deliveries of the
            # same event_id will block here; only one INSERT wins; the loser
            # sees inserted=None and returns immediately without doing any work.
            inserted = await conn.fetchval(
                """INSERT INTO stripe_processed_events (event_id)
                   VALUES ($1) ON CONFLICT DO NOTHING RETURNING event_id""",
                event_id,
            )
            if not inserted:
                logger.info("Duplicate Stripe event %s — skipping", event_id)
                return {"status": "ok"}

            # All handler DB mutations share this transaction. On any exception
            # the transaction rolls back and the event_id insert is undone so
            # Stripe's next retry will process the event fresh.
            if event_type == "checkout.session.completed":
                await _handle_checkout_completed(conn, data)
            elif event_type == "customer.subscription.updated":
                await _handle_subscription_updated(conn, data)
            elif event_type == "customer.subscription.deleted":
                await _handle_subscription_deleted(conn, data)
            else:
                logger.info("Unhandled Stripe event: %s", event_type)

            # Expire old dedup entries (keep last 24 h). Non-critical; runs
            # inside the transaction but the DELETE is cheap.
            await conn.execute(
                "DELETE FROM stripe_processed_events WHERE processed_at < NOW() - INTERVAL '24 hours'"
            )

    return {"status": "ok"}


async def _handle_checkout_completed(conn, session: dict) -> None:
    """Route completed checkout to B2B or provider profile handler."""
    if session.get("metadata", {}).get("type") == "profile":
        await _handle_profile_checkout_completed(conn, session)
        return

    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier")
    extra_seats = int(session.get("metadata", {}).get("extra_seats", "0") or 0)
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    price_id = session.get("metadata", {}).get("price_id")

    if not user_id:
        raise RuntimeError("checkout.session.completed missing user_id metadata")
    if tier not in {"starter", "pro", "business"}:
        raise RuntimeError(f"checkout.session.completed has invalid tier metadata: {tier!r}")
    if not subscription_id:
        raise RuntimeError("checkout.session.completed missing subscription id")
    if price_id and PRICE_TO_TIER.get(price_id) != tier:
        raise RuntimeError(
            f"checkout.session.completed price/tier mismatch: price_id={price_id!r} tier={tier!r}"
        )

    await _persist_subscription_state(
        conn,
        int(user_id),
        subscription_id,
        tier,
        "active",
        stripe_price_id=price_id,
        extra_seats=extra_seats,
    )

    if customer_id:
        await conn.execute(
            "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
            customer_id, int(user_id),
        )

    logger.info("User %s upgraded to %s (subscription: %s)", user_id, tier, subscription_id)


async def _handle_subscription_updated(conn, subscription: dict) -> None:
    """Handle subscription changes (upgrade/downgrade)."""
    sub_id = subscription.get("id")
    status = subscription.get("status", "active")
    price_id = None
    extra_seats = 0
    unknown_price_ids: list[str] = []
    items = subscription.get("items", {}).get("data", [])
    if items:
        for item in items:
            item_price_id = item.get("price", {}).get("id")
            mapped = PRICE_TO_TIER.get(item_price_id)
            if mapped in {"starter", "pro", "business"}:
                price_id = item_price_id
            elif mapped == "pro-seat":
                extra_seats += int(item.get("quantity") or 0)
            elif item_price_id:
                unknown_price_ids.append(item_price_id)

    sub_row = await conn.fetchrow(
        "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
    )
    if not sub_row:
        logger.info("Subscription %s updated but no B2B subscription row exists; skipping", sub_id)
        return

    if unknown_price_ids or not price_id:
        raise RuntimeError(
            f"subscription.updated cannot map base price for subscription {sub_id}: "
            f"base_price={price_id!r}, unknown_prices={unknown_price_ids!r}"
        )

    tier = PRICE_TO_TIER[price_id]
    await _persist_subscription_state(
        conn,
        sub_row["user_id"],
        sub_id,
        tier,
        status,
        stripe_price_id=price_id,
        extra_seats=extra_seats,
    )

    logger.info("Subscription %s updated: tier=%s status=%s", sub_id, tier, status)


async def _handle_subscription_deleted(conn, subscription: dict) -> None:
    """Downgrade to free on cancellation (B2B) or to claimed on cancellation (profile)."""
    sub_id = subscription.get("id")

    # B2B plan cancellation
    sub_row = await conn.fetchrow(
        "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
    )
    if sub_row:
        await _persist_subscription_state(
            conn,
            sub_row["user_id"],
            sub_id,
            "free",
            "canceled",
            extra_seats=0,
        )
        logger.info("Subscription %s canceled, user downgraded to free", sub_id)

    # Provider profile cancellation
    await conn.execute(
        """UPDATE care_providers
           SET profile_tier = 'claimed', profile_subscription_id = NULL
           WHERE profile_subscription_id = $1""",
        sub_id,
    )


async def _handle_profile_checkout_completed(conn, session: dict) -> None:
    """Activate provider listing tier after successful profile checkout."""
    slug = session.get("metadata", {}).get("slug")
    tier = session.get("metadata", {}).get("tier")
    subscription_id = session.get("subscription")

    if not slug or not tier:
        raise RuntimeError("profile checkout completed with missing slug or tier metadata")
    if tier not in _PROFILE_TIERS:
        raise RuntimeError(f"profile checkout completed with invalid tier metadata: {tier!r}")
    if not subscription_id:
        raise RuntimeError("profile checkout completed without subscription id")

    result = await conn.execute(
        """UPDATE care_providers
           SET profile_tier = $1, profile_subscription_id = $2
           WHERE slug = $3""",
        tier, subscription_id, slug,
    )
    if result == "UPDATE 0":
        raise RuntimeError(f"profile checkout completed for unknown provider slug: {slug!r}")

    logger.info("Provider %s upgraded to profile tier %s (subscription: %s)", slug, tier, subscription_id)
