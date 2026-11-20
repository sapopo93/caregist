"""Region Monthly (stage 2): orders, the signed payment event, entitlements and refunds.

The paid path, in order:

1. Checkout (``api/routers/region_monthly_orders.py``) resolves the purchase with the
   stage 1 rules. Every refusal is decided there, before any Stripe call. The price
   comes from ``PURCHASE_KINDS`` in ``api/services/region_monthly.py`` and from nowhere
   else. The order pins the region, service, kind, the exact list of months, which of
   them were future, the price and the terms.
2. The signed ``checkout.session.completed`` event reaches
   :func:`handle_checkout_completed` through the shared webhook. It checks the
   authoritative Stripe session against the pinned order, marks the order paid and
   creates one entitlement per purchased month, in the webhook's own transaction.
   There is nothing to render at payment time: months are built by the schedule, so
   delivery means the entitlement.
3. If the entitlements cannot be created, :class:`EntitlementError` makes the shared
   webhook roll back and then call ``record_failure`` on a fresh connection. The order
   is left ``paid`` with a visible error. Stripe redelivers the same event, or
   ``tools/retry_region_monthly_entitlements.py`` runs, and either finishes the job.
   Entitlements are unique per order and month, so they are created once.
4. A full refund (``_handle_refund`` calls :func:`mark_refunded`) moves the order to
   ``refunded``. Access needs a paid order, so the download stops. The purchased
   months and the entitlement rows are never changed. A partial refund changes nothing.

Nothing here calls a model, and nothing here writes customer-facing text beyond fixed
templates.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

import asyncpg
import stripe

from api.config import settings
from api.database import get_connection
from api.queries import region_monthly as stage_one_queries
from api.queries import region_monthly_orders as q
from api.services import region_monthly as rm
from api.services import region_monthly_render as render
from api.utils.audit import write_audit_log
from api.utils.stripe_compat import stripe_dict

logger = logging.getLogger("caregist.region_monthly_orders")

METADATA_TYPE = "region_monthly"
ALL_SERVICES_METADATA = "all-services"

# A Checkout Session needs at least 30 minutes. One hour leaves room to recover a
# lost response: a retried create with the same idempotency key and parameters
# still satisfies Stripe's minimum.
CHECKOUT_LIFETIME = timedelta(hours=1)

PENDING = "pending_payment"
PAID = "paid"
REFUNDED = "refunded"
EXPIRED = "expired"
ORDER_STATES = (PENDING, PAID, REFUNDED, EXPIRED)


def stripe_price_lookup_key(kind: str) -> str:
    """The lookup key the Stripe Price must carry: ``region_monthly_<kind>_gbp_oneoff_v1``."""
    return f"region_monthly_{kind}_gbp_oneoff_v1"


def configured_price_id(kind: str) -> str:
    rm.require_kind(kind)
    return getattr(settings, f"stripe_price_region_monthly_{kind}", "") or ""


def all_price_ids_configured() -> bool:
    return all(configured_price_id(kind) for kind in rm.PURCHASE_KINDS)


class RegionMonthlyOrderError(RuntimeError):
    """A paid-path state that must make Stripe redeliver the event."""


class EntitlementError(RegionMonthlyOrderError):
    """Carry the failure recorder to the webhook's post-rollback boundary."""

    def __init__(self, order_id: str, message: str, context: dict[str, Any]):
        super().__init__(f"region-monthly entitlement failed for order {order_id}: {message}")
        self.order_id = order_id
        self.failure_message = message
        self.context = context

    async def record_failure(self) -> None:
        await record_entitlement_failure(self.order_id, self.failure_message, self.context)


