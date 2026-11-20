"""Region Monthly (stage 2): paid checkout, order status and the account-scoped download.

Off unless ``region_monthly_enabled``: every route here then answers with the same
404 as an unknown route. The checkout also needs ``billing_checkout_enabled`` and
``region_monthly_checkout_enabled`` and answers 503 until both are on, the three
Stripe Prices and the approved B2B terms are configured, and the source evidence is
fresh. Status and download need only ``region_monthly_enabled``, so turning checkout
off never strands a customer who has already paid.

The payment event is handled by the shared signed webhook in ``billing.py``, which
hands ``checkout.session.completed`` to ``services/region_monthly_orders``.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timezone
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_billing_identity
from api.middleware.ip_rate_limit import check_ip_rate_limit
from api.queries import region_monthly as stage_one_queries
from api.routers import billing
from api.services import region_monthly as rm
from api.services import region_monthly_orders as service
from api.services.pipeline_health import get_pipeline_health
from api.utils.audit import actor_from_auth, write_audit_log

logger = logging.getLogger("caregist.region_monthly_orders")
router = APIRouter(tags=["region-monthly"])

NOT_FOUND = "Order not found."


def _require_enabled() -> None:
    if not settings.region_monthly_enabled:
        raise HTTPException(status_code=404, detail="Not Found")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RegionMonthlyCheckoutRequest(BaseModel):
    """The only things a buyer chooses. There is no price field and no extra field.

    Region, service, kind and month are plain strings so that a bad value reaches the
    purchase rules and comes back with their stable refusal code and wording.
    """

    region: str = Field(max_length=60)
    service: str | None = Field(default=None, max_length=60)
    kind: str = Field(max_length=12)
    first_month: str = Field(max_length=40)
    accept_future_months: bool = False
    email: EmailStr
    terms_version: str = Field(min_length=1, max_length=100)
    business_use_confirmed: bool

    model_config = {"extra": "forbid"}


def _refusal(error: rm.RegionMonthlyError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message})


def _checkout_response(order: dict, *, reused: bool) -> dict:
    future = dict(zip(order["future_months"], order["future_available_from"], strict=True))
    return {
        "order_id": str(order["id"]),
        "checkout_url": order["stripe_checkout_url"],
        "session_id": order["stripe_checkout_session_id"],
        "region": order["region"],
        "service": order["service_slug"],
        "kind": order["kind"],
        "price_pence": order["price_pence"],
        "currency": order["currency"],
        "months": [
            {
                "month": rm.month_key(m),
                "label": rm.format_month(m),
                "status": "future" if m in future else "built",
                "available_from": future[m].isoformat() if m in future else None,
            }
            for m in order["months"]
        ],
        "future_months": [rm.month_key(m) for m in order["future_months"]],
        "future_month_notice": rm.FUTURE_MONTH_NOTICE if order["future_months"] else None,
        "reused": reused,
        "stripe_mode": "test" if settings.stripe_secret_key.startswith("sk_test_") else "live",
    }


@router.post(
    "/api/v1/billing/region-monthly-checkout",
    dependencies=[Depends(_require_enabled), Depends(check_ip_rate_limit)],
)
async def create_region_monthly_checkout(
    req: RegionMonthlyCheckoutRequest,
    request: Request,
    _auth: dict = Depends(validate_billing_identity),
) -> dict:
    """Create (or recover) the one payable Checkout Session for a Region Monthly purchase.

    Nothing reaches Stripe unless the purchase resolves under the stage 1 rules, the
    account holds none of the months already, and the source evidence is fresh.
    """
    if not (settings.billing_checkout_enabled and settings.region_monthly_checkout_enabled):
        raise HTTPException(status_code=503, detail="Region Monthly checkout is not available yet.")
    if not (settings.stripe_secret_key and service.all_price_ids_configured()):
        raise HTTPException(status_code=503, detail="Region Monthly checkout is not configured.")
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
        logger.warning("Region Monthly checkout closed: %s", gap)
        raise HTTPException(
            status_code=503,
            detail="Region Monthly checkout is waiting for its source-freshness gate.",
        )

    # Every stage 1 refusal is decided here, before any Stripe call.
    try:
        rm.require_kind(req.kind)
        region = rm.normalise_region(req.region)
        slug = rm.normalise_service(req.service)
        first_month = rm.parse_month(req.first_month)
        async with get_connection() as conn:
            if not await conn.fetchval(stage_one_queries.BUILDS_TABLE_PRESENT):
                raise rm.RegionMonthlyError("source_unavailable")
            built = [r["period_month"] for r in await conn.fetch(stage_one_queries.BUILT_MONTHS, region, slug)]
        purchase = rm.resolve_purchase(
            req.kind,
            first_month,
            _now(),
            region=region,
            service_slug=slug,
            built_months=built,
            accept_future_months=req.accept_future_months,
        )
    except rm.RegionMonthlyError as error:
        raise _refusal(error)

    try:
        async with get_connection() as conn:
            order, reused = await service.reserve_order(
                conn,
                user_id=user_id,
                email=str(user["email"]).strip().lower(),
                purchase=purchase,
                accepted_future_months=req.accept_future_months,
                terms_version=req.terms_version.strip(),
                terms_sha256=settings.b2b_terms_sha256.strip().lower(),
                stripe_price_id=service.configured_price_id(purchase.kind),
            )
    except service.OrderRefusal as refusal:
        raise HTTPException(status_code=refusal.status_code, detail=refusal.as_detail())

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
                    "SELECT * FROM region_monthly_orders WHERE id = $1 FOR UPDATE", order["id"]
                )
                locked = dict(locked)
                if locked["state"] != service.PENDING:
                    raise HTTPException(
                        status_code=409,
                        detail="This order is no longer open for payment. Start a new one.",
                    )
                if locked["stripe_checkout_session_id"] and locked["stripe_checkout_url"]:
                    return _checkout_response(locked, reused=True)
                price_gap = service.validate_checkout_price(locked["kind"])
                if price_gap:
                    logger.error("Region Monthly price check failed: %s", price_gap)
                    raise HTTPException(status_code=503, detail="Region Monthly checkout is not configured.")
                try:
                    session = stripe.checkout.Session.create(
                        mode="payment",
                        customer_email=locked["customer_email"],
                        line_items=[{"price": locked["stripe_price_id"], "quantity": 1}],
                        success_url=(
                            f"{settings.app_url}/region-monthly/orders/{locked['id']}"
                            "?session_id={CHECKOUT_SESSION_ID}"
                        ),
                        cancel_url=f"{settings.app_url}/region-monthly?cancelled=1",
                        expires_at=int(locked["checkout_expires_at"].timestamp()),
                        invoice_creation={"enabled": True},
                        metadata=service.build_checkout_metadata(locked),
                        idempotency_key=f"caregist-region-monthly-{locked['id']}",
                    )
                except stripe.StripeError as exc:
                    logger.exception("Stripe refused the Region Monthly Checkout Session")
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
                        action="region_monthly.checkout.create",
                        outcome="success",
                        actor=actor_from_auth(_auth),
                        target_type="region_monthly_order",
                        target_id=str(locked["id"]),
                        metadata={
                            "region": locked["region"],
                            "service": locked["service_slug"],
                            "kind": locked["kind"],
                            "months": [rm.month_key(m) for m in locked["months"]],
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
                "UPDATE region_monthly_orders SET state = 'expired', updated_at = NOW() "
                "WHERE id = $1 AND state = 'pending_payment' AND stripe_checkout_session_id IS NULL",
                item.order_id,
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to close Region Monthly order %s", item.order_id)


def _parse_order_id(order_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=NOT_FOUND) from None


async def _own_order(order_id: str, auth: dict) -> dict:
    """The buyer's order. Unknown, malformed and other accounts' orders look identical."""
    user_id = billing._require_billing_user_id(auth)
    async with get_connection() as conn:
        order = await service.get_order_for_user(conn, _parse_order_id(order_id), user_id)
    if order is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return order


@router.get("/api/v1/region-monthly/orders/{order_id}", dependencies=[Depends(_require_enabled)])
async def get_region_monthly_order(order_id: str, _auth: dict = Depends(validate_billing_identity)) -> dict:
    order = await _own_order(order_id, _auth)
    async with get_connection() as conn:
        return await service.load_order_view(conn, order, _now())


_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _purchased_month(month: str, order: dict) -> date:
    """A month of this order. Anything else looks the same as an unknown order."""
    match = _MONTH_RE.fullmatch(month)
    if not match:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    first = date(int(match.group(1)), int(match.group(2)), 1)
    if first not in order["months"]:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return first


@router.get("/api/v1/region-monthly/orders/{order_id}/months/{month}/download", dependencies=[Depends(_require_enabled)])
async def download_region_monthly_month(
    order_id: str,
    month: str,
    format: Literal["csv", "pdf"] = Query(...),
    _auth: dict = Depends(validate_billing_identity),
) -> Response:
    order = await _own_order(order_id, _auth)
    period = _purchased_month(month, order)
    try:
        async with get_connection() as conn:
            build = await service.resolve_download(conn, order, period, _now())
    except service.OrderRefusal as refusal:
        raise HTTPException(status_code=refusal.status_code, detail=refusal.as_detail())
    try:
        file = service.render_download(build, format)
    except service.RegionMonthlyOrderError:
        logger.exception("Region Monthly order %s: the stored build for %s could not be served", order["id"], month)
        raise HTTPException(status_code=500, detail="This file could not be served. CareGist has been notified.")
    await write_audit_log(
        action="region_monthly.download",
        outcome="success",
        actor=actor_from_auth(_auth),
        target_type="region_monthly_order",
        target_id=str(order["id"]),
        metadata={
            "month": rm.month_key(period),
            "format": format,
            "build_version": file.build_version,
            "sha256": file.sha256,
        },
    )
    return Response(
        content=file.content,
        media_type=file.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename}"',
            "X-Content-SHA256": file.sha256,
            "X-Build-Version": str(file.build_version),
            "X-Build-Content-SHA256": build["content_sha256"],
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
