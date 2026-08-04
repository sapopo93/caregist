"""Stripe billing: checkout, webhooks, and subscription management."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from api.middleware.auth import validate_billing_identity

from api.config import (
    allows_extra_seats,
    max_tier,
    get_subscription_entitlements,
    get_tier_config,
    get_tier_rank,
    settings,
)
from api.database import get_connection
from api.utils.audit import actor_from_auth, write_audit_log

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


CHECKOUT_TIERS = {"alerts-pro", "starter", "pro", "business"}
ENTITLED_SUBSCRIPTION_STATUSES = {"active", "trialing"}
CHECKOUT_TIER_ALIASES = {
    "data-starter": "starter",
    "data-pro": "pro",
    "data-business": "business",
}


def _normalize_checkout_tier(tier: str) -> str:
    normalized = "-".join(tier.strip().lower().replace("_", "-").split())
    return CHECKOUT_TIER_ALIASES.get(normalized, normalized)


def _is_base_plan_price(price_id: str | None) -> bool:
    return PRICE_TO_TIER.get(price_id) in CHECKOUT_TIERS


def _request_fingerprint(*state: object) -> str:
    return hashlib.sha256("\x1f".join(str(value) for value in state).encode()).hexdigest()


async def _reserve_billing_operation(
    conn,
    *,
    owner_type: str,
    owner_id: str,
    operation_type: str,
    fingerprint: str,
    lifetime: timedelta,
) -> dict:
    """Create or recover the one pending Stripe operation for a billing owner."""
    await conn.execute(
        """
        UPDATE billing_operations
        SET status = 'expired', updated_at = NOW()
        WHERE owner_type = $1 AND owner_id = $2 AND operation_type = $3
          AND status = 'pending' AND expires_at <= NOW()
        """,
        owner_type,
        owner_id,
        operation_type,
    )
    expires_at = datetime.now(timezone.utc) + lifetime
    created = await conn.fetchrow(
        """
        INSERT INTO billing_operations (
            owner_type, owner_id, operation_type, request_fingerprint, expires_at
        )
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (owner_type, owner_id, operation_type)
          WHERE status = 'pending'
        DO NOTHING
        RETURNING id, request_fingerprint, stripe_object_id, stripe_object_url, expires_at
        """,
        owner_type,
        owner_id,
        operation_type,
        fingerprint,
        expires_at,
    )
    if created:
        return dict(created)
    pending = await conn.fetchrow(
        """
        SELECT id, request_fingerprint, stripe_object_id, stripe_object_url, expires_at
        FROM billing_operations
        WHERE owner_type = $1 AND owner_id = $2 AND operation_type = $3
          AND status = 'pending'
        FOR UPDATE
        """,
        owner_type,
        owner_id,
        operation_type,
    )
    if not pending:
        raise RuntimeError("Could not reserve a billing operation after resolving a concurrent request")
    if pending["request_fingerprint"] != fingerprint:
        raise HTTPException(
            status_code=409,
            detail="Another billing change is already in progress. Complete it or wait for it to expire.",
        )
    return dict(pending)


async def _record_operation_object(conn, operation_id: object, *, object_id: str, object_url: str | None = None) -> None:
    await conn.execute(
        """
        UPDATE billing_operations
        SET stripe_object_id = $1, stripe_object_url = $2, updated_at = NOW()
        WHERE id = $3 AND status = 'pending'
        """,
        object_id,
        object_url,
        operation_id,
    )


async def _complete_operation(conn, operation_id: object) -> None:
    await conn.execute(
        "UPDATE billing_operations SET status = 'succeeded', updated_at = NOW() WHERE id = $1 AND status = 'pending'",
        operation_id,
    )


async def _complete_pending_owner_operations(
    conn,
    *,
    owner_type: str,
    owner_id: str,
    operation_type: str,
    stripe_object_id: str,
) -> None:
    await conn.execute(
        """
        UPDATE billing_operations
        SET status = 'succeeded', updated_at = NOW()
        WHERE owner_type = $1 AND owner_id = $2 AND operation_type = $3
          AND stripe_object_id = $4 AND status = 'pending'
        """,
        owner_type,
        owner_id,
        operation_type,
        stripe_object_id,
    )


def _b2b_subscription_state(
    subscription: dict,
    *,
    known_price_id: str | None = None,
    known_tier: str | None = None,
    known_seat_price_id: str | None = None,
) -> tuple[str, str, str, int]:
    metadata = subscription.get("metadata", {})
    known_price_id = known_price_id or metadata.get("price_id")
    known_tier = known_tier or metadata.get("tier")
    known_seat_price_id = known_seat_price_id or metadata.get("seat_price_id")
    status = subscription.get("status") or "unknown"
    base_items: list[tuple[str, str]] = []
    unknown_price_ids: list[str] = []
    extra_seats = 0
    for item in subscription.get("items", {}).get("data", []):
        item_price_id = item.get("price", {}).get("id")
        mapped = PRICE_TO_TIER.get(item_price_id)
        if known_price_id and item_price_id == known_price_id and known_tier in CHECKOUT_TIERS:
            mapped = known_tier
        elif known_seat_price_id and item_price_id == known_seat_price_id:
            mapped = "pro-seat"
        if mapped in CHECKOUT_TIERS:
            base_items.append((item_price_id, mapped))
        elif mapped == "pro-seat":
            extra_seats += int(item.get("quantity") or 0)
        elif item_price_id:
            unknown_price_ids.append(item_price_id)
    if len(base_items) != 1 or unknown_price_ids:
        raise RuntimeError(
            "subscription.updated cannot map base price exactly once: "
            f"mapped_prices={base_items!r}, unknown_prices={unknown_price_ids!r}"
        )
    price_id, tier = base_items[0]
    return status, price_id, tier, extra_seats


def _profile_subscription_state(
    subscription: dict,
    *,
    known_price_id: str | None = None,
    known_tier: str | None = None,
) -> tuple[str, str, str]:
    metadata = subscription.get("metadata", {})
    known_price_id = known_price_id or metadata.get("price_id")
    known_tier = known_tier or metadata.get("tier")
    status = subscription.get("status") or "unknown"
    mapped_items: list[tuple[str, str]] = []
    unknown_price_ids: list[str] = []
    for item in subscription.get("items", {}).get("data", []):
        item_price_id = item.get("price", {}).get("id")
        mapped = PRICE_TO_PROFILE_TIER.get(item_price_id)
        if known_price_id and item_price_id == known_price_id and known_tier in _PROFILE_TIERS:
            mapped = known_tier
        if mapped in _PROFILE_TIERS:
            mapped_items.append((item_price_id, mapped))
        elif item_price_id:
            unknown_price_ids.append(item_price_id)
    if len(mapped_items) != 1 or unknown_price_ids:
        raise RuntimeError(
            "profile subscription.updated cannot map one profile price exactly: "
            f"mapped_prices={mapped_items!r}, unknown_prices={unknown_price_ids!r}"
        )
    price_id, tier = mapped_items[0]
    return status, price_id, tier


class CheckoutRequest(BaseModel):
    email: EmailStr
    tier: str  # "alerts-pro", "starter", "pro", or "business"
    extra_seats: int | None = Field(None, ge=0, le=50)

    model_config = {"extra": "forbid"}


def _require_billing_user_id(auth: dict) -> int:
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authenticated user account required.")
    return int(user_id)


def _verify_request_email(req_email: str, account_email: str) -> None:
    if req_email.strip().casefold() != account_email.strip().casefold():
        raise HTTPException(status_code=403, detail="Checkout is only available for the authenticated account.")


def _normalize_extra_seats(tier: str, extra_seats: int) -> int:
    if extra_seats <= 0:
        return 0
    if not allows_extra_seats(tier):
        raise HTTPException(status_code=422, detail=f"Extra seats are not available on the {tier.title()} plan.")
    if not settings.stripe_price_pro_seat:
        raise HTTPException(status_code=503, detail="Seat add-on checkout is not configured yet. Contact support to add users.")
    return extra_seats


def _configured_base_price_for_tier(tier: str) -> str | None:
    price_map = {
        "alerts-pro": settings.stripe_price_alerts_pro,
        "starter": settings.stripe_price_starter,
        "pro": settings.stripe_price_pro,
        "business": settings.stripe_price_business,
    }
    return price_map.get(tier) or None


def _base_price_for_tier(tier: str) -> str:
    price_id = _configured_base_price_for_tier(tier)
    if not price_id:
        logger.error("Stripe checkout price missing for tier=%s", tier)
        raise HTTPException(status_code=503, detail=f"Checkout for the {tier} plan is not yet configured. Contact support@caregist.co.uk.")
    return price_id


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
        """
        WITH effective AS (
            SELECT COALESCE(
                (
                    SELECT tier
                    FROM subscriptions
                    WHERE user_id = $1
                      AND status IN ('active', 'trialing')
                    ORDER BY CASE tier
                        WHEN 'business' THEN 4
                        WHEN 'pro' THEN 3
                        WHEN 'starter' THEN 2
                        WHEN 'alerts-pro' THEN 1
                        ELSE 0
                    END DESC, created_at DESC
                    LIMIT 1
                ),
                'free'
            ) AS tier
        )
        UPDATE api_keys
        SET tier = effective.tier,
            rate_limit = CASE effective.tier
                WHEN 'business' THEN $2::int
                WHEN 'pro' THEN $3::int
                WHEN 'starter' THEN $4::int
                WHEN 'alerts-pro' THEN $5::int
                ELSE $6::int
            END
        FROM effective
        WHERE user_id = $1 AND is_active = true
        """,
        user_id,
        get_tier_config("business")["rate"],
        get_tier_config("pro")["rate"],
        get_tier_config("starter")["rate"],
        get_tier_config("alerts-pro")["rate"],
        get_tier_config("free")["rate"],
    )


@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, _auth: dict = Depends(validate_billing_identity)) -> dict:
    """Create a Stripe Checkout session for upgrading."""
    user_id = _require_billing_user_id(_auth)
    if not _auth.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before starting billing.")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    tier = _normalize_checkout_tier(req.tier)
    if tier == "free":
        raise HTTPException(status_code=422, detail="The Free plan does not require checkout. Create an account to start free.")
    if tier not in CHECKOUT_TIERS:
        if tier == "enterprise":
            raise HTTPException(
                status_code=422,
                detail="Enterprise plans require custom setup. Contact enterprise@caregist.co.uk to get started.",
            )
        raise HTTPException(status_code=400, detail=f"Invalid tier: {req.tier}. Choose 'alerts-pro', 'starter', 'pro', or 'business'.")

    requested_extra_seats = req.extra_seats

    # Find or create Stripe customer
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id, email, stripe_customer_id FROM users WHERE id = $1", user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user account required.")
    _verify_request_email(req.email, user["email"])

    # Prevent double-charge: reject if user already has an active paid subscription
    async with get_connection() as conn:
        existing_sub = await conn.fetchrow(
            """
            SELECT tier, status, stripe_subscription_id, stripe_price_id, extra_seats
            FROM subscriptions
            WHERE user_id = $1
              AND status NOT IN ('canceled', 'incomplete_expired')
              AND tier != 'free'
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
        existing_tier = _normalize_checkout_tier(existing_sub["tier"] or "")
        subscription = stripe.Subscription.retrieve(subscription_id)
        if subscription.get("customer") != user.get("stripe_customer_id"):
            raise HTTPException(
                status_code=409,
                detail="This subscription is not linked to the authenticated billing customer. Contact support.",
            )
        stripe_status = subscription.get("status") or "unknown"
        if stripe_status not in ENTITLED_SUBSCRIPTION_STATUSES:
            async with get_connection() as conn:
                async with conn.transaction():
                    await _persist_subscription_state(
                        conn,
                        int(user["id"]),
                        subscription_id,
                        existing_tier,
                        stripe_status or "unknown",
                        stripe_price_id=existing_sub.get("stripe_price_id"),
                        extra_seats=int(existing_sub.get("extra_seats") or 0),
                    )
            raise HTTPException(
                status_code=409,
                detail="Your Stripe subscription is not active. Resolve its billing status before changing plan.",
            )
        stripe_status, source_price_id, source_tier, source_extra_seats = _b2b_subscription_state(
            subscription,
            known_price_id=existing_sub.get("stripe_price_id"),
            known_tier=existing_tier,
        )
        if requested_extra_seats and get_tier_rank(source_tier) > get_tier_rank(tier):
            tier = source_tier
        desired_extra_seats = (
            source_extra_seats
            if requested_extra_seats is None and allows_extra_seats(tier)
            else int(requested_extra_seats or 0)
        )
        if tier == source_tier and desired_extra_seats == source_extra_seats:
            async with get_connection() as conn:
                async with conn.transaction():
                    await _persist_subscription_state(
                        conn,
                        int(user["id"]),
                        subscription_id,
                        source_tier,
                        stripe_status,
                        stripe_price_id=source_price_id,
                        extra_seats=source_extra_seats,
                    )
                    await _complete_pending_owner_operations(
                        conn,
                        owner_type="account",
                        owner_id=str(user["id"]),
                        operation_type="subscription_change",
                        stripe_object_id=subscription_id,
                    )
            return {
                "updated": True,
                "tier": tier,
                "extra_seats": source_extra_seats,
                "unchanged": True,
            }
        extra_seats = _normalize_extra_seats(tier, desired_extra_seats)
        items = subscription.get("items", {}).get("data", [])
        configured_base_price_id = _configured_base_price_for_tier(tier)
        base_item = next((item for item in items if item.get("price", {}).get("id") == source_price_id), None)
        if not base_item or not base_item.get("id"):
            raise HTTPException(
                status_code=409,
                detail="The current Stripe base plan item could not be identified safely. Contact support.",
            )
        seat_item = next((item for item in items if PRICE_TO_TIER.get(item.get("price", {}).get("id")) == "pro-seat"), None)

        updated_items: list[dict] = []
        if configured_base_price_id:
            updated_items.append({"id": base_item["id"], "price": configured_base_price_id, "quantity": 1})
        elif tier != source_tier:
            _base_price_for_tier(tier)

        if seat_item and extra_seats <= 0:
            updated_items.append({"id": seat_item["id"], "deleted": True})
        elif seat_item and extra_seats > 0:
            updated_items.append({"id": seat_item["id"], "price": settings.stripe_price_pro_seat, "quantity": extra_seats})
        elif extra_seats > 0:
            updated_items.append({"price": settings.stripe_price_pro_seat, "quantity": extra_seats})

        operation_fingerprint = _request_fingerprint(
            source_price_id,
            source_extra_seats,
            configured_base_price_id or source_price_id,
            extra_seats,
        )
        async with get_connection() as conn:
            operation = await _reserve_billing_operation(
                conn,
                owner_type="account",
                owner_id=str(user["id"]),
                operation_type="subscription_change",
                fingerprint=operation_fingerprint,
                lifetime=timedelta(minutes=15),
            )
            await _record_operation_object(conn, operation["id"], object_id=subscription_id)

        changed_subscription = subscription
        if updated_items:
            changed_subscription = stripe.Subscription.modify(
                subscription_id,
                items=updated_items,
                proration_behavior="always_invoice",
                payment_behavior="error_if_incomplete",
                metadata={
                    "user_id": str(user["id"]),
                    "tier": tier,
                    "extra_seats": str(extra_seats),
                    "price_id": configured_base_price_id or source_price_id,
                    "seat_price_id": settings.stripe_price_pro_seat if extra_seats else "",
                },
                idempotency_key=f"caregist-subscription-change-{operation['id']}",
            )
        changed_status, changed_price_id, changed_tier, changed_extra_seats = _b2b_subscription_state(
            changed_subscription,
            known_price_id=configured_base_price_id or source_price_id,
            known_tier=tier,
        )
        if changed_status not in ENTITLED_SUBSCRIPTION_STATUSES:
            raise RuntimeError(
                "Stripe returned a non-entitled status after changing the account subscription"
            )
        if changed_tier != tier or changed_extra_seats != extra_seats:
            raise RuntimeError(
                "Stripe returned subscription items that do not match the requested account plan change"
            )
        async with get_connection() as conn:
            async with conn.transaction():
                await _persist_subscription_state(
                    conn,
                    int(user["id"]),
                    subscription_id,
                    tier,
                    changed_status,
                    stripe_price_id=changed_price_id,
                    extra_seats=extra_seats,
                )
                await write_audit_log(
                    action="billing.subscription.update",
                    outcome="success",
                    actor=actor_from_auth(_auth),
                    target_type="subscription",
                    target_id=subscription_id,
                    metadata={"tier": tier, "extra_seats": extra_seats},
                    conn=conn,
                )
                await _complete_operation(conn, operation["id"])
        return {"updated": True, "tier": tier, "extra_seats": extra_seats}

    extra_seats = _normalize_extra_seats(tier, int(requested_extra_seats or 0))
    price_id = _base_price_for_tier(tier)

    customer_id = user["stripe_customer_id"]
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            idempotency_key=f"caregist-customer-user-{user['id']}",
        )
        customer_id = customer.id
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
                customer_id, user["id"],
            )

    async with get_connection() as conn:
        operation = await _reserve_billing_operation(
            conn,
            owner_type="account",
            owner_id=str(user["id"]),
            operation_type="checkout",
            fingerprint=_request_fingerprint(customer_id, tier, extra_seats, price_id),
            lifetime=timedelta(minutes=31),
        )
    if operation.get("stripe_object_id") and operation.get("stripe_object_url"):
        stripe_mode = "test" if settings.stripe_secret_key.startswith("sk_test_") else "live"
        return {
            "checkout_url": operation["stripe_object_url"],
            "session_id": operation["stripe_object_id"],
            "stripe_mode": stripe_mode,
            "reused": True,
        }

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[
            {"price": price_id, "quantity": 1},
            *([{"price": settings.stripe_price_pro_seat, "quantity": extra_seats}] if extra_seats else []),
        ],
        mode="subscription",
        subscription_data={
            "metadata": {
                "user_id": str(user["id"]),
                "tier": tier,
                "extra_seats": str(extra_seats),
                "price_id": price_id,
                **({"seat_price_id": settings.stripe_price_pro_seat} if extra_seats else {}),
            }
        },
        success_url=f"{settings.app_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url}/pricing",
        expires_at=int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        metadata={
            "user_id": str(user["id"]),
            "tier": tier,
            "extra_seats": str(extra_seats),
            "price_id": price_id,
            **({"seat_price_id": settings.stripe_price_pro_seat} if extra_seats else {}),
        },
        idempotency_key=f"caregist-checkout-{operation['id']}",
    )
    async with get_connection() as conn:
        await _record_operation_object(
            conn,
            operation["id"],
            object_id=session.id,
            object_url=session.url,
        )
        await write_audit_log(
            action="billing.checkout.create",
            outcome="success",
            actor=actor_from_auth(_auth),
            target_type="checkout_session",
            target_id=session.id,
            metadata={"tier": tier, "extra_seats": extra_seats},
            conn=conn,
        )

    stripe_mode = "test" if settings.stripe_secret_key.startswith("sk_test_") else "live"
    return {"checkout_url": session.url, "session_id": session.id, "stripe_mode": stripe_mode}


