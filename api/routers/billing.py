"""Stripe billing: checkout, webhooks, and subscription management."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from api.middleware.auth import validate_billing_identity
from api.middleware.ip_rate_limit import _get_client_ip

from api.config import (
    allows_extra_seats,
    get_subscription_entitlements,
    get_tier_config,
    max_tier,
    settings,
)
from api.database import get_connection
from api.utils.audit import actor_from_auth, write_audit_log

logger = logging.getLogger("caregist.billing")
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

PRICE_TO_TIER = {}         # B2B data plan prices → tier name
PRICE_TO_PROFILE_TIER = {}  # Provider listing prices → profile tier name
BASE_PLAN_TIERS = {"alerts-pro", "starter", "pro", "business"}


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
        PRICE_TO_PROFILE_TIER[settings.stripe_price_profile_premium] = "enhanced"
    if settings.stripe_price_profile_sponsored:
        PRICE_TO_PROFILE_TIER[settings.stripe_price_profile_sponsored] = "sponsored"


def _is_base_plan_price(price_id: str | None) -> bool:
    return PRICE_TO_TIER.get(price_id) in BASE_PLAN_TIERS


CHECKOUT_TIERS = BASE_PLAN_TIERS
CHECKOUT_TIER_ALIASES = {
    "data-starter": "starter",
    "data-pro": "pro",
    "data-business": "business",
}


def _normalize_checkout_tier(tier: str) -> str:
    normalized = "-".join(tier.strip().lower().replace("_", "-").split())
    return CHECKOUT_TIER_ALIASES.get(normalized, normalized)


class CheckoutRequest(BaseModel):
    email: EmailStr
    tier: str  # "alerts-pro", "starter", "pro", or "business"
    extra_seats: int = Field(0, ge=0, le=50)
    terms_version: str = Field(min_length=1, max_length=100)
    business_use_confirmed: Literal[True]

    model_config = {"extra": "forbid"}


class SubscriptionChangeRequest(BaseModel):
    tier: str  # "alerts-pro", "starter", "pro", or "business"
    extra_seats: int = Field(0, ge=0, le=50)

    model_config = {"extra": "forbid"}


def _require_billing_user_id(auth: dict) -> int:
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authenticated user account required.")
    return int(user_id)


def _require_browser_billing_owner(auth: dict) -> int:
    """Reject API-key initiated commercial mutations, including team keys."""
    user_id = _require_billing_user_id(auth)
    if auth.get("auth_method") != "session":
        raise HTTPException(status_code=403, detail="Billing changes require an authenticated browser session.")
    return user_id


def _verify_request_email(req_email: str, account_email: str) -> None:
    if req_email.strip().casefold() != account_email.strip().casefold():
        raise HTTPException(status_code=403, detail="Checkout is only available for the authenticated account.")


def _verify_contract_acceptance(terms_version: str, business_use_confirmed: bool) -> None:
    approved = settings.b2b_terms_version.strip()
    approved_sha = settings.b2b_terms_sha256.strip().lower()
    if not approved or len(approved_sha) != 64 or any(c not in "0123456789abcdef" for c in approved_sha):
        raise HTTPException(status_code=503, detail="Paid checkout is awaiting approved B2B terms.")
    if terms_version.strip() != approved:
        raise HTTPException(status_code=409, detail="The B2B terms have changed. Review and accept the current version.")
    if business_use_confirmed is not True:
        raise HTTPException(status_code=422, detail="Business use and contracting authority must be confirmed.")


def _minimised_ip_evidence(request: Request) -> str | None:
    client_ip = _get_client_ip(request)
    if not client_ip:
        return None
    salt = settings.b2b_evidence_hash_key
    if not salt:
        return None
    return hashlib.sha256(f"{salt}:{client_ip}".encode("utf-8")).hexdigest()


async def _persist_contract_acceptance(
    conn,
    *,
    user_id: int,
    checkout_session_id: str,
    terms_version: str,
    request: Request,
) -> None:
    user_agent = request.headers.get("user-agent", "").strip()[:512] or None
    await conn.execute(
        """
        INSERT INTO b2b_contract_acceptances (
          user_id, stripe_checkout_session_id, terms_version, terms_sha256,
          business_use_confirmed, ip_address_hash, user_agent
        ) VALUES ($1, $2, $3, $4, TRUE, $5, $6)
        ON CONFLICT (stripe_checkout_session_id) DO NOTHING
        """,
        user_id,
        checkout_session_id,
        terms_version,
        settings.b2b_terms_sha256.strip().lower(),
        _minimised_ip_evidence(request),
        user_agent,
    )


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


async def _sync_api_key_entitlements(conn, user_id: int, tier: str, entitlements: dict) -> None:
    rate_limit = get_tier_config(tier)["rate"]
    await conn.execute(
        "UPDATE api_keys SET tier = $1, rate_limit = $2 WHERE user_id = $3 AND is_active = true",
        tier, rate_limit, user_id,
    )
    # F-17: if a downgrade dropped the seat allowance below the number of active
    # keys, deactivate the excess (newest first, keeping the original/primary
    # key) so old keys can't outlive the seats the customer is paying for.
    max_users = int(entitlements["max_users"])
    await conn.execute(
        """
        UPDATE api_keys
        SET is_active = false
        WHERE id IN (
            SELECT id FROM api_keys
            WHERE user_id = $1 AND is_active = true
            ORDER BY created_at ASC, id ASC
            OFFSET $2
        )
        """,
        user_id,
        max_users,
    )


async def _persist_subscription_state(
    conn,
    user_id: int,
    subscription_id: str | None,
    tier: str,
    status: str,
    *,
    stripe_price_id: str | None = None,
    extra_seats: int = 0,
    cancel_at_period_end: bool = False,
    current_period_end: datetime | None = None,
) -> None:
    entitlements = get_subscription_entitlements(tier, extra_seats)
    await conn.execute(
        """
        INSERT INTO subscriptions (
            user_id, stripe_subscription_id, stripe_price_id, tier, status,
            included_users, extra_seats, max_users, seat_price_gbp,
            cancel_at_period_end, current_period_end
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (stripe_subscription_id) DO UPDATE SET
            stripe_price_id = EXCLUDED.stripe_price_id,
            tier = EXCLUDED.tier,
            status = EXCLUDED.status,
            included_users = EXCLUDED.included_users,
            extra_seats = EXCLUDED.extra_seats,
            max_users = EXCLUDED.max_users,
            seat_price_gbp = EXCLUDED.seat_price_gbp,
            cancel_at_period_end = EXCLUDED.cancel_at_period_end,
            current_period_end = EXCLUDED.current_period_end
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
        cancel_at_period_end,
        current_period_end,
    )
    await _sync_api_key_entitlements(conn, user_id, tier, entitlements)


