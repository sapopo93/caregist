"""Operator History (stage 2): paid checkout, order status and the account-scoped download.

Off unless ``operator_history_enabled``: every route here then answers with the same
404 as an unknown route. The checkout also needs ``billing_checkout_enabled`` and
``operator_history_checkout_enabled`` and answers 503 until both are on, the Stripe
Price and the approved B2B terms are configured, and the source evidence is fresh.
Status and download need only ``operator_history_enabled``, so turning checkout off
never strands a customer who has already paid.

The payment event is handled by the shared signed webhook in ``billing.py``, which
hands ``checkout.session.completed`` to ``services/operator_history_orders``.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_billing_identity
from api.middleware.ip_rate_limit import check_ip_rate_limit
from api.routers import billing
from api.services import operator_history as oh
from api.services import operator_history_orders as service
from api.services.pipeline_health import get_pipeline_health
from api.utils.audit import actor_from_auth, write_audit_log

logger = logging.getLogger("caregist.operator_history_orders")
router = APIRouter(tags=["operator-history"])


def _require_enabled() -> None:
    if not settings.operator_history_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


class OperatorHistoryCheckoutRequest(BaseModel):
    """The only things a buyer chooses. There is no price field and no extra field."""

    provider_id: str = Field(min_length=1, max_length=32)
    email: EmailStr
    terms_version: str = Field(min_length=1, max_length=100)
    business_use_confirmed: bool

    model_config = {"extra": "forbid"}


def _checkout_response(order: dict, *, reused: bool) -> dict:
    view = service.order_view(order)
    return {
        "order_id": view["order_id"],
        "checkout_url": order["stripe_checkout_url"],
        "session_id": order["stripe_checkout_session_id"],
        "provider_id": view["provider_id"],
        "legal_name": view["legal_name"],
        "price_pence": view["price_pence"],
        "currency": view["currency"],
        "content_sha256": view["content_sha256"],
        "edition": view["edition"],
        "reused": reused,
        "stripe_mode": "test" if settings.stripe_secret_key.startswith("sk_test_") else "live",
    }


@router.post(
    "/api/v1/billing/operator-history-checkout",
    dependencies=[Depends(_require_enabled), Depends(check_ip_rate_limit)],
)
async def create_operator_history_checkout(
    req: OperatorHistoryCheckoutRequest,
    request: Request,
    _auth: dict = Depends(validate_billing_identity),
) -> dict:
    """Create (or recover) the one payable Checkout Session for an operator's history.

    Nothing reaches Stripe unless the operator resolves to exactly one CQC Provider
    ID with a held name, no identity dispute and at least one location.
    """
    if not (settings.billing_checkout_enabled and settings.operator_history_checkout_enabled):
        raise HTTPException(status_code=503, detail="Operator History checkout is not available yet.")
    if not (settings.stripe_secret_key and settings.stripe_price_operator_history):
        raise HTTPException(status_code=503, detail="Operator History checkout is not configured.")
    billing._verify_contract_acceptance(req.terms_version, req.business_use_confirmed)
    user_id = billing._require_browser_billing_owner(_auth)
    if not _auth.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before starting billing.")
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id, email FROM users WHERE id = $1", user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Authenticated user account required.")
    billing._verify_request_email(req.email, user["email"])

    async with get_connection() as conn:
        gap = await service.readiness_gap(conn, get_pipeline_health)
    if gap:
        logger.warning("Operator History checkout closed: %s", gap)
        raise HTTPException(
            status_code=503,
            detail="Operator History checkout is waiting for its source-freshness gate.",
        )

    # Every stage 1 refusal is decided here, before any Stripe call.
    try:
        async with get_connection() as conn, conn.transaction(isolation="repeatable_read", readonly=True):
            operator = await oh.resolve_operator(conn, provider_id=req.provider_id)
            record = await oh.build_operator_history(conn, operator)
    except oh.OperatorRefusal as refusal:
        raise HTTPException(status_code=refusal.http_status, detail=refusal.as_detail())
    pin = service.pin_record(operator, record)

    async with get_connection() as conn:
        order, reused = await service.reserve_order(
            conn,
            user_id=user_id,
            email=str(user["email"]).strip().lower(),
            provider_id=operator.provider_id,
            pin=pin,
            record=record,
            terms_version=req.terms_version.strip(),
            terms_sha256=settings.b2b_terms_sha256.strip().lower(),
            stripe_price_id=settings.stripe_price_operator_history,
        )

    # One session per order: the order row is locked while the session is made, so a
    # concurrent double submit waits and then finds the stored session instead of
    # asking Stripe again. The order was committed first, so a payment can never meet
    # an unknown order. If the session cannot be recorded it is expired and the order
    # is closed, so the buyer's next submit starts a clean order and key.
    unrecorded: _UnrecordedSession | None = None
    try:
        async with get_connection() as conn:
            async with conn.transaction():
                locked = await conn.fetchrow(
                    "SELECT * FROM operator_history_orders WHERE id = $1 FOR UPDATE", order["id"]
                )
                locked = dict(locked)
                if locked["state"] != service.PENDING:
                    raise HTTPException(
                        status_code=409,
                        detail="This order is no longer open for payment. Start a new one.",
                    )
                if locked["stripe_checkout_session_id"] and locked["stripe_checkout_url"]:
                    return _checkout_response(locked, reused=True)
                price_gap = service.validate_checkout_price()
                if price_gap:
                    logger.error("Operator History price check failed: %s", price_gap)
                    raise HTTPException(status_code=503, detail="Operator History checkout is not configured.")
                try:
                    session = stripe.checkout.Session.create(
                        mode="payment",
                        customer_email=locked["customer_email"],
                        line_items=[{"price": locked["stripe_price_id"], "quantity": 1}],
                        success_url=(
                            f"{settings.app_url}/operator-history/orders/{locked['id']}"
                            "?session_id={CHECKOUT_SESSION_ID}"
                        ),
                        cancel_url=f"{settings.app_url}/operator-history?cancelled=1",
                        expires_at=int(locked["checkout_expires_at"].timestamp()),
                        invoice_creation={"enabled": True},
                        metadata=service.build_checkout_metadata(locked),
                        idempotency_key=f"caregist-operator-history-{locked['id']}",
                    )
                except stripe.StripeError as exc:
                    logger.exception("Stripe refused the Operator History Checkout Session")
                    raise HTTPException(
                        status_code=502,
                        detail="The payment provider could not start checkout. No payment has been taken.",
                    ) from exc
                try:
                    await billing._persist_contract_acceptance(
                        conn,
                        user_id=user_id,
                        checkout_session_id=session.id,
                        terms_version=locked["terms_version"],
                        request=request,
                    )
                    acceptance_id = await conn.fetchval(
                        "SELECT id FROM b2b_contract_acceptances WHERE stripe_checkout_session_id = $1",
                        session.id,
                    )
                    await service.attach_session(
                        conn, locked["id"], session_id=session.id, url=session.url, acceptance_id=acceptance_id
                    )
                    await write_audit_log(
                        action="operator_history.checkout.create",
                        outcome="success",
                        actor=actor_from_auth(_auth),
                        target_type="operator_history_order",
                        target_id=str(locked["id"]),
                        metadata={
                            "provider_id": locked["provider_id"],
                            "content_sha256": locked["content_sha256"],
                            "terms_version": locked["terms_version"],
                        },
                        conn=conn,
                        strict=True,
                    )
                except Exception as exc:
                    unrecorded = _UnrecordedSession(session.id, locked["id"], exc)
                    raise
                locked["stripe_checkout_session_id"] = session.id
                locked["stripe_checkout_url"] = session.url
                return _checkout_response(locked, reused=reused)
    except Exception:
        if unrecorded is not None:
            # The transaction has rolled back, so the order row is free to change.
            await _close_unrecorded(unrecorded)
        raise


class _UnrecordedSession:
    def __init__(self, session_id: str, order_id: object, cause: Exception) -> None:
        self.session_id = session_id
        self.order_id = order_id
        self.cause = cause


async def _close_unrecorded(item: _UnrecordedSession) -> None:
    """Expire a Checkout Session that could not be recorded and close its order."""
    try:
        stripe.checkout.Session.expire(item.session_id)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to expire unrecorded Checkout Session %s", item.session_id)
    try:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE operator_history_orders SET state = 'expired', updated_at = NOW() "
                "WHERE id = $1 AND state = 'pending_payment' AND stripe_checkout_session_id IS NULL",
                item.order_id,
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to close Operator History order %s", item.order_id)


def _parse_order_id(order_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found.") from None


async def _own_order(order_id: str, auth: dict) -> dict:
    """The buyer's order. Unknown, malformed and other accounts' orders look identical."""
    user_id = billing._require_billing_user_id(auth)
    async with get_connection() as conn:
        order = await service.get_order_for_user(conn, _parse_order_id(order_id), user_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.get("/api/v1/operator-history/orders/{order_id}", dependencies=[Depends(_require_enabled)])
async def get_operator_history_order(order_id: str, _auth: dict = Depends(validate_billing_identity)) -> dict:
    return service.order_view(await _own_order(order_id, _auth))


_NOT_DOWNLOADABLE = {
    service.PENDING: (402, "This order has not been paid."),
    service.EXPIRED: (402, "This order was not paid and has expired."),
    service.PAID: (409, "Your record is being prepared. Try again shortly."),
    service.FAILED: (409, "Your record could not be prepared yet. CareGist has been notified."),
    service.REFUNDED: (410, "This order was refunded, so the download is no longer available."),
}


@router.get("/api/v1/operator-history/orders/{order_id}/download", dependencies=[Depends(_require_enabled)])
async def download_operator_history(
    order_id: str,
    format: Literal["csv", "pdf"] = Query(...),
    _auth: dict = Depends(validate_billing_identity),
) -> Response:
    order = await _own_order(order_id, _auth)
    if order["state"] != service.DELIVERED:
        status, message = _NOT_DOWNLOADABLE.get(order["state"], (409, "This order cannot be downloaded."))
        raise HTTPException(status_code=status, detail=message)
    async with get_connection() as conn:
        artefact = await service.fetch_artefact(conn, order["id"], format)
    content = bytes(artefact["content"]) if artefact else b""
    recorded = order[f"{format}_sha256"]
    if not artefact or hashlib.sha256(content).hexdigest() != recorded or artefact["artefact_sha256"] != recorded:
        logger.error("Operator History order %s: stored %s does not match its recorded SHA-256", order["id"], format)
        raise HTTPException(status_code=500, detail="This file could not be served. CareGist has been notified.")
    await write_audit_log(
        action="operator_history.download",
        outcome="success",
        actor=actor_from_auth(_auth),
        target_type="operator_history_order",
        target_id=str(order["id"]),
        metadata={"format": format, "sha256": recorded},
    )
    return Response(
        content=content,
        media_type=artefact["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{artefact["filename"]}"',
            "X-Content-SHA256": recorded,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