class OrderRefusal(Exception):
    """A plain refusal with a stable code, an HTTP status and fixed wording."""

    def __init__(self, code: str, status_code: int, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.extra = extra

    def as_detail(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, **self.extra}


MONTHS_ALREADY_HELD = "Your account already holds {months} for {region}, {service}. Choose months you do not hold yet."
CHECKOUT_STILL_OPEN = (
    "A checkout for this region and service is still open and could not be closed. "
    "Wait a few minutes, then check your orders before trying again."
)
NOT_PAID = "This order has not been paid."
REFUNDED_TEXT = "This order was refunded, so the download is no longer available."
BEING_SET_UP = "Your access is being set up. Try again shortly."
WILL_BE_AVAILABLE = "{month} will be available on {date}."
NOT_BUILT_YET = "{month} has not been built yet. It is due from {date}. Try again later."

# --------------------------------------------------------------------------
# Readiness
# --------------------------------------------------------------------------


async def readiness_gap(conn, get_health: Callable[[Any], Awaitable[dict[str, Any]]]) -> str | None:
    """Why checkout must stay closed, or None when the source evidence is accepted.

    Uses the same pipeline-health snapshot as the Operator History and Radar gates:
    the pipeline's own checks passed, the CQC source is fresh and its counts
    reconcile. It leaves out Operator History's check of the stored CQC edition,
    because that edition supplies provider names and Region Monthly does not read it.
    It adds the one table Region Monthly does read: the stored builds.
    """
    health = await get_health(conn)
    if not health.get("readiness_ok"):
        return "pipeline readiness checks have not passed"
    if not health.get("source_fresh"):
        return "the CQC source is not fresh"
    if not (health.get("units") or {}).get("countsReconciled"):
        return "the CQC source counts are not reconciled"
    if not await conn.fetchval(stage_one_queries.BUILDS_TABLE_PRESENT):
        return "the stored monthly builds are missing"
    return None


# --------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------

_INSERT_ORDER = """
INSERT INTO region_monthly_orders (
  user_id, customer_email, region, service_slug, kind, month_count, months,
  future_months, future_available_from, future_months_accepted, price_pence, currency,
  stripe_price_id, terms_version, terms_sha256, checkout_expires_at
) VALUES ($1, $2, $3, $4, $5, $6, $7::date[], $8::date[], $9::date[], $10, $11, $12, $13, $14, $15, $16)
RETURNING *
"""


def _scope_lock_key(user_id: int, region: str, service_slug: str | None) -> str:
    return f"region-monthly-order:{user_id}:{region}:{service_slug or ''}"


def _same_purchase(order: dict[str, Any], purchase: rm.Purchase, terms_version: str, terms_sha256: str, price_id: str) -> bool:
    return (
        order["kind"] == purchase.kind
        and list(order["months"]) == [m.period_month for m in purchase.months]
        and order["terms_version"] == terms_version
        and order["terms_sha256"] == terms_sha256
        and order["stripe_price_id"] == price_id
    )


async def reserve_order(
    conn,
    *,
    user_id: int,
    email: str,
    purchase: rm.Purchase,
    accepted_future_months: bool,
    terms_version: str,
    terms_sha256: str,
    stripe_price_id: str,
) -> tuple[dict[str, Any], bool]:
    """The one pending order for this account and scope: reused, or newly created.

    A double submit of the same purchase finds the pending order and gets it back
    (``reused`` is true), so only one payable session can exist. A different purchase
    in the same scope replaces it: its Checkout Session is expired at Stripe first,
    and if Stripe cannot expire it nothing changes and the buyer is told to wait. A
    pending order past its checkout lifetime is expired without a Stripe call. A later
    deliberate purchase of the same scope (the earlier one is paid) is a new order, but
    months the account already holds are refused here, before payment.
    """
    months = [m.period_month for m in purchase.months]
    future = purchase.future_months
    for _attempt in range(2):
        try:
            async with conn.transaction():
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))",
                    _scope_lock_key(user_id, purchase.region, purchase.service_slug),
                )
                await conn.execute(
                    """
                    UPDATE region_monthly_orders SET state = 'expired', updated_at = NOW()
                    WHERE user_id = $1 AND region = $2 AND service_slug IS NOT DISTINCT FROM $3::text
                      AND state = 'pending_payment' AND checkout_expires_at <= NOW()
                    """,
                    user_id, purchase.region, purchase.service_slug,
                )
                held = await conn.fetch(q.HELD_OVERLAP, user_id, purchase.region, purchase.service_slug, months)
                if held:
                    overlap = sorted({m for row in held for m in row["months"]} & set(months))
                    raise OrderRefusal(
                        "months_already_held",
                        409,
                        MONTHS_ALREADY_HELD.format(
                            months=", ".join(rm.format_month(m) for m in overlap),
                            region=purchase.region,
                            service=render.service_label(purchase.service_slug),
                        ),
                        months=[rm.month_key(m) for m in overlap],
                    )
                existing = await conn.fetchrow(
                    """
                    SELECT * FROM region_monthly_orders
                    WHERE user_id = $1 AND region = $2 AND service_slug IS NOT DISTINCT FROM $3::text
                      AND state = 'pending_payment'
                    FOR UPDATE
                    """,
                    user_id, purchase.region, purchase.service_slug,
                )
                if existing:
                    existing = dict(existing)
                    if _same_purchase(existing, purchase, terms_version, terms_sha256, stripe_price_id):
                        return existing, True
                    # A different purchase: close the earlier session before it can be paid.
                    if existing["stripe_checkout_session_id"]:
                        try:
                            stripe.checkout.Session.expire(existing["stripe_checkout_session_id"])
                        except stripe.StripeError as exc:
                            logger.warning("Region Monthly: could not expire the earlier session: %s", exc)
                            raise OrderRefusal("checkout_still_open", 409, CHECKOUT_STILL_OPEN) from exc
                    await conn.execute(
                        "UPDATE region_monthly_orders SET state = 'expired', updated_at = NOW() WHERE id = $1",
                        existing["id"],
                    )
                created = await conn.fetchrow(
                    _INSERT_ORDER,
                    user_id, email, purchase.region, purchase.service_slug, purchase.kind, len(months), months,
                    [m.period_month for m in future], [m.available_from for m in future], accepted_future_months,
                    purchase.price_pence, rm.CURRENCY, stripe_price_id, terms_version, terms_sha256,
                    datetime.now(timezone.utc) + CHECKOUT_LIFETIME,
                )
                return dict(created), False
        except asyncpg.UniqueViolationError:
            continue  # a concurrent submit created it first: read it on the next pass
    raise RegionMonthlyOrderError("could not reserve a Region Monthly order")


