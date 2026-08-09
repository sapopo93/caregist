"""Stripe billing: checkout, webhooks, and subscription management."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from api.middleware.auth import validate_billing_identity
from api.middleware.ip_rate_limit import _get_client_ip, check_ip_rate_limit

from api.config import (
    allows_extra_seats,
    get_subscription_entitlements,
    get_tier_config,
    get_tier_rank,
    max_tier,
    settings,
)
from api.database import get_connection
from api.utils.audit import actor_from_auth, write_audit_log

logger = logging.getLogger("caregist.billing")
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

PRICE_TO_TIER = {}         # B2B data plan prices → tier name
PRICE_TO_PROFILE_TIER = {}  # Provider listing prices → profile tier name

FULL_DATASET_CONSENT_TEXT = (
    "By purchasing, I expressly request immediate supply of the digital dataset before the end "
    "of the 14-day cancellation period and acknowledge that I lose my statutory right to cancel "
    "once download access is provided. I agree to the Terms of Service."
)
OGL_ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0"
)


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


CHECKOUT_TIERS = {"alerts-pro", "starter", "pro", "business"}
BASE_PLAN_TIERS = CHECKOUT_TIERS  # kept as an alias for older internal call sites
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
    """Create or recover the one pending Stripe operation for a billing owner.

    This is the concurrency-safe mutation ledger: two concurrent requests for
    the same owner/operation race on a unique partial index instead of both
    reaching Stripe, so a lost update fails closed (409) instead of silently
    dropping one of the two changes.
    """
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
    # None on an existing-subscription change means "keep the current seat count".
    extra_seats: int | None = Field(None, ge=0, le=50)
    terms_version: str = Field(min_length=1, max_length=100)
    business_use_confirmed: Literal[True]

    model_config = {"extra": "forbid"}


class DatasetCheckoutRequest(BaseModel):
    email: EmailStr

    model_config = {"extra": "forbid"}


def _dataset_terms() -> tuple[str, str, str]:
    version = settings.digital_content_terms_version.strip()
    terms_sha = settings.digital_content_terms_sha256.strip().lower()
    consent_sha = hashlib.sha256(FULL_DATASET_CONSENT_TEXT.encode("utf-8")).hexdigest()
    if not version or len(terms_sha) != 64 or any(char not in "0123456789abcdef" for char in terms_sha):
        raise HTTPException(status_code=503, detail="Dataset checkout is awaiting approved digital-content terms.")
    return version, terms_sha, consent_sha


def _new_dataset_download_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    rate_limit = get_tier_config(tier)["rate"]
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


@router.post("/dataset-checkout", dependencies=[Depends(check_ip_rate_limit)])
async def create_dataset_checkout(req: DatasetCheckoutRequest) -> dict:
    """Create a one-time Checkout Session tied to an immutable full-dataset artefact."""
    if not settings.full_dataset_checkout_enabled:
        raise HTTPException(status_code=503, detail="Dataset checkout is not available yet.")
    if not settings.stripe_secret_key or not settings.stripe_price_full_dataset or not settings.resend_api_key:
        raise HTTPException(status_code=503, detail="Dataset checkout is not configured.")

    terms_version, terms_sha, consent_sha = _dataset_terms()
    email = str(req.email).strip().lower()
    async with get_connection() as conn:
        artifact = await conn.fetchrow(
            """
            SELECT id, record_count, sha256, source_watermark
            FROM full_dataset_artifacts
            WHERE is_active
            LIMIT 1
            """
        )
        if not artifact:
            raise HTTPException(status_code=503, detail="A current full dataset is being prepared. No payment has been taken.")
        order = await conn.fetchrow(
            """
            INSERT INTO full_dataset_orders (artifact_id, customer_email, stripe_price_id)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            artifact["id"],
            email,
            settings.stripe_price_full_dataset,
        )

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=email,
            line_items=[{"price": settings.stripe_price_full_dataset, "quantity": 1}],
            success_url=f"{settings.app_url}/full-dataset?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.app_url}/full-dataset?cancelled=1",
            expires_at=int(expires_at.timestamp()),
            consent_collection={"terms_of_service": "required"},
            custom_text={
                "terms_of_service_acceptance": {"message": FULL_DATASET_CONSENT_TEXT},
                "after_submit": {"message": "Your private download link will be emailed after payment is confirmed."},
            },
            invoice_creation={"enabled": True},
            metadata={
                "type": "full_dataset",
                "order_id": str(order["id"]),
                "artifact_id": str(artifact["id"]),
                "price_id": settings.stripe_price_full_dataset,
                "terms_version": terms_version,
                "terms_sha256": terms_sha,
                "consent_text_sha256": consent_sha,
            },
            idempotency_key=f"caregist-full-dataset-{order['id']}",
        )
        async with get_connection() as conn:
            await conn.execute(
                """
                UPDATE full_dataset_orders
                SET stripe_checkout_session_id = $1, updated_at = NOW()
                WHERE id = $2 AND status = 'pending'
                """,
                session.id,
                order["id"],
            )
    except Exception:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE full_dataset_orders SET status = 'expired', updated_at = NOW() WHERE id = $1",
                order["id"],
            )
        raise

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "record_count": int(artifact["record_count"]),
        "source_watermark": artifact["source_watermark"].isoformat(),
        "stripe_mode": "test" if settings.stripe_secret_key.startswith("sk_test_") else "live",
    }