_PROFILE_TIERS = {"enhanced", "premium", "sponsored"}


def _configured_profile_price_for_tier(tier: str) -> str | None:
    price_map = {
        "enhanced": settings.stripe_price_profile_enhanced,
        "premium": settings.stripe_price_profile_premium,
        "sponsored": settings.stripe_price_profile_sponsored,
    }
    return price_map.get(tier) or None


class ProfileCheckoutRequest(BaseModel):
    slug: str
    tier: str
    email: EmailStr

    model_config = {"extra": "forbid"}


@router.post("/profile-checkout")
async def create_profile_checkout(
    req: ProfileCheckoutRequest,
    _auth: dict = Depends(validate_billing_identity),
) -> dict:
    """Create a Stripe Checkout session for a provider listing tier upgrade."""
    user_id = _require_billing_user_id(_auth)
    if not _auth.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before starting billing.")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    if req.tier not in _PROFILE_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid profile tier: {req.tier}. Choose from {sorted(_PROFILE_TIERS)}.")

    price_id = _configured_profile_price_for_tier(req.tier)
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Checkout for the {req.tier} profile tier is not yet configured.")

    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id, email, stripe_customer_id FROM users WHERE id = $1", user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user account required.")
    _verify_request_email(req.email, user["email"])

    async with get_connection() as conn:
        provider = await conn.fetchrow(
            """
            SELECT id, is_claimed, profile_tier, profile_subscription_id
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

    async with get_connection() as conn:
        approved_claim = await conn.fetchrow(
            """SELECT id FROM provider_claims
               WHERE provider_id = $1 AND status = 'approved'
               AND claimant_email = (SELECT email FROM users WHERE id = $2)""",
            provider["id"], user_id,
        )
    if not approved_claim:
        raise HTTPException(status_code=403, detail="You don't have an approved claim for this provider.")
    existing_subscription_id = provider.get("profile_subscription_id")
    existing_tier = provider.get("profile_tier")
    if existing_subscription_id or existing_tier in _PROFILE_TIERS:
        if not existing_subscription_id or existing_tier not in _PROFILE_TIERS:
            raise HTTPException(
                status_code=409,
                detail="This provider's paid listing cannot be changed automatically. Contact support.",
            )
        subscription = stripe.Subscription.retrieve(existing_subscription_id)
        if subscription.get("customer") != user.get("stripe_customer_id"):
            raise HTTPException(
                status_code=409,
                detail="This listing subscription belongs to a different billing customer. Contact support to transfer it.",
            )
        source_status = subscription.get("status") or "unknown"
        if source_status not in ENTITLED_SUBSCRIPTION_STATUSES:
            raise HTTPException(
                status_code=409,
                detail="This provider's subscription is not active. Resolve its billing status before changing plan.",
            )
        source_status, source_price_id, source_tier = _profile_subscription_state(subscription)
        if source_tier == req.tier:
            async with get_connection() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE care_providers SET profile_tier = $1 WHERE id = $2 AND profile_subscription_id = $3",
                        source_tier,
                        provider["id"],
                        existing_subscription_id,
                    )
                    await _complete_pending_owner_operations(
                        conn,
                        owner_type="provider",
                        owner_id=str(provider["id"]),
                        operation_type="profile_change",
                        stripe_object_id=existing_subscription_id,
                    )
            return {"updated": True, "tier": req.tier, "unchanged": True}

        base_item = next(
            (
                item for item in subscription.get("items", {}).get("data", [])
                if item.get("price", {}).get("id") == source_price_id
            ),
            None,
        )
        if not base_item or not base_item.get("id"):
            raise HTTPException(
                status_code=409,
                detail="This provider's Stripe subscription does not match its current plan. Contact support.",
            )

        async with get_connection() as conn:
            operation = await _reserve_billing_operation(
                conn,
                owner_type="provider",
                owner_id=str(provider["id"]),
                operation_type="profile_change",
                fingerprint=_request_fingerprint(source_price_id, price_id),
                lifetime=timedelta(minutes=15),
            )
            await _record_operation_object(conn, operation["id"], object_id=existing_subscription_id)

        changed_subscription = stripe.Subscription.modify(
            existing_subscription_id,
            items=[{"id": base_item["id"], "price": price_id, "quantity": 1}],
            proration_behavior="always_invoice",
            payment_behavior="error_if_incomplete",
            metadata={
                "type": "profile",
                "slug": req.slug,
                "provider_id": str(provider["id"]),
                "tier": req.tier,
                "price_id": price_id,
            },
            idempotency_key=f"caregist-profile-change-{operation['id']}",
        )
        changed_status, changed_price_id, changed_tier = _profile_subscription_state(changed_subscription)
        if changed_status not in ENTITLED_SUBSCRIPTION_STATUSES:
            raise RuntimeError(
                "Stripe returned a non-entitled status after changing the profile subscription"
            )
        if changed_price_id != price_id or changed_tier != req.tier:
            raise RuntimeError("Stripe returned a profile plan that does not match the requested change")
        async with get_connection() as conn:
            async with conn.transaction():
                update_result = await conn.execute(
                    "UPDATE care_providers SET profile_tier = $1 WHERE id = $2 AND profile_subscription_id = $3",
                    req.tier, provider["id"], existing_subscription_id,
                )
                if update_result == "UPDATE 0":
                    raise RuntimeError(
                        "Stripe changed the profile subscription, but the local provider link no longer matches"
                    )
                await write_audit_log(
                    action="billing.profile_subscription.update",
                    outcome="success",
                    actor=actor_from_auth(_auth),
                    target_type="provider",
                    target_id=str(provider["id"]),
                    metadata={
                        "subscription_id": existing_subscription_id,
                        "previous_tier": existing_tier,
                        "tier": req.tier,
                    },
                    conn=conn,
                )
                await _complete_operation(conn, operation["id"])
        return {"updated": True, "tier": req.tier, "unchanged": False}

    customer_id = user["stripe_customer_id"]
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            idempotency_key=f"caregist-customer-user-{user['id']}",
        )
        customer_id = customer.id
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
                customer_id, user["id"],
            )

    async with get_connection() as conn:
        operation = await _reserve_billing_operation(
            conn,
            owner_type="provider",
            owner_id=str(provider["id"]),
            operation_type="profile_checkout",
            fingerprint=_request_fingerprint(customer_id, provider["id"], req.tier, price_id),
            lifetime=timedelta(minutes=31),
        )
    if operation.get("stripe_object_id") and operation.get("stripe_object_url"):
        stripe_mode = "test" if settings.stripe_secret_key.startswith("sk_test_") else "live"
        return {
            "checkout_url": operation["stripe_object_url"],
            "session_id": operation["stripe_object_id"],
            "stripe_mode": stripe_mode,
            "reused": True,
        }

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        subscription_data={
            "metadata": {
                "type": "profile",
                "slug": req.slug,
                "provider_id": str(provider["id"]),
                "tier": req.tier,
                "price_id": price_id,
            }
        },
        success_url=f"{settings.app_url}/provider-dashboard/{req.slug}?upgraded=1",
        cancel_url=f"{settings.app_url}/provider-dashboard/{req.slug}",
        expires_at=int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        metadata={
            "type": "profile",
            "slug": req.slug,
            "provider_id": str(provider["id"]),
            "tier": req.tier,
            "price_id": price_id,
        },
        idempotency_key=f"caregist-profile-checkout-{operation['id']}",
    )
    async with get_connection() as conn:
        await _record_operation_object(
            conn,
            operation["id"],
            object_id=session.id,
            object_url=session.url,
        )
        await write_audit_log(
            action="billing.profile_checkout.create",
            outcome="success",
            actor=actor_from_auth(_auth),
            target_type="checkout_session",
            target_id=session.id,
            metadata={"provider_id": str(provider["id"]), "slug": req.slug, "tier": req.tier},
            conn=conn,
        )

    stripe_mode = "test" if settings.stripe_secret_key.startswith("sk_test_") else "live"
    return {"checkout_url": session.url, "session_id": session.id, "stripe_mode": stripe_mode}


@router.get("/subscription")
async def get_subscription(_auth: dict = Depends(validate_billing_identity)) -> dict:
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
            ORDER BY
              CASE WHEN status IN ('active', 'trialing') THEN 1 ELSE 0 END DESC,
              CASE tier
                WHEN 'business' THEN 4
                WHEN 'pro' THEN 3
                WHEN 'starter' THEN 2
                WHEN 'alerts-pro' THEN 1
                ELSE 0
              END DESC,
              created_at DESC
            LIMIT 1
            """,
            user_id,
        )

    status = sub["status"] if sub else "active"
    stored_tier = sub["tier"] if sub and status in ENTITLED_SUBSCRIPTION_STATUSES else None
    effective_tier = (
        max_tier(_auth.get("tier", "free"), stored_tier)
        if status in ENTITLED_SUBSCRIPTION_STATUSES
        else "free"
    )
    extra_seats = int(sub["extra_seats"] or 0) if sub and status in ENTITLED_SUBSCRIPTION_STATUSES else 0
    entitlements = get_subscription_entitlements(effective_tier, extra_seats)
    return {
        "tier": effective_tier,
        "status": status,
        "stripe_subscription_id": sub["stripe_subscription_id"] if sub else None,
        "entitlements": entitlements,
    }