@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    request: Request,
    _auth: dict = Depends(validate_billing_identity),
) -> dict:
    """Create a Stripe Checkout session for upgrading."""
    if not settings.billing_checkout_enabled:
        raise HTTPException(status_code=503, detail="Billing checkout is awaiting Human Gate approval.")
    _verify_contract_acceptance(req.terms_version, req.business_use_confirmed)
    user_id = _require_browser_billing_owner(_auth)
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

    # Resolve account and paid state together. A separate active subscription
    # is redirected to POST /subscription/change, which mutates through the
    # concurrency-safe ledger instead of opening a second Stripe subscription.
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id, email, stripe_customer_id FROM users WHERE id = $1", user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user account required.")
    _verify_request_email(req.email, user["email"])

    async with get_connection() as conn:
        existing_sub = await conn.fetchrow(
            """
            SELECT tier, status, stripe_subscription_id, stripe_price_id, extra_seats
            FROM subscriptions
            WHERE user_id = $1
              AND stripe_subscription_id IS NOT NULL
              AND status NOT IN ('canceled', 'incomplete_expired')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user["id"],
        )
    if existing_sub:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Your account already has an active {existing_sub['tier']} subscription. "
                "Use POST /api/v1/billing/subscription/change to change plans or seats."
            ),
        )

    extra_seats = _normalize_extra_seats(tier, requested_extra_seats)
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

    session = stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[
            {"price": price_id, "quantity": 1},
            *([{"price": settings.stripe_price_pro_seat, "quantity": extra_seats}] if extra_seats else []),
        ],
        mode="subscription",
        success_url=f"{settings.app_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url}/pricing",
        metadata={
            "user_id": str(user["id"]), "tier": tier, "extra_seats": str(extra_seats),
            "price_id": price_id, "terms_version": req.terms_version,
            "business_use_confirmed": "true",
            "terms_sha256": settings.b2b_terms_sha256.strip().lower(),
        },
        subscription_data={
            "metadata": {
                "type": "b2b",
                "user_id": str(user["id"]),
                "tier": tier,
                "extra_seats": str(extra_seats),
                "terms_version": req.terms_version,
                "terms_sha256": settings.b2b_terms_sha256.strip().lower(),
            },
        },
        idempotency_key=f"caregist-checkout-user-{user['id']}",
    )
    try:
        async with get_connection() as conn:
            await _persist_contract_acceptance(
                conn,
                user_id=int(user["id"]),
                checkout_session_id=session.id,
                terms_version=req.terms_version,
                request=request,
            )
            await write_audit_log(
                action="billing.checkout.create",
                outcome="success",
                actor=actor_from_auth(_auth),
                target_type="checkout_session",
                target_id=session.id,
                metadata={"tier": tier, "extra_seats": extra_seats, "terms_version": req.terms_version},
                conn=conn,
            )
    except Exception:
        try:
            stripe.checkout.Session.expire(session.id)
        except Exception:
            logger.exception("Failed to expire unevidenced Checkout Session %s", session.id)
        raise

    stripe_mode = "test" if settings.stripe_secret_key.startswith("sk_test_") else "live"
    return {"checkout_url": session.url, "session_id": session.id, "stripe_mode": stripe_mode}


_PROFILE_TIERS = {"enhanced", "sponsored"}
_PROFILE_TIER_ALIASES = {
    "premium": "enhanced",
    "provider-pro": "enhanced",
    "provider_pro": "enhanced",
    "pro-listing": "enhanced",
}


def _normalize_profile_tier(tier: str) -> str:
    normalized = "-".join(tier.strip().lower().replace("_", "-").split())
    return _PROFILE_TIER_ALIASES.get(normalized, normalized)


class ProfileCheckoutRequest(BaseModel):
    slug: str
    tier: str
    email: EmailStr
    terms_version: str = Field(min_length=1, max_length=100)
    business_use_confirmed: Literal[True]

    model_config = {"extra": "forbid"}


@router.post("/profile-checkout")
async def create_profile_checkout(
    req: ProfileCheckoutRequest,
    request: Request,
    _auth: dict = Depends(validate_billing_identity),
) -> dict:
    """Create a Stripe Checkout session for a provider listing tier upgrade."""
    if not settings.billing_checkout_enabled:
        raise HTTPException(status_code=503, detail="Billing checkout is awaiting Human Gate approval.")
    _verify_contract_acceptance(req.terms_version, req.business_use_confirmed)
    user_id = _require_browser_billing_owner(_auth)
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    tier = _normalize_profile_tier(req.tier)
    if tier not in _PROFILE_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid profile tier: {req.tier}. Choose from {sorted(_PROFILE_TIERS)}.")

    price_map = {
        "enhanced": settings.stripe_price_profile_enhanced or settings.stripe_price_profile_premium,
        "sponsored": settings.stripe_price_profile_sponsored,
    }
    price_id = price_map[tier]
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Checkout for the {tier} profile tier is not yet configured.")

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
    if provider["profile_subscription_id"]:
        raise HTTPException(
            status_code=409,
            detail="This listing already has a paid subscription. Contact support to change its plan.",
        )
    async with get_connection() as conn:
        claim = await conn.fetchrow(
            """
            SELECT id
            FROM provider_claims
            WHERE provider_id = $1
              AND claimant_email = $2
              AND status = 'approved'
            LIMIT 1
            """,
            provider["id"],
            user["email"],
        )
    if not claim:
        raise HTTPException(status_code=403, detail="An approved claim is required before upgrading this listing.")

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

    session = stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.app_url}/provider-dashboard/{req.slug}?upgraded=1",
        cancel_url=f"{settings.app_url}/provider-dashboard/{req.slug}",
        metadata={
            "type": "profile",
            "slug": req.slug,
            "provider_id": str(provider["id"]),
            "tier": tier,
            "user_id": str(user["id"]),
            "terms_version": req.terms_version,
            "business_use_confirmed": "true",
            "terms_sha256": settings.b2b_terms_sha256.strip().lower(),
        },
        subscription_data={
            "metadata": {
                "type": "profile",
                "provider_id": str(provider["id"]),
                "tier": tier,
                "terms_version": req.terms_version,
                "terms_sha256": settings.b2b_terms_sha256.strip().lower(),
            },
        },
        idempotency_key=f"caregist-profile-checkout-provider-{provider['id']}",
    )
    try:
        async with get_connection() as conn:
            await _persist_contract_acceptance(
                conn,
                user_id=int(user["id"]),
                checkout_session_id=session.id,
                terms_version=req.terms_version,
                request=request,
            )
            await write_audit_log(
                action="billing.profile_checkout.create",
                outcome="success",
                actor=actor_from_auth(_auth),
                target_type="checkout_session",
                target_id=session.id,
                metadata={"provider_id": str(provider["id"]), "slug": req.slug, "tier": tier},
                conn=conn,
            )
    except Exception:
        try:
            stripe.checkout.Session.expire(session.id)
        except Exception:
            logger.exception("Failed to expire unevidenced profile Checkout Session %s", session.id)
        raise

    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/subscription")
async def get_subscription(_auth: dict = Depends(validate_billing_identity)) -> dict:
    """Return the active subscription and plan entitlements for the authenticated user."""
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")

    async with get_connection() as conn:
        sub = await conn.fetchrow(
            """
            SELECT tier, status, included_users, extra_seats, max_users, seat_price_gbp,
                   stripe_subscription_id, cancel_at_period_end, current_period_end
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
        "cancel_at_period_end": bool(sub["cancel_at_period_end"]) if sub else False,
        "current_period_end": (
            sub["current_period_end"].isoformat() if sub and sub["current_period_end"] else None
        ),
        "entitlements": entitlements,
    }