def months_text(months: list[date]) -> str:
    return ",".join(rm.month_key(m) for m in months)


def build_checkout_metadata(order: dict[str, Any]) -> dict[str, str]:
    """Correlation values for the Checkout Session. The webhook re-checks each one."""
    return {
        "type": METADATA_TYPE,
        "order_id": str(order["id"]),
        "user_id": str(order["user_id"]),
        "region": order["region"],
        "service": order["service_slug"] or ALL_SERVICES_METADATA,
        "kind": order["kind"],
        "months": months_text(list(order["months"])),
        "price_pence": str(order["price_pence"]),
        "price_id": order["stripe_price_id"],
        "terms_version": order["terms_version"],
        "terms_sha256": order["terms_sha256"],
        "business_use_confirmed": "true",
    }


def validate_checkout_price(kind: str) -> str | None:
    """Why the configured Stripe Price cannot be used, or None. A read-only Stripe call."""
    spec = rm.require_kind(kind)
    price_id = configured_price_id(kind)
    try:
        price = stripe_dict(stripe.Price.retrieve(price_id, expand=["product"]))
    except stripe.StripeError:
        return "the Stripe Price could not be read"
    product = price.get("product") or {}
    if not (
        price.get("id") == price_id
        and price.get("active") is True
        and price.get("livemode") is settings.stripe_secret_key.startswith("sk_live_")
        and price.get("currency") == rm.CURRENCY
        and price.get("unit_amount") == spec.price_pence
        and price.get("type") == "one_time"
        and price.get("recurring") is None
        and price.get("lookup_key") == stripe_price_lookup_key(kind)
        and hasattr(product, "get")
        and product.get("active") is True
    ):
        return f"the Stripe Price does not match the {kind} one-off catalogue entry"
    return None


async def attach_session(conn, order_id: Any, *, session_id: str, url: str, acceptance_id: int | None) -> None:
    updated = await conn.fetchval(
        """
        UPDATE region_monthly_orders
        SET stripe_checkout_session_id = $2, stripe_checkout_url = $3,
            contract_acceptance_id = $4, updated_at = NOW()
        WHERE id = $1 AND state = 'pending_payment' AND stripe_checkout_session_id IS NULL
        RETURNING id
        """,
        order_id, session_id, url, acceptance_id,
    )
    if updated is None:
        raise RegionMonthlyOrderError("the order could not be bound to its Checkout Session")