@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    request: Request,
    _auth: dict = Depends(validate_billing_identity),
) -> dict:
    """Create a Stripe Checkout session for a new plan, or change an existing one.

    Existing subscriptions used to fail closed to "contact support" for any
    plan/seat change. This now resolves the change through the same
    concurrency-safe billing_operations reservation ledger used for new
    checkout, so a race between two change requests fails one of them closed
    (409) instead of silently dropping it.
    """
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
        subscription_id = existing_sub["stripe_subscription_id"]
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
            return {"updated": True, "tier": tier, "extra_seats": source_extra_seats, "unchanged": True}

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
            raise RuntimeError("Stripe returned a non-entitled status after changing the account subscription")
        if changed_tier != tier or changed_extra_seats != extra_seats:
            raise RuntimeError("Stripe returned subscription items that do not match the requested account plan change")

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
                    metadata={
                        "tier": tier,
                        "extra_seats": extra_seats,
                        "terms_version": req.terms_version,
                        "terms_sha256": settings.b2b_terms_sha256.strip().lower(),
                    },
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
        line_items=[
            {"price": price_id, "quantity": 1},
            *([{"price": settings.stripe_price_pro_seat, "quantity": extra_seats}] if extra_seats else []),
        ],
        mode="subscription",
        success_url=f"{settings.app_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url}/pricing",
        expires_at=int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
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
                "price_id": price_id,
                **({"seat_price_id": settings.stripe_price_pro_seat} if extra_seats else {}),
                "terms_version": req.terms_version,
                "terms_sha256": settings.b2b_terms_sha256.strip().lower(),
            },
        },
        idempotency_key=f"caregist-checkout-{operation['id']}",
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
        expires_at=int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
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

    status = sub["status"] if sub else "active"
    entitled = status in ENTITLED_SUBSCRIPTION_STATUSES if sub else True
    stored_tier = sub["tier"] if sub and entitled else None
    effective_tier = max_tier(_auth.get("tier", "free"), stored_tier) if entitled else "free"
    extra_seats = int(sub["extra_seats"] or 0) if sub and entitled else 0
    entitlements = get_subscription_entitlements(effective_tier, extra_seats)
    return {
        "tier": effective_tier,
        "status": status,
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


@router.post("/portal")
async def create_billing_portal(_auth: dict = Depends(validate_billing_identity)) -> dict:
    """Open Stripe's customer-owned billing portal for invoices and payment methods."""
    user_id = _require_browser_billing_owner(_auth)
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
            elif event_type == "checkout.session.async_payment_succeeded":
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
                await conn.execute(
                    """
                    UPDATE full_dataset_orders
                    SET status = 'expired', updated_at = NOW()
                    WHERE stripe_checkout_session_id = $1 AND status = 'pending'
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
            elif event_type in ("charge.refunded", "charge.refund.updated"):
                await _handle_refund(conn, data)
            else:
                logger.info("Unhandled Stripe event: %s", event_type)

            # Retain beyond Stripe's automatic retry horizon so a delayed
            # replay cannot reapply commercial state.
            await conn.execute(
                "DELETE FROM stripe_processed_events WHERE processed_at < NOW() - INTERVAL '7 days'"
            )

    return {"status": "ok"}


async def _handle_dataset_checkout_completed(conn, session: dict) -> None:
    """Verify Stripe state, preserve consent evidence, and queue fulfilment atomically."""
    session_id = session.get("id")
    if not session_id:
        raise RuntimeError("full-dataset checkout missing session id")
    authoritative = stripe.checkout.Session.retrieve(session_id, expand=["line_items"])
    metadata = authoritative.get("metadata", {})
    order_id = metadata.get("order_id")
    artifact_id = metadata.get("artifact_id")
    if metadata.get("type") != "full_dataset" or not order_id or not artifact_id:
        raise RuntimeError("full-dataset checkout missing immutable order metadata")
    if authoritative.get("payment_status") not in {"paid", "no_payment_required"}:
        raise RuntimeError("full-dataset checkout completed before payment became valid")
    if authoritative.get("consent", {}).get("terms_of_service") != "accepted":
        raise RuntimeError("full-dataset checkout has no Stripe terms acceptance")

    terms_version, terms_sha, consent_sha = _dataset_terms()
    if (
        metadata.get("terms_version") != terms_version
        or metadata.get("terms_sha256") != terms_sha
        or metadata.get("consent_text_sha256") != consent_sha
    ):
        raise RuntimeError("full-dataset checkout legal evidence does not match approved terms")

    line_items = authoritative.get("line_items", {}).get("data", [])
    actual_items = [
        (item.get("price", {}).get("id"), int(item.get("quantity") or 0))
        for item in line_items
    ]
    if actual_items != [(settings.stripe_price_full_dataset, 1)]:
        raise RuntimeError(f"full-dataset checkout has unexpected line items: {actual_items!r}")

    order = await conn.fetchrow(
        """
        SELECT id, artifact_id, customer_email, stripe_price_id, status
        FROM full_dataset_orders
        WHERE id = $1 AND stripe_checkout_session_id = $2
        FOR UPDATE
        """,
        order_id,
        session_id,
    )
    if (
        not order
        or str(order["artifact_id"]) != artifact_id
        or order["stripe_price_id"] != settings.stripe_price_full_dataset
    ):
        raise RuntimeError("full-dataset checkout does not match its reserved local order")
    if order["status"] == "refunded":
        raise RuntimeError("refunded full-dataset order cannot be fulfilled")
    if order["status"] == "paid":
        logger.info("Full-dataset order %s is already fulfilled", order["id"])
        return

    payment_intent = authoritative.get("payment_intent")
    if hasattr(payment_intent, "get"):
        payment_intent = payment_intent.get("id")
    await conn.execute(
        """
        UPDATE full_dataset_orders
        SET status = 'paid', stripe_payment_intent_id = $1,
            amount_total = $2, currency = LOWER($3), paid_at = COALESCE(paid_at, NOW()),
            fulfilled_at = COALESCE(fulfilled_at, NOW()), updated_at = NOW()
        WHERE id = $4
        """,
        payment_intent,
        authoritative.get("amount_total"),
        authoritative.get("currency"),
        order["id"],
    )
    await conn.execute(
        """
        INSERT INTO digital_content_consents (
          order_id, stripe_checkout_session_id, terms_version, terms_sha256,
          consent_text_sha256, immediate_supply_consented,
          cancellation_right_acknowledged, accepted_at, evidence_source
        ) VALUES ($1, $2, $3, $4, $5, TRUE, TRUE, NOW(), 'stripe_checkout_terms_checkbox')
        ON CONFLICT (order_id) DO NOTHING
        """,
        order["id"], session_id, terms_version, terms_sha, consent_sha,
    )

    raw_token, token_hash = _new_dataset_download_token()
    await conn.execute(
        """
        INSERT INTO dataset_download_tokens (token_hash, order_id, expires_at)
        VALUES ($1, $2, NOW() + INTERVAL '7 days')
        ON CONFLICT (token_hash) DO NOTHING
        """,
        token_hash,
        order["id"],
    )
    download_url = f"{settings.app_url}/api/export?token={raw_token}"
    safe_url = html.escape(download_url, quote=True)
    safe_version = html.escape(terms_version)
    email_body = (
        "<p>Your CareGist full dataset is ready.</p>"
        f'<p><a href="{safe_url}">Download the private CSV</a>. '
        "This link expires in 7 days and permits up to 5 downloads.</p>"
        f"<p>You expressly requested immediate supply and acknowledged that your statutory "
        f"right to cancel would be lost once access was provided (Terms {safe_version}). "
        "This does not affect rights relating to faulty or misdescribed digital content.</p>"
        f"<p>{html.escape(OGL_ATTRIBUTION)}. "
        '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">View licence</a>.</p>'
    )
    await conn.execute(
        """
        INSERT INTO pending_emails (to_email, subject, html_body, idempotency_key)
        VALUES ($1, 'Your CareGist full dataset', $2, $3)
        ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
        """,
        order["customer_email"],
        email_body,
        f"full-dataset-delivery:{order['id']}",
    )
    await write_audit_log(
        action="billing.full_dataset.fulfil",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="full_dataset_order",
        target_id=str(order["id"]),
        metadata={"artifact_id": artifact_id, "session_id": session_id},
        conn=conn,
    )


async def _handle_checkout_completed(conn, session: dict) -> None:
    """Route completed checkout to B2B or provider profile handler.

    Requires a matching immutable b2b_contract_acceptances row before any
    entitlement is granted — this is the legal evidence gate; Stripe metadata
    alone is not trusted as proof of acceptance.
    """
    session_id = session.get("id")
    metadata = session.get("metadata", {})
    if metadata.get("type") == "full_dataset":
        await _handle_dataset_checkout_completed(conn, session)
        return
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
    if metadata.get("type") == "profile":
        await _handle_profile_checkout_completed(conn, session)
        return

    tier = metadata.get("tier")
    extra_seats = int(metadata.get("extra_seats", "0") or 0)
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    price_id = metadata.get("price_id")
    seat_price_id = metadata.get("seat_price_id")

    if tier not in CHECKOUT_TIERS:
        raise RuntimeError(f"checkout.session.completed has invalid tier metadata: {tier!r}")
    if not subscription_id:
        raise RuntimeError("checkout.session.completed missing subscription id")

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

    # The authoritative Stripe state can race ahead of the just-completed
    # session (e.g. an immediate downgrade to past_due). Persisting the raw
    # tier regardless of status would grant paid entitlements to an account
    # that isn't actually entitled — same class of gap as
    # _handle_subscription_updated, so it gets the same write-time guard.
    entitled = status in ENTITLED_SUBSCRIPTION_STATUSES
    effective_tier = actual_tier if entitled else "free"
    effective_extra_seats = actual_extra_seats if entitled else 0
    await _persist_subscription_state(
        conn,
        int(user_id),
        subscription_id,
        effective_tier,
        status,
        stripe_price_id=actual_price_id,
        extra_seats=effective_extra_seats,
    )
    await write_audit_log(
        action="billing.subscription.activate",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="subscription",
        target_id=subscription_id,
        metadata={
            "user_id": int(user_id),
            "approved_tier": actual_tier,
            "effective_tier": effective_tier,
            "status": status,
            "extra_seats": effective_extra_seats,
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
        session_id,
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
            if status not in ENTITLED_SUBSCRIPTION_STATUSES:
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
                    metadata={"subscription_id": sub_id, "tier": "claimed", "status": status},
                    conn=conn,
                )
                logger.warning(
                    "Profile subscription %s downgraded to claimed for non-entitled status=%s", sub_id, status,
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
                metadata={"subscription_id": sub_id, "tier": profile_tier, "status": status, "price_id": profile_price_id},
                conn=conn,
            )
            logger.info("Profile subscription %s updated: tier=%s status=%s", sub_id, profile_tier, status)
            return

        logger.info("Subscription %s updated but no local subscription row exists; skipping", sub_id)
        return

    status, price_id, configured_tier, extra_seats = _b2b_subscription_state(
        subscription,
        known_price_id=sub_row.get("stripe_price_id"),
        known_tier=_normalize_checkout_tier(sub_row.get("tier") or ""),
    )
    # _persist_subscription_state writes `tier` straight onto api_keys, so a
    # past-due/unpaid/canceled subscription must not keep its paid tier here —
    # downgrade to free at write time rather than relying on every reader to
    # re-check status.
    entitled = status in ENTITLED_SUBSCRIPTION_STATUSES
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

    sub_row = await conn.fetchrow(
        "SELECT user_id, tier, stripe_price_id FROM subscriptions WHERE stripe_subscription_id = $1", sub_id
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
    metadata = session.get("metadata", {})
    slug = metadata.get("slug")
    tier = _normalize_profile_tier(metadata.get("tier", ""))
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


async def _handle_refund(conn, charge: dict) -> None:
    """Record a charge.refunded or charge.refund.updated event atomically.

    Updates billing_operations with the refund status and writes an audit log
    inside the same transaction as the webhook dedup insert. On exception the
    entire transaction rolls back and Stripe will re-deliver the event.

    Clawback (full refund of a paid charge) also records the commercial reversal
    so reconciliation can detect orphaned value.
    """
    if charge.get("object") == "refund" or str(charge.get("id", "")).startswith("re_"):
        charge_id_for_refund = charge.get("charge")
        if not charge_id_for_refund:
            raise RuntimeError("charge.refund.updated missing charge reference")
        charge = stripe.Charge.retrieve(charge_id_for_refund)

    charge_id = charge.get("id")
    if not charge_id:
        raise RuntimeError("charge.refunded missing charge id")

    amount_refunded = charge.get("amount_refunded", 0)
    amount = charge.get("amount", 0)
    fully_refunded = charge.get("refunded", False)
    payment_intent = charge.get("payment_intent")

    await conn.execute(
        """
        INSERT INTO billing_operations
            (owner_type, operation_type, stripe_object_id, status,
             amount_gbp, metadata, created_at, updated_at)
        VALUES ('account', 'refund', $1, $2, $3, $4, NOW(), NOW())
        ON CONFLICT (stripe_object_id, operation_type)
        DO UPDATE SET status = EXCLUDED.status,
                      amount_gbp = EXCLUDED.amount_gbp,
                      metadata = EXCLUDED.metadata,
                      updated_at = NOW()
        """,
        charge_id,
        "refunded" if fully_refunded else "partial_refund",
        round(amount_refunded / 100, 2),
        json.dumps({"payment_intent": payment_intent, "amount": amount,
                     "amount_refunded": amount_refunded,
                     "fully_refunded": fully_refunded}),
    )

    if fully_refunded and payment_intent:
        refunded_order = await conn.fetchrow(
            """
            UPDATE full_dataset_orders
            SET status = 'refunded', updated_at = NOW()
            WHERE stripe_payment_intent_id = $1 AND status = 'paid'
            RETURNING id
            """,
            payment_intent,
        )
        if refunded_order:
            await conn.execute(
                "UPDATE dataset_download_tokens SET expires_at = NOW() WHERE order_id = $1 AND expires_at > NOW()",
                refunded_order["id"],
            )

    await write_audit_log(
        action="billing.charge.refund",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="charge",
        target_id=charge_id,
        metadata={
            "amount_refunded_gbp": round(amount_refunded / 100, 2),
            "amount_original_gbp": round(amount / 100, 2),
            "fully_refunded": fully_refunded,
            "payment_intent": payment_intent,
        },
        conn=conn,
    )

    logger.info(
        "Refund recorded: charge=%s refunded=%s/%s full=%s",
        charge_id, amount_refunded, amount, fully_refunded,
    )