def _stripe_period_end(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


@router.post("/subscription/cancel")
async def cancel_subscription(_auth: dict = Depends(validate_billing_identity)) -> dict:
    """Idempotently schedule the authenticated B2B subscription to end at period close."""
    user_id = _require_browser_billing_owner(_auth)
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")
    async with get_connection() as conn:
        subscription = await conn.fetchrow(
            """
            SELECT s.stripe_subscription_id, s.cancel_at_period_end,
                   s.current_period_end, s.status, u.stripe_customer_id
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.user_id = $1 AND s.tier != 'free'
            ORDER BY created_at DESC LIMIT 1
            """,
            user_id,
        )
    if not subscription or not subscription["stripe_subscription_id"]:
        raise HTTPException(status_code=404, detail="No cancellable paid subscription was found.")
    subscription_id = subscription["stripe_subscription_id"]
    stripe_subscription = stripe.Subscription.retrieve(subscription_id)
    if stripe_subscription.get("customer") != subscription["stripe_customer_id"]:
        raise HTTPException(status_code=409, detail="Stripe subscription ownership could not be verified.")
    if stripe_subscription.get("status") in {"canceled", "incomplete_expired"}:
        raise HTTPException(status_code=409, detail="This subscription is no longer cancellable.")
    if stripe_subscription.get("cancel_at_period_end"):
        period_end = _stripe_period_end(stripe_subscription.get("current_period_end"))
        async with get_connection() as conn:
            await conn.execute(
                """UPDATE subscriptions SET cancel_at_period_end = TRUE,
                   current_period_end = $1 WHERE user_id = $2 AND stripe_subscription_id = $3""",
                period_end,
                user_id,
                subscription_id,
            )
        return {
            "cancel_at_period_end": True,
            "current_period_end": period_end.isoformat() if period_end else None,
        }

    idempotency_key = f"caregist-cancel-{user_id}-{subscription_id}"
    stripe_subscription = stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True,
        idempotency_key=idempotency_key,
    )
    period_end = _stripe_period_end(stripe_subscription.get("current_period_end"))
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE subscriptions
                SET cancel_at_period_end = TRUE, current_period_end = $1
                WHERE user_id = $2 AND stripe_subscription_id = $3
                """,
                period_end,
                user_id,
                subscription_id,
            )
            await write_audit_log(
                action="billing.subscription.cancel_at_period_end",
                outcome="success",
                actor=actor_from_auth(_auth),
                target_type="subscription",
                target_id=subscription_id,
                metadata={
                    "cancel_at_period_end": True,
                    "current_period_end": period_end.isoformat() if period_end else None,
                },
                conn=conn,
            )
    return {
        "cancel_at_period_end": True,
        "current_period_end": period_end.isoformat() if period_end else None,
    }


@router.post("/subscription/change")
async def change_subscription(
    req: SubscriptionChangeRequest,
    _auth: dict = Depends(validate_billing_identity),
) -> dict:
    """Concurrency-safe self-service plan/seat change for an existing subscription.

    Existing subscriptions used to fail closed to "contact support" because
    two concurrent change requests could otherwise race and silently drop one
    of them. This uses optimistic locking (`subscriptions.version`) plus an
    append-only `subscription_mutations` ledger so a lost update is rejected
    with 409 instead of applied silently.
    """
    if not settings.billing_checkout_enabled:
        raise HTTPException(status_code=503, detail="Billing checkout is awaiting Human Gate approval.")
    user_id = _require_browser_billing_owner(_auth)
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured.")

    tier = _normalize_checkout_tier(req.tier)
    if tier not in CHECKOUT_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {req.tier}. Choose 'alerts-pro', 'starter', 'pro', or 'business'.")
    extra_seats = _normalize_extra_seats(tier, req.extra_seats)

    async with get_connection() as conn:
        subscription = await conn.fetchrow(
            """
            SELECT s.tier, s.extra_seats, s.version, s.stripe_subscription_id, u.stripe_customer_id
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.user_id = $1 AND s.tier != 'free'
              AND s.stripe_subscription_id IS NOT NULL
              AND s.status NOT IN ('canceled', 'incomplete_expired')
            ORDER BY s.created_at DESC LIMIT 1
            """,
            user_id,
        )
    if not subscription or not subscription["stripe_subscription_id"]:
        raise HTTPException(status_code=404, detail="No active paid subscription was found to change.")

    subscription_id = subscription["stripe_subscription_id"]
    current_version = int(subscription["version"])
    from_tier = subscription["tier"]
    from_extra_seats = int(subscription["extra_seats"] or 0)

    if tier == from_tier and extra_seats == from_extra_seats:
        entitlements = get_subscription_entitlements(from_tier, from_extra_seats)
        return {"tier": from_tier, "extra_seats": from_extra_seats, "entitlements": entitlements, "changed": False}

    stripe_subscription = stripe.Subscription.retrieve(subscription_id)
    if stripe_subscription.get("customer") != subscription["stripe_customer_id"]:
        raise HTTPException(status_code=409, detail="Stripe subscription ownership could not be verified.")

    base_price_id = _base_price_for_tier(tier)
    idempotency_key = f"caregist-change-{user_id}-{subscription_id}-{current_version}-{tier}-{extra_seats}"
    stripe.Subscription.modify(
        subscription_id,
        items=[
            {"price": base_price_id, "quantity": 1},
            *([{"price": settings.stripe_price_pro_seat, "quantity": extra_seats}] if extra_seats else []),
        ],
        proration_behavior="create_prorations",
        idempotency_key=idempotency_key,
    )

    entitlements = get_subscription_entitlements(tier, extra_seats)
    async with get_connection() as conn:
        async with conn.transaction():
            updated = await conn.execute(
                """
                UPDATE subscriptions
                SET tier = $1, extra_seats = $2, included_users = $3, max_users = $4,
                    seat_price_gbp = $5, stripe_price_id = $6, version = version + 1
                WHERE user_id = $7 AND stripe_subscription_id = $8 AND version = $9
                """,
                tier,
                extra_seats,
                entitlements["included_users"],
                entitlements["max_users"],
                entitlements["seat_price_gbp"],
                base_price_id,
                user_id,
                subscription_id,
                current_version,
            )
            if updated == "UPDATE 0":
                raise HTTPException(
                    status_code=409,
                    detail="This subscription changed while your request was in flight. Reload and try again.",
                )
            await _sync_api_key_entitlements(conn, user_id, tier, entitlements)
            await conn.execute(
                """
                INSERT INTO subscription_mutations (
                    user_id, stripe_subscription_id, from_tier, from_extra_seats,
                    to_tier, to_extra_seats, stripe_idempotency_key, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'succeeded')
                ON CONFLICT (stripe_idempotency_key) DO NOTHING
                """,
                user_id,
                subscription_id,
                from_tier,
                from_extra_seats,
                tier,
                extra_seats,
                idempotency_key,
            )
            await write_audit_log(
                action="billing.subscription.change",
                outcome="success",
                actor=actor_from_auth(_auth),
                target_type="subscription",
                target_id=subscription_id,
                metadata={
                    "from_tier": from_tier, "from_extra_seats": from_extra_seats,
                    "to_tier": tier, "to_extra_seats": extra_seats,
                },
                conn=conn,
            )
    return {"tier": tier, "extra_seats": extra_seats, "entitlements": entitlements, "changed": True}


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
            elif event_type == "checkout.session.async_payment_succeeded":
                await _handle_checkout_completed(conn, data)
            elif event_type == "customer.subscription.updated":
                await _handle_subscription_updated(conn, data)
            elif event_type == "customer.subscription.deleted":
                await _handle_subscription_deleted(conn, data)
            else:
                logger.info("Unhandled Stripe event: %s", event_type)

            # Retain beyond Stripe's automatic retry horizon so a delayed
            # replay cannot reapply commercial state.
            # inside the transaction but the DELETE is cheap.
            await conn.execute(
                "DELETE FROM stripe_processed_events WHERE processed_at < NOW() - INTERVAL '7 days'"
            )

    return {"status": "ok"}


async def _handle_checkout_completed(conn, session: dict) -> None:
    """Route completed checkout to B2B or provider profile handler."""
    session_id = session.get("id")
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    terms_version = metadata.get("terms_version")
    if not user_id:
        raise RuntimeError("checkout.session.completed missing user_id metadata")
    if not session_id or not terms_version or metadata.get("business_use_confirmed") != "true":
        raise RuntimeError("checkout.session.completed missing B2B acceptance metadata")
    acceptance = await conn.fetchrow(
        """
        SELECT user_id, terms_version, terms_sha256, business_use_confirmed
        FROM b2b_contract_acceptances WHERE stripe_checkout_session_id = $1
        """,
        session_id,
    )
    if (
        not acceptance
        or int(acceptance["user_id"]) != int(user_id)
        or acceptance["terms_version"] != terms_version
        or acceptance["terms_sha256"] != metadata.get("terms_sha256")
        or not acceptance["business_use_confirmed"]
    ):
        raise RuntimeError("checkout.session.completed has no matching immutable B2B acceptance")
    if session.get("payment_status") not in {"paid", "no_payment_required"}:
        raise RuntimeError("checkout session completed before payment became valid")
    if session.get("metadata", {}).get("type") == "profile":
        await _handle_profile_checkout_completed(conn, session)
        return

    tier = session.get("metadata", {}).get("tier")
    extra_seats = int(session.get("metadata", {}).get("extra_seats", "0") or 0)
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    price_id = session.get("metadata", {}).get("price_id")

    if tier not in BASE_PLAN_TIERS:
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
        cancel_at_period_end=False,
        current_period_end=None,
    )
    await write_audit_log(
        action="billing.subscription.activate",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="subscription",
        target_id=subscription_id,
        metadata={"user_id": int(user_id), "tier": tier, "extra_seats": extra_seats},
        conn=conn,
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
    status = subscription.get("status")
    if not status:
        raise RuntimeError("subscription.updated missing status")
    price_id = None
    extra_seats = 0
    unknown_price_ids: list[str] = []
    items = subscription.get("items", {}).get("data", [])
    if items:
        for item in items:
            item_price_id = item.get("price", {}).get("id")
            mapped = PRICE_TO_TIER.get(item_price_id)
            if mapped in BASE_PLAN_TIERS:
                price_id = item_price_id
            elif mapped == "pro-seat":
                extra_seats += int(item.get("quantity") or 0)
            elif item_price_id:
                unknown_price_ids.append(item_price_id)

    sub_row = await conn.fetchrow(
        "SELECT user_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
    )
    if not sub_row:
        profile = await conn.fetchrow(
            "SELECT id, profile_tier FROM care_providers WHERE profile_subscription_id = $1",
            sub_id,
        )
        if profile:
            entitled = status in {"active", "trialing"}
            metadata_tier = _normalize_profile_tier(subscription.get("metadata", {}).get("tier", ""))
            if entitled and metadata_tier not in _PROFILE_TIERS:
                raise RuntimeError(f"profile subscription {sub_id} is active without valid tier metadata")
            effective_tier = metadata_tier if entitled else "claimed"
            await conn.execute(
                "UPDATE care_providers SET profile_tier = %s WHERE id = %s",
                effective_tier,
                profile["id"],
            )
            await write_audit_log(
                action="billing.profile_subscription.update",
                outcome="success",
                actor={"type": "system", "name": "stripe"},
                target_type="subscription",
                target_id=sub_id,
                metadata={"provider_id": str(profile["id"]), "tier": effective_tier, "status": status},
                conn=conn,
            )
            return
        logger.info("Subscription %s updated but no CareGist subscription state exists; skipping", sub_id)
        return

    if unknown_price_ids or not price_id:
        raise RuntimeError(
            f"subscription.updated cannot map base price for subscription {sub_id}: "
            f"base_price={price_id!r}, unknown_prices={unknown_price_ids!r}"
        )

    configured_tier = PRICE_TO_TIER[price_id]
    entitled = status in {"active", "trialing"}
    tier = configured_tier if entitled else "free"
    effective_extra_seats = extra_seats if entitled else 0
    await _persist_subscription_state(
        conn,
        sub_row["user_id"],
        sub_id,
        tier,
        status,
        stripe_price_id=price_id,
        extra_seats=effective_extra_seats,
        cancel_at_period_end=bool(subscription.get("cancel_at_period_end", False)),
        current_period_end=_stripe_period_end(subscription.get("current_period_end")),
    )
    await write_audit_log(
        action="billing.subscription.update",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="subscription",
        target_id=sub_id,
        metadata={
            "user_id": int(sub_row["user_id"]),
            "configured_tier": configured_tier,
            "effective_tier": tier,
            "status": status,
            "extra_seats": effective_extra_seats,
        },
        conn=conn,
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
        await write_audit_log(
            action="billing.subscription.cancel",
            outcome="success",
            actor={"type": "system", "name": "stripe"},
            target_type="subscription",
            target_id=sub_id,
            metadata={"user_id": int(sub_row["user_id"]), "tier": "free"},
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
    """Activate provider listing tier after successful profile checkout."""
    slug = session.get("metadata", {}).get("slug")
    tier = _normalize_profile_tier(session.get("metadata", {}).get("tier", ""))
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
    await write_audit_log(
        action="billing.profile_subscription.activate",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="provider",
        target_id=slug,
        metadata={"tier": tier, "subscription_id": subscription_id},
        conn=conn,
    )

    logger.info("Provider %s upgraded to profile tier %s (subscription: %s)", slug, tier, subscription_id)