async def get_order_for_user(conn, order_id: Any, user_id: int) -> dict[str, Any] | None:
    """The order if it exists and belongs to this account. Anything else is None."""
    row = await conn.fetchrow("SELECT * FROM region_monthly_orders WHERE id = $1 AND user_id = $2", order_id, user_id)
    return dict(row) if row else None


# --------------------------------------------------------------------------
# What the buyer sees
# --------------------------------------------------------------------------

AVAILABLE = "available"
WILL_BE = "will_be_available"
NOT_BUILT = "not_built"
NOT_PAID_STATE = "not_paid"
REFUNDED_STATE = "refunded"
BEING_SET_UP_STATE = "being_set_up"

AVAILABILITY_TEXT = {
    AVAILABLE: "Available to download.",
    WILL_BE: "Will be available on {date}.",
    NOT_BUILT: "Not built yet. It is due from {date}.",
    NOT_PAID_STATE: "Available once the order is paid.",
    REFUNDED_STATE: "Not available. This order was refunded.",
    BEING_SET_UP_STATE: "Your access is being set up.",
}


def month_availability(
    order: dict[str, Any],
    month: date,
    *,
    entitled: set[date],
    build: dict[str, Any] | None,
    now: datetime,
) -> str:
    """One purchased month's state: needs a paid order, an entitlement and a stored build."""
    if order["state"] == REFUNDED:
        return REFUNDED_STATE
    if order["state"] != PAID:
        return NOT_PAID_STATE
    if month not in entitled:
        return BEING_SET_UP_STATE
    if build is not None:
        return AVAILABLE
    return NOT_BUILT if rm.is_buildable(month, now) else WILL_BE


def order_view(
    order: dict[str, Any],
    *,
    builds: dict[date, dict[str, Any]],
    entitled: set[date],
    now: datetime,
) -> dict[str, Any]:
    """The buyer's view of an order. Never Stripe identifiers or the terms hash."""
    future = dict(zip(order["future_months"], order["future_available_from"], strict=True))
    months = []
    for month in order["months"]:
        build = builds.get(month)
        availability = month_availability(order, month, entitled=entitled, build=build, now=now)
        due = rm.available_on(month)
        months.append(
            {
                "month": rm.month_key(month),
                "label": rm.format_month(month),
                "was_future_at_purchase": month in future,
                "available_from": future[month].isoformat() if month in future else None,
                "availability": availability,
                "text": AVAILABILITY_TEXT[availability].format(date=rm.format_day(due)),
                "build_version": build["build_version"] if build and availability == AVAILABLE else None,
                "content_sha256": build["content_sha256"] if build and availability == AVAILABLE else None,
            }
        )
    return {
        "order_id": str(order["id"]),
        "state": order["state"],
        "region": order["region"],
        "service": order["service_slug"],
        "kind": order["kind"],
        "price_pence": order["price_pence"],
        "currency": order["currency"],
        "terms_version": order["terms_version"],
        "months": months,
        "future_months": [rm.month_key(m) for m in order["future_months"]],
        "future_month_notice": rm.FUTURE_MONTH_NOTICE if order["future_months"] else None,
        "created_at": order["created_at"].isoformat(),
        "paid_at": order["paid_at"].isoformat() if order["paid_at"] else None,
        "refunded_at": order["refunded_at"].isoformat() if order["refunded_at"] else None,
    }


async def load_order_view(conn, order: dict[str, Any], now: datetime) -> dict[str, Any]:
    builds = {
        row["period_month"]: dict(row)
        for row in await conn.fetch(
            q.LATEST_BUILDS_FOR_MONTHS, order["region"], order["service_slug"], list(order["months"])
        )
    }
    entitled = {row["period_month"] for row in await conn.fetch(q.ENTITLED_MONTHS, order["id"])}
    return order_view(order, builds=builds, entitled=entitled, now=now)