@router.post("/portal")
async def create_billing_portal(_auth: dict = Depends(validate_billing_identity)) -> dict:
    """Open Stripe's customer-owned billing portal for cancellation and invoices."""
    user_id = _require_billing_user_id(_auth)
    if not _auth.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before managing billing.")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT stripe_customer_id FROM users WHERE id = $1",
            user_id,
        )
    if not user or not user.get("stripe_customer_id"):
        raise HTTPException(status_code=409, detail="No Stripe billing account is linked to this user.")
    session = stripe.billing_portal.Session.create(
        customer=user["stripe_customer_id"],
        return_url=f"{settings.app_url}/dashboard",
    )
    if not session.get("url"):
        raise RuntimeError("Stripe billing portal did not return a secure URL")
    return {"portal_url": session["url"]}


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
            elif event_type == "checkout.session.expired":
                await conn.execute(
                    """
                    UPDATE billing_operations
                    SET status = 'expired', updated_at = NOW()
                    WHERE stripe_object_id = $1 AND status = 'pending'
                      AND operation_type IN ('checkout', 'profile_checkout')
                    """,
                    data.get("id"),
                )
            elif event_type == "customer.subscription.updated":
                subscription_id = data.get("id")
                if not subscription_id:
                    raise RuntimeError("customer.subscription.updated missing subscription id")
                authoritative = stripe.Subscription.retrieve(subscription_id)
                await _handle_subscription_updated(conn, authoritative)
            elif event_type == "customer.subscription.deleted":
                await _handle_subscription_deleted(conn, data)
            else:
                logger.info("Unhandled Stripe event: %s", event_type)

            # Retain event IDs across Stripe's retry and manual-redelivery
            # windows. This keeps a delayed duplicate from mutating an
            # entitlement twice while still bounding table growth.
            await conn.execute(
                "DELETE FROM stripe_processed_events WHERE processed_at < NOW() - INTERVAL '30 days'"
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
    seat_price_id = session.get("metadata", {}).get("seat_price_id")

    if not user_id:
        raise RuntimeError("checkout.session.completed missing user_id metadata")
    if tier not in CHECKOUT_TIERS:
        raise RuntimeError(f"checkout.session.completed has invalid tier metadata: {tier!r}")
    if not subscription_id:
        raise RuntimeError("checkout.session.completed missing subscription id")
    if session.get("payment_status") not in {"paid", "no_payment_required"}:
        raise RuntimeError(
            f"checkout.session.completed has non-paying payment_status={session.get('payment_status')!r}"
        )
    if price_id and PRICE_TO_TIER.get(price_id) not in {None, tier}:
        raise RuntimeError(
            f"checkout.session.completed price/tier mismatch: price_id={price_id!r} tier={tier!r}"
        )

    authoritative = stripe.Subscription.retrieve(subscription_id)
    if authoritative.get("customer") != customer_id:
        raise RuntimeError("checkout.session.completed subscription customer mismatch")
    status, actual_price_id, actual_tier, actual_extra_seats = _b2b_subscription_state(
        authoritative,
        known_price_id=price_id,
        known_tier=tier,
        known_seat_price_id=seat_price_id,
    )
    if actual_tier != tier or (price_id and actual_price_id != price_id) or actual_extra_seats != extra_seats:
        raise RuntimeError(
            "checkout.session.completed authoritative subscription does not match its approved metadata"
        )

    await _persist_subscription_state(
        conn,
        int(user_id),
        subscription_id,
        actual_tier,
        status,
        stripe_price_id=actual_price_id,
        extra_seats=actual_extra_seats,
    )
    await write_audit_log(
        action="billing.subscription.activate",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="subscription",
        target_id=subscription_id,
        metadata={
            "user_id": int(user_id),
            "tier": actual_tier,
            "status": status,
            "extra_seats": actual_extra_seats,
        },
        conn=conn,
    )

    if customer_id:
        await conn.execute(
            "UPDATE users SET stripe_customer_id = $1 WHERE id = $2",
            customer_id, int(user_id),
        )
    await conn.execute(
        """
        UPDATE billing_operations
        SET status = 'succeeded', updated_at = NOW()
        WHERE stripe_object_id = $1 AND owner_type = 'account'
          AND operation_type = 'checkout' AND status = 'pending'
        """,
        session.get("id"),
    )

    logger.info("User %s reconciled to %s/%s (subscription: %s)", user_id, actual_tier, status, subscription_id)


async def _handle_subscription_updated(conn, subscription: dict) -> None:
    """Handle subscription changes (upgrade/downgrade)."""
    sub_id = subscription.get("id")
    status = subscription.get("status") or "unknown"
    sub_row = await conn.fetchrow(
        "SELECT user_id, tier, stripe_price_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
    )
    if not sub_row:
        profile_row = await conn.fetchrow(
            "SELECT id, slug FROM care_providers WHERE profile_subscription_id = $1",
            sub_id,
        )
        if profile_row:
            if status not in {"active", "trialing"}:
                await conn.execute(
                    "UPDATE care_providers SET profile_tier = 'claimed' WHERE id = $1 AND profile_subscription_id = $2",
                    profile_row["id"],
                    sub_id,
                )
                await write_audit_log(
                    action="billing.profile_subscription.update",
                    outcome="success",
                    actor={"type": "system", "name": "stripe"},
                    target_type="provider",
                    target_id=str(profile_row["id"]),
                    metadata={
                        "subscription_id": sub_id,
                        "tier": "claimed",
                        "status": status,
                    },
                    conn=conn,
                )
                logger.warning(
                    "Profile subscription %s downgraded to claimed for non-entitled status=%s",
                    sub_id,
                    status,
                )
                return

            _, profile_price_id, profile_tier = _profile_subscription_state(subscription)
            await conn.execute(
                "UPDATE care_providers SET profile_tier = $1 WHERE id = $2 AND profile_subscription_id = $3",
                profile_tier, profile_row["id"], sub_id,
            )
            await write_audit_log(
                action="billing.profile_subscription.update",
                outcome="success",
                actor={"type": "system", "name": "stripe"},
                target_type="provider",
                target_id=str(profile_row["id"]),
                metadata={
                    "subscription_id": sub_id,
                    "tier": profile_tier,
                    "status": status,
                    "price_id": profile_price_id,
                },
                conn=conn,
            )
            logger.info("Profile subscription %s updated: tier=%s status=%s", sub_id, profile_tier, status)
            return

        logger.info("Subscription %s updated but no local subscription row exists; skipping", sub_id)
        return

    status, price_id, tier, extra_seats = _b2b_subscription_state(
        subscription,
        known_price_id=sub_row.get("stripe_price_id"),
        known_tier=_normalize_checkout_tier(sub_row.get("tier") or ""),
    )
    await _persist_subscription_state(
        conn,
        sub_row["user_id"],
        sub_id,
        tier,
        status,
        stripe_price_id=price_id,
        extra_seats=extra_seats,
    )
    await write_audit_log(
        action="billing.subscription.update",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="subscription",
        target_id=sub_id,
        metadata={"user_id": int(sub_row["user_id"]), "tier": tier, "status": status, "extra_seats": extra_seats},
        conn=conn,
    )

    logger.info("Subscription %s updated: tier=%s status=%s", sub_id, tier, status)


async def _handle_subscription_deleted(conn, subscription: dict) -> None:
    """Downgrade to free on cancellation (B2B) or to claimed on cancellation (profile)."""
    sub_id = subscription.get("id")

    # B2B plan cancellation
    sub_row = await conn.fetchrow(
        "SELECT user_id, tier, stripe_price_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
    )
    if sub_row:
        await _persist_subscription_state(
            conn,
            sub_row["user_id"],
            sub_id,
            _normalize_checkout_tier(sub_row.get("tier") or "free"),
            "canceled",
            stripe_price_id=sub_row.get("stripe_price_id"),
            extra_seats=0,
        )
        await write_audit_log(
            action="billing.subscription.cancel",
            outcome="success",
            actor={"type": "system", "name": "stripe"},
            target_type="subscription",
            target_id=sub_id,
            metadata={"user_id": int(sub_row["user_id"]), "effective_tier_recomputed": True},
            conn=conn,
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
    """Reconcile a completed provider checkout from Stripe's current subscription state."""
    slug = session.get("metadata", {}).get("slug")
    tier = session.get("metadata", {}).get("tier")
    provider_id = session.get("metadata", {}).get("provider_id")
    price_id = session.get("metadata", {}).get("price_id")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    if not slug or not tier or not provider_id:
        raise RuntimeError("profile checkout completed with missing slug or tier or provider metadata")
    if tier not in _PROFILE_TIERS:
        raise RuntimeError(f"profile checkout completed with invalid tier metadata: {tier!r}")
    if not subscription_id:
        raise RuntimeError("profile checkout completed without subscription id")
    if session.get("payment_status") not in {"paid", "no_payment_required"}:
        raise RuntimeError(
            f"profile checkout completed with non-paying payment_status={session.get('payment_status')!r}"
        )

    authoritative = stripe.Subscription.retrieve(subscription_id)
    if authoritative.get("customer") != customer_id:
        raise RuntimeError("profile checkout subscription customer mismatch")
    status, actual_price_id, actual_tier = _profile_subscription_state(
        authoritative,
        known_price_id=price_id,
        known_tier=tier,
    )
    if actual_tier != tier or (price_id and actual_price_id != price_id):
        raise RuntimeError("profile checkout authoritative plan does not match approved metadata")
    entitlement_tier = actual_tier if status in ENTITLED_SUBSCRIPTION_STATUSES else "claimed"

    result = await conn.execute(
        """UPDATE care_providers
           SET profile_tier = $1, profile_subscription_id = $2
           WHERE slug = $3 AND id = $4""",
        entitlement_tier, subscription_id, slug, provider_id,
    )
    if result == "UPDATE 0":
        raise RuntimeError(f"profile checkout completed for unknown provider slug: {slug!r}")
    await write_audit_log(
        action="billing.profile_subscription.activate",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="provider",
        target_id=slug,
        metadata={
            "tier": entitlement_tier,
            "purchased_tier": actual_tier,
            "status": status,
            "price_id": actual_price_id,
            "subscription_id": subscription_id,
        },
        conn=conn,
    )
    await conn.execute(
        """
        UPDATE billing_operations
        SET status = 'succeeded', updated_at = NOW()
        WHERE stripe_object_id = $1 AND owner_type = 'provider'
          AND operation_type = 'profile_checkout' AND status = 'pending'
        """,
        session.get("id"),
    )

    logger.info(
        "Provider %s reconciled to profile tier %s/%s (subscription: %s)",
        slug,
        entitlement_tier,
        status,
        subscription_id,
    )