async def resolve_download(conn, order: dict[str, Any], month: date, now: datetime) -> dict[str, Any]:
    """The build to serve for one purchased month, or an :class:`OrderRefusal`.

    The order must be paid, the month must have its entitlement, and a build must
    exist at this moment. The latest build version of the month is served.
    """
    if order["state"] == REFUNDED:
        raise OrderRefusal("order_refunded", 410, REFUNDED_TEXT)
    if order["state"] != PAID:
        raise OrderRefusal("order_not_paid", 402, NOT_PAID)
    entitled = {row["period_month"] for row in await conn.fetch(q.ENTITLED_MONTHS, order["id"])}
    if month not in entitled:
        raise OrderRefusal("access_being_set_up", 409, BEING_SET_UP)
    row = await conn.fetchrow(q.LATEST_BUILD_FULL, order["region"], order["service_slug"], month)
    if row is None:
        due = rm.available_on(month)
        label = rm.format_month(month)
        if rm.is_buildable(month, now):
            raise OrderRefusal(
                "month_not_built", 409, NOT_BUILT_YET.format(month=label, date=rm.format_day(due)),
                available_from=due.isoformat(),
            )
        raise OrderRefusal(
            "month_not_available_yet", 409, WILL_BE_AVAILABLE.format(month=label, date=rm.format_day(due)),
            available_from=due.isoformat(),
        )
    return _build_dict(row)


def _build_dict(row: Any) -> dict[str, Any]:
    build = dict(row)
    for key in ("metrics", "coverage", "limits"):
        if isinstance(build[key], (str, bytes)):
            build[key] = json.loads(build[key])
    return build


# --------------------------------------------------------------------------
# The signed payment event
# --------------------------------------------------------------------------


def _retrieve_session(session_id: str) -> dict[str, Any]:
    return stripe_dict(stripe.checkout.Session.retrieve(session_id, expand=["line_items"]))


def _payment_intent_of(value: Any) -> str:
    if hasattr(value, "get"):
        value = value.get("id")
    if not isinstance(value, str) or not value.strip().startswith("pi_") or len(value.strip()) <= 3:
        raise RegionMonthlyOrderError("region-monthly checkout has no valid authoritative payment intent")
    return value.strip()


def _as_uuid(value: Any) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except ValueError as exc:
        raise RegionMonthlyOrderError("region-monthly order id is malformed") from exc


_LOCK_PAYMENT = "SELECT pg_advisory_xact_lock(hashtextextended('caregist-payment:' || $1, 0))"

_FULLY_REFUNDED = """
SELECT EXISTS (
  SELECT 1 FROM audit_log
  WHERE action = 'billing.charge.refund'
    AND metadata->>'payment_intent' = $1
    AND metadata->>'fully_refunded' = 'true'
)
"""


async def handle_checkout_completed(conn, session: dict[str, Any]) -> None:
    """Pay one order and create its entitlements from a signature-verified payment event.

    Runs inside the webhook's transaction. Safe to run again for the same session: a
    paid order is a no-op apart from filling any entitlement that is missing, so a
    second delivery never creates a second entitlement.
    """
    session_id = session.get("id")
    if not session_id:
        raise RegionMonthlyOrderError("region-monthly checkout missing session id")
    authoritative = _retrieve_session(session_id)
    metadata = authoritative.get("metadata") or {}
    order_id = metadata.get("order_id")
    if metadata.get("type") != METADATA_TYPE or not order_id:
        raise RegionMonthlyOrderError("region-monthly checkout missing immutable order metadata")
    status = authoritative.get("payment_status")
    if status == "unpaid":
        # A delayed payment method: the later async_payment_succeeded event pays it.
        logger.info("Region-monthly session %s completed unpaid; waiting for payment", session_id)
        return
    if status != "paid":
        raise RegionMonthlyOrderError("region-monthly checkout completed before payment became valid")
    amount_total = authoritative.get("amount_total")
    currency = authoritative.get("currency")
    payment_intent = _payment_intent_of(authoritative.get("payment_intent"))

    await conn.execute(_LOCK_PAYMENT, payment_intent)
    fully_refunded = await conn.fetchval(_FULLY_REFUNDED, payment_intent)
    order = await conn.fetchrow("SELECT * FROM region_monthly_orders WHERE id = $1 FOR UPDATE", _as_uuid(order_id))
    if not order:
        raise RegionMonthlyOrderError("region-monthly checkout does not match a reserved order")
    order = dict(order)
    expected_price = rm.require_kind(order["kind"]).price_pence  # the central price, not a stored copy
    if currency != rm.CURRENCY or amount_total != expected_price or order["price_pence"] != expected_price:
        raise RegionMonthlyOrderError("region-monthly checkout was not paid at the catalogue price")
    if order["stripe_checkout_session_id"] not in (None, session_id):
        raise RegionMonthlyOrderError("region-monthly checkout does not match the order's session")
    if order["stripe_payment_intent_id"] not in (None, payment_intent):
        raise RegionMonthlyOrderError("region-monthly checkout conflicts with durable payment evidence")
    if order["amount_total"] not in (None, amount_total):
        raise RegionMonthlyOrderError("region-monthly checkout conflicts with durable payment evidence")
    if (
        metadata.get("user_id") != str(order["user_id"])
        or metadata.get("region") != order["region"]
        or metadata.get("service") != (order["service_slug"] or ALL_SERVICES_METADATA)
        or metadata.get("kind") != order["kind"]
        or metadata.get("months") != months_text(list(order["months"]))
        or metadata.get("price_id") != order["stripe_price_id"]
        or metadata.get("price_pence") != str(order["price_pence"])
        or order["currency"] != rm.CURRENCY
    ):
        raise RegionMonthlyOrderError("region-monthly checkout does not match its pinned order")
    line_items = (authoritative.get("line_items") or {}).get("data", [])
    actual = [((item.get("price") or {}).get("id"), int(item.get("quantity") or 0)) for item in line_items]
    if actual != [(order["stripe_price_id"], 1)]:
        raise RegionMonthlyOrderError(f"region-monthly checkout has unexpected line items: {actual!r}")
    acceptance = await conn.fetchrow(
        """
        SELECT user_id, terms_version, terms_sha256, business_use_confirmed
        FROM b2b_contract_acceptances WHERE stripe_checkout_session_id = $1
        """,
        session_id,
    )
    if (
        not acceptance
        or int(acceptance["user_id"]) != int(order["user_id"])
        or acceptance["terms_version"] != order["terms_version"]
        or acceptance["terms_sha256"] != order["terms_sha256"]
        or metadata.get("terms_version") != order["terms_version"]
        or metadata.get("terms_sha256") != order["terms_sha256"]
        or not acceptance["business_use_confirmed"]
    ):
        raise RegionMonthlyOrderError("region-monthly checkout has no matching immutable B2B acceptance")

    state = order["state"]
    if state == REFUNDED:
        logger.info("Region-monthly order %s is refunded; no entitlement is created", order_id)
        return
    if fully_refunded:
        await _bind_payment(conn, order, session_id, payment_intent, amount_total)
        await conn.execute(
            "UPDATE region_monthly_orders SET state = 'refunded', refunded_at = COALESCE(refunded_at, NOW()), "
            "updated_at = NOW() WHERE id = $1 AND state <> 'refunded'",
            order["id"],
        )
        logger.info("Region-monthly order %s was refunded before payment was recorded", order_id)
        return

    first_payment = state in (PENDING, EXPIRED)
    if first_payment:
        order = await _bind_payment(conn, order, session_id, payment_intent, amount_total)
    context = {
        "payment_intent": payment_intent,
        "amount_total": amount_total,
        "currency": currency,
        "stripe_checkout_session_id": session_id,
    }
    try:
        await grant_entitlements(conn, order, first_payment=first_payment)
    except Exception as exc:  # noqa: BLE001 - the failure is recorded and Stripe redelivers
        message = f"{type(exc).__name__}: {exc}"[:500]
        logger.exception("Region-monthly entitlements failed for order %s", order_id)
        # The webhook releases its locks before the failure is written on another
        # connection. Writing it here would wait on this transaction's own row lock.
        raise EntitlementError(str(order_id), message, context) from exc


async def _bind_payment(conn, order: dict[str, Any], session_id: str, payment_intent: str, amount_total: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        UPDATE region_monthly_orders
        SET state = CASE WHEN state IN ('pending_payment', 'expired') THEN 'paid' ELSE state END,
            stripe_checkout_session_id = COALESCE(stripe_checkout_session_id, $2),
            stripe_payment_intent_id = COALESCE(stripe_payment_intent_id, $3),
            amount_total = COALESCE(amount_total, $4),
            paid_at = COALESCE(paid_at, NOW()),
            updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        order["id"], session_id, payment_intent, amount_total,
    )
    return dict(row)


# --------------------------------------------------------------------------
# Entitlements
# --------------------------------------------------------------------------


async def _insert_entitlements(conn, order_id: Any) -> list[date]:
    """One row per purchased month. A month that already has its row is left alone."""
    rows = await conn.fetch(q.INSERT_ENTITLEMENTS, order_id)
    return [row["period_month"] for row in rows]


async def grant_entitlements(conn, order: dict[str, Any], *, first_payment: bool = False) -> int:
    """Create the missing entitlements for a paid order. Returns how many were created.

    Everything runs in one savepoint, so a failure leaves no partial set behind. The
    audit event is written only when rows were created, so a replay writes none.
    """
    if order["state"] != PAID:
        raise RegionMonthlyOrderError(f"an order in state {order['state']} cannot be granted")
    async with conn.transaction():
        created = await _insert_entitlements(conn, order["id"])
        held = await conn.fetchval("SELECT count(*) FROM region_monthly_entitlements WHERE order_id = $1", order["id"])
        if held != order["month_count"]:
            raise RegionMonthlyOrderError("the order does not hold one entitlement for each purchased month")
        if created or first_payment:
            await conn.execute(
                "UPDATE region_monthly_orders SET last_error = NULL, updated_at = NOW() WHERE id = $1",
                order["id"],
            )
        if created:
            await write_audit_log(
                action="region_monthly.order.paid",
                outcome="success",
                actor={"type": "system", "name": "stripe"},
                target_type="region_monthly_order",
                target_id=str(order["id"]),
                metadata={
                    "region": order["region"],
                    "service": order["service_slug"],
                    "kind": order["kind"],
                    "months": [rm.month_key(m) for m in created],
                    "future_months": [rm.month_key(m) for m in order["future_months"]],
                },
                conn=conn,
                strict=True,
            )
            overlaps = await conn.fetch(
                """
                SELECT id FROM region_monthly_orders
                WHERE user_id = $1 AND region = $2 AND service_slug IS NOT DISTINCT FROM $3::text
                  AND state = 'paid' AND id <> $4 AND months && $5::date[]
                """,
                order["user_id"], order["region"], order["service_slug"], order["id"], list(order["months"]),
            )
            if overlaps:
                # Two payments for the same months: access is granted, and the founder is told.
                logger.error("Region-monthly order %s overlaps a paid order of the same account", order["id"])
                await write_audit_log(
                    action="region_monthly.order.overlap_paid",
                    outcome="failure",
                    actor={"type": "system", "name": "stripe"},
                    target_type="region_monthly_order",
                    target_id=str(order["id"]),
                    metadata={"other_orders": [str(row["id"]) for row in overlaps]},
                    conn=conn,
                    strict=True,
                )
    return len(created)


async def record_entitlement_failure(order_id: str, message: str, context: dict[str, Any]) -> None:
    """Leave the order ``paid`` with the error and a count of attempts.

    Runs on a fresh connection after the webhook transaction rolled back, and
    restores the payment evidence that rollback removed.
    """
    payment_intent = context.get("payment_intent")
    session_id = context.get("stripe_checkout_session_id")
    amount_total = context.get("amount_total")
    if (
        not isinstance(payment_intent, str) or not payment_intent.startswith("pi_")
        or not isinstance(session_id, str) or not session_id
        or not isinstance(amount_total, int) or context.get("currency") != rm.CURRENCY
    ):
        raise RegionMonthlyOrderError("region-monthly failure recorder rejected an invalid payment context")
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute(_LOCK_PAYMENT, payment_intent)
            order = await conn.fetchrow("SELECT * FROM region_monthly_orders WHERE id = $1 FOR UPDATE", _as_uuid(order_id))
            if not order:
                raise RegionMonthlyOrderError("region-monthly failure recorder could not find its order")
            if amount_total != rm.require_kind(order["kind"]).price_pence:
                raise RegionMonthlyOrderError("region-monthly failure recorder rejected an invalid amount")
            if (
                order["stripe_checkout_session_id"] not in (None, session_id)
                or order["stripe_payment_intent_id"] not in (None, payment_intent)
            ):
                raise RegionMonthlyOrderError("region-monthly failure recorder found conflicting payment identity")
            if order["state"] == REFUNDED:
                return
            if await conn.fetchval(_FULLY_REFUNDED, payment_intent):
                await _bind_payment(conn, dict(order), session_id, payment_intent, amount_total)
                await conn.execute(
                    "UPDATE region_monthly_orders SET state = 'refunded', refunded_at = COALESCE(refunded_at, NOW()), "
                    "updated_at = NOW() WHERE id = $1",
                    order["id"],
                )
                return
            await _bind_payment(conn, dict(order), session_id, payment_intent, amount_total)
            await conn.execute(
                """
                UPDATE region_monthly_orders
                SET entitlement_attempts = entitlement_attempts + 1, last_error = $2::text, updated_at = NOW()
                WHERE id = $1
                """,
                order["id"], message[:500],
            )


async def grant_outstanding(conn, *, apply: bool, limit: int = 50) -> list[dict[str, Any]]:
    """Finish paid orders that lack some entitlement. Dry run unless ``apply``."""
    rows = await conn.fetch(
        """
        SELECT o.id, o.entitlement_attempts, o.last_error
        FROM region_monthly_orders o
        WHERE o.state = 'paid'
          AND (SELECT count(*) FROM region_monthly_entitlements e WHERE e.order_id = o.id) < o.month_count
        ORDER BY o.updated_at, o.id LIMIT $1
        """,
        limit,
    )
    report: list[dict[str, Any]] = []
    for row in rows:
        item = {"order_id": str(row["id"]), "attempts": row["entitlement_attempts"], "last_error": row["last_error"]}
        if not apply:
            report.append({**item, "result": "would_grant"})
            continue
        try:
            async with conn.transaction():
                locked = await conn.fetchrow(
                    "SELECT * FROM region_monthly_orders WHERE id = $1 AND state = 'paid' FOR UPDATE SKIP LOCKED",
                    row["id"],
                )
                if locked is None:
                    report.append({**item, "result": "skipped"})
                    continue
                if await conn.fetchval(_FULLY_REFUNDED, locked["stripe_payment_intent_id"]):
                    report.append({**item, "result": "skipped_refunded"})
                    continue
                await grant_entitlements(conn, dict(locked))
            report.append({**item, "result": "granted"})
        except Exception as exc:  # noqa: BLE001 - recorded, then the next order is tried
            message = f"{type(exc).__name__}: {exc}"[:500]
            logger.exception("Retry failed for region-monthly order %s", row["id"])
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE region_monthly_orders
                    SET entitlement_attempts = entitlement_attempts + 1, last_error = $2::text, updated_at = NOW()
                    WHERE id = $1 AND state = 'paid'
                    """,
                    row["id"], message,
                )
            report.append({**item, "result": "failed", "error": message})
    return report


# --------------------------------------------------------------------------
# Refunds
# --------------------------------------------------------------------------


async def mark_refunded(conn, payment_intent: str) -> str | None:
    """Move the order bought with this payment to ``refunded`` and withdraw downloads.

    Called from the shared refund handler for a full refund. Changes state only: the
    purchased months and the entitlement rows stay as they were. Returns the order id.
    """
    row = await conn.fetchrow(
        """
        UPDATE region_monthly_orders
        SET state = 'refunded', refunded_at = NOW(), updated_at = NOW()
        WHERE stripe_payment_intent_id = $1 AND state = 'paid'
        RETURNING id
        """,
        payment_intent,
    )
    if row is None:
        return None
    await write_audit_log(
        action="region_monthly.order.refund",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="region_monthly_order",
        target_id=str(row["id"]),
        metadata={"payment_intent": payment_intent},
        conn=conn,
    )
    return str(row["id"])


@dataclass(frozen=True)
class DownloadFile:
    filename: str
    content_type: str
    content: bytes
    sha256: str
    build_version: int


def render_download(build: dict[str, Any], fmt: str) -> DownloadFile:
    """The CSV or PDF for one stored build. Refuses a build whose stored hash does not match."""
    if not render.verify_build(build):
        raise RegionMonthlyOrderError("the stored build no longer matches its content_sha256")
    if fmt == "csv":
        content, content_type = render.render_csv(build), render.CSV_CONTENT_TYPE
    elif fmt == "pdf":
        content, content_type = render.render_pdf(build), render.PDF_CONTENT_TYPE
    else:
        raise ValueError(f"unknown deliverable format {fmt!r}")
    return DownloadFile(
        filename=render.deliverable_filename(
            build["region"], build["service_slug"], build["period_month"], build["build_version"], fmt
        ),
        content_type=content_type,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        build_version=int(build["build_version"]),
    )
