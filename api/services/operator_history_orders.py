"""Operator History (stage 2): orders, the signed payment event, delivery and refunds.

The paid path, in order:

1. Checkout (``api/routers/operator_history_orders.py``) re-resolves the operator,
   builds the record and pins it to a new order together with the price. Nothing
   reaches Stripe unless every stage 1 check passed.
2. The signed ``checkout.session.completed`` event reaches
   :func:`handle_checkout_completed` through the shared webhook. It checks the
   authoritative Stripe session against the pinned order, marks the order paid and
   delivers the CSV and PDF built from the pinned record.
3. A delivery failure raises :class:`DeliveryError`. The shared webhook rolls its
   transaction back and then calls ``record_failure`` on a fresh connection, so the
   order is left ``paid`` with a visible error. Stripe redelivers the same event, or
   ``tools/retry_operator_history_delivery.py`` runs, and either finishes the order.
   Delivery happens once: artefacts are append-only and unique per order and format,
   and the state change to ``delivered`` is guarded in the database.
4. A full refund (``_handle_refund`` calls :func:`mark_refunded`) moves the order to
   ``refunded`` and the download is refused. The delivered bytes and the pinned
   record are never changed.

Nothing here calls a model, and nothing here writes customer-facing text: the files
come from ``operator_history_render``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

import asyncpg
import stripe

from api.config import settings
from api.database import get_connection
from api.services import operator_history as oh
from api.services import operator_history_render as render
from api.services.cqc_reconciliation_evidence import FRESHNESS_SLA
from api.utils.audit import write_audit_log
from api.utils.stripe_compat import stripe_dict

logger = logging.getLogger("caregist.operator_history_orders")

METADATA_TYPE = "operator_history"

# The one place the price is defined. The client never sends a price: the checkout
# request model refuses unknown fields, the Stripe Price is verified against these
# values before a session exists, and the webhook refuses any other amount.
OPERATOR_HISTORY_PRICE_PENCE = 9500
OPERATOR_HISTORY_CURRENCY = "gbp"
# The lookup key the Stripe Price must carry, as for the Territory Brief's Price.
STRIPE_PRICE_LOOKUP_KEY = "operator_history_gbp_oneoff_v1"

# A Checkout Session needs at least 30 minutes. One hour leaves room to recover a
# lost response: a retried create with the same idempotency key and parameters
# still satisfies Stripe's minimum.
CHECKOUT_LIFETIME = timedelta(hours=1)
MAX_DELIVERY_ATTEMPTS = 5

PENDING = "pending_payment"
PAID = "paid"
DELIVERED = "delivered"
REFUNDED = "refunded"
FAILED = "failed"
EXPIRED = "expired"
ORDER_STATES = (PENDING, PAID, DELIVERED, REFUNDED, FAILED, EXPIRED)


class OperatorHistoryOrderError(RuntimeError):
    """A paid-path state that must make Stripe redeliver the event."""


class DeliveryError(OperatorHistoryOrderError):
    """Carry the failure recorder to the webhook's post-rollback boundary."""

    def __init__(self, order_id: str, message: str, context: dict[str, Any]):
        super().__init__(f"operator-history delivery failed for order {order_id}: {message}")
        self.order_id = order_id
        self.failure_message = message
        self.context = context

    async def record_failure(self) -> None:
        await record_delivery_failure(self.order_id, self.failure_message, self.context)


@dataclass(frozen=True)
class Pin:
    """What a purchase pins: the build, the edition rows used and the price."""

    legal_name: str
    schema_version: int
    content_sha256: str
    edition_id: int
    edition_ids: tuple[int, ...]
    providers_sha256: str
    locations_sha256: str
    price_pence: int = OPERATOR_HISTORY_PRICE_PENCE
    currency: str = OPERATOR_HISTORY_CURRENCY


def pin_record(operator: oh.ResolvedOperator, record: dict[str, Any]) -> Pin:
    ids = [held.edition_id for held in operator.held_names]
    if not ids or any(value is None for value in ids):
        raise OperatorHistoryOrderError("the resolved operator carries no stored edition to pin")
    edition = record["provider"]["edition"]
    latest = operator.held_names[-1].edition_id
    assert latest is not None
    return Pin(
        legal_name=record["provider"]["legal_name"],
        schema_version=int(record["schema_version"]),
        content_sha256=record["content_sha256"],
        edition_id=int(latest),
        edition_ids=tuple(sorted({int(value) for value in ids if value is not None})),
        providers_sha256=edition["providers_sha256"],
        locations_sha256=edition["locations_sha256"],
    )


# --------------------------------------------------------------------------
# Readiness
# --------------------------------------------------------------------------

SQL_LATEST_EDITION = """
SELECT e.id, e.source_retrieved_at, e.location_count,
       (SELECT count(*) FROM territory_brief_source_locations l WHERE l.edition_id = e.id) AS held_count
FROM territory_brief_source_editions e
ORDER BY e.source_retrieved_at DESC, e.id DESC
LIMIT 1
"""


async def readiness_gap(conn, get_health: Callable[[Any], Awaitable[dict[str, Any]]]) -> str | None:
    """Why checkout must stay closed, or None when the source evidence is accepted.

    Uses the same pipeline-health snapshot as the Radar gate
    (``billing._require_radar_commerce_ready``): the pipeline's own checks passed, the
    CQC source is fresh and its counts reconcile. The Radar-only parts (shadow signal
    polling, ledger latency, the Radar delivery switch and outbox) are not asked,
    because Operator History is not a Radar delivery. It adds one check of its own: the
    newest stored CQC edition, which supplies provider names, must be complete and
    inside the freshness window.
    """
    health = await get_health(conn)
    if not health.get("readiness_ok"):
        return "pipeline readiness checks have not passed"
    if not health.get("source_fresh"):
        return "the CQC source is not fresh"
    if not (health.get("units") or {}).get("countsReconciled"):
        return "the CQC source counts are not reconciled"
    edition = await conn.fetchrow(SQL_LATEST_EDITION)
    if edition is None:
        return "no CQC evidence edition is stored"
    age = datetime.now(timezone.utc) - edition["source_retrieved_at"]
    if age.total_seconds() < 0 or age > FRESHNESS_SLA:
        return "the newest stored CQC edition is stale or future dated"
    if edition["held_count"] != edition["location_count"]:
        return "the newest stored CQC edition is incomplete"
    return None


# --------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------

_INSERT_ORDER = """
INSERT INTO operator_history_orders (
  user_id, customer_email, provider_id, legal_name, price_pence, currency, stripe_price_id,
  record_schema_version, record, content_sha256, edition_id, edition_ids,
  edition_providers_sha256, edition_locations_sha256, terms_version, terms_sha256,
  checkout_expires_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11, $12::bigint[], $13, $14, $15, $16, $17)
RETURNING *
"""


async def reserve_order(
    conn,
    *,
    user_id: int,
    email: str,
    provider_id: str,
    pin: Pin,
    record: dict[str, Any],
    terms_version: str,
    terms_sha256: str,
    stripe_price_id: str,
) -> tuple[dict[str, Any], bool]:
    """The one pending order for this account and operator: reused, or newly created.

    A double submit finds the pending order and gets it back (``reused`` is true), so
    only one payable session can exist. A pending order past its checkout lifetime, or
    one taken under other terms or another Stripe Price, is expired first. A later
    deliberate purchase of the same operator (the earlier one is paid) is a new order.
    """
    body = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    for _attempt in range(2):
        try:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE operator_history_orders SET state = 'expired', updated_at = NOW()
                    WHERE user_id = $1 AND provider_id = $2 AND state = 'pending_payment'
                      AND (checkout_expires_at <= NOW() OR terms_version <> $3
                           OR terms_sha256 <> $4 OR stripe_price_id <> $5)
                    """,
                    user_id, provider_id, terms_version, terms_sha256, stripe_price_id,
                )
                existing = await conn.fetchrow(
                    """
                    SELECT * FROM operator_history_orders
                    WHERE user_id = $1 AND provider_id = $2 AND state = 'pending_payment'
                    FOR UPDATE
                    """,
                    user_id, provider_id,
                )
                if existing:
                    return dict(existing), True
                created = await conn.fetchrow(
                    _INSERT_ORDER,
                    user_id, email, provider_id, pin.legal_name, pin.price_pence, pin.currency,
                    stripe_price_id, pin.schema_version, body, pin.content_sha256, pin.edition_id,
                    list(pin.edition_ids), pin.providers_sha256, pin.locations_sha256,
                    terms_version, terms_sha256, datetime.now(timezone.utc) + CHECKOUT_LIFETIME,
                )
                return dict(created), False
        except asyncpg.UniqueViolationError:
            continue  # a concurrent submit created it first: read it on the next pass
    raise OperatorHistoryOrderError("could not reserve an Operator History order")


def build_checkout_metadata(order: dict[str, Any]) -> dict[str, str]:
    """Correlation values for the Checkout Session. The webhook re-checks each one."""
    return {
        "type": METADATA_TYPE,
        "order_id": str(order["id"]),
        "user_id": str(order["user_id"]),
        "provider_id": order["provider_id"],
        "content_sha256": order["content_sha256"],
        "price_pence": str(order["price_pence"]),
        "price_id": order["stripe_price_id"],
        "terms_version": order["terms_version"],
        "terms_sha256": order["terms_sha256"],
        "business_use_confirmed": "true",
    }


def validate_checkout_price() -> str | None:
    """Why the configured Stripe Price cannot be used, or None. A read-only Stripe call."""
    price_id = settings.stripe_price_operator_history
    try:
        price = stripe_dict(stripe.Price.retrieve(price_id, expand=["product"]))
    except stripe.StripeError:
        return "the Stripe Price could not be read"
    product = price.get("product") or {}
    if not (
        price.get("id") == price_id
        and price.get("active") is True
        and price.get("livemode") is settings.stripe_secret_key.startswith("sk_live_")
        and price.get("currency") == OPERATOR_HISTORY_CURRENCY
        and price.get("unit_amount") == OPERATOR_HISTORY_PRICE_PENCE
        and price.get("type") == "one_time"
        and price.get("recurring") is None
        and price.get("lookup_key") == STRIPE_PRICE_LOOKUP_KEY
        and hasattr(product, "get")
        and product.get("active") is True
    ):
        return "the Stripe Price does not match the GBP 95.00 one-off catalogue entry"
    return None


async def attach_session(conn, order_id: Any, *, session_id: str, url: str, acceptance_id: int | None) -> None:
    updated = await conn.fetchval(
        """
        UPDATE operator_history_orders
        SET stripe_checkout_session_id = $2, stripe_checkout_url = $3,
            contract_acceptance_id = $4, updated_at = NOW()
        WHERE id = $1 AND state = 'pending_payment' AND stripe_checkout_session_id IS NULL
        RETURNING id
        """,
        order_id, session_id, url, acceptance_id,
    )
    if updated is None:
        raise OperatorHistoryOrderError("the order could not be bound to its Checkout Session")


# Every column except the (large) pinned record, plus the two edition dates read out of it.
_VIEW_COLUMNS = """
  id, user_id, customer_email, provider_id, legal_name, state, price_pence, currency, stripe_price_id,
  record_schema_version, content_sha256, edition_id, edition_ids, edition_providers_sha256,
  edition_locations_sha256, terms_version, terms_sha256, contract_acceptance_id, stripe_checkout_session_id,
  stripe_checkout_url, checkout_expires_at, stripe_payment_intent_id, amount_total, delivery_attempts,
  last_error, csv_sha256, pdf_sha256, created_at, updated_at, paid_at, delivered_at, refunded_at,
  record #>> '{provider,edition,retrieved_on}' AS edition_retrieved_on,
  record #>> '{provider,edition,source_as_of}' AS edition_source_as_of
"""


async def get_order_for_user(conn, order_id: Any, user_id: int) -> dict[str, Any] | None:
    """The order if it exists and belongs to this account. Anything else is None."""
    row = await conn.fetchrow(
        f"SELECT {_VIEW_COLUMNS} FROM operator_history_orders WHERE id = $1 AND user_id = $2",
        order_id, user_id,
    )
    return dict(row) if row else None


def order_view(order: dict[str, Any]) -> dict[str, Any]:
    """The buyer's view of an order. Never the record body or the Stripe identifiers."""
    retrieved_on = order.get("edition_retrieved_on")
    source_as_of = order.get("edition_source_as_of")
    if retrieved_on is None or source_as_of is None:
        edition = _record_of(order)["provider"]["edition"]
        retrieved_on, source_as_of = edition["retrieved_on"], edition["source_as_of"]
    delivered = order["state"] == DELIVERED
    return {
        "order_id": str(order["id"]),
        "state": order["state"],
        "provider_id": order["provider_id"],
        "legal_name": order["legal_name"],
        "price_pence": order["price_pence"],
        "currency": order["currency"],
        "content_sha256": order["content_sha256"],
        "edition": {
            "retrieved_on": retrieved_on,
            "source_as_of": source_as_of,
            "providers_sha256": order["edition_providers_sha256"],
            "locations_sha256": order["edition_locations_sha256"],
        },
        "terms_version": order["terms_version"],
        "created_at": order["created_at"].isoformat(),
        "paid_at": order["paid_at"].isoformat() if order["paid_at"] else None,
        "delivered_at": order["delivered_at"].isoformat() if order["delivered_at"] else None,
        "downloads": (
            {"csv": {"sha256": order["csv_sha256"]}, "pdf": {"sha256": order["pdf_sha256"]}} if delivered else None
        ),
    }


def _record_of(order: dict[str, Any]) -> dict[str, Any]:
    record = order["record"]
    return json.loads(record) if isinstance(record, (str, bytes)) else record


async def fetch_artefact(conn, order_id: Any, fmt: str) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        """
        SELECT filename, content_type, content, artefact_sha256
        FROM operator_history_artefacts WHERE order_id = $1 AND format = $2
        """,
        order_id, fmt,
    )
    return dict(row) if row else None


# --------------------------------------------------------------------------
# The signed payment event
# --------------------------------------------------------------------------


def _retrieve_session(session_id: str) -> dict[str, Any]:
    return stripe_dict(stripe.checkout.Session.retrieve(session_id, expand=["line_items"]))


def _payment_intent_of(value: Any) -> str:
    if hasattr(value, "get"):
        value = value.get("id")
    if not isinstance(value, str) or not value.strip().startswith("pi_") or len(value.strip()) <= 3:
        raise OperatorHistoryOrderError("operator-history checkout has no valid authoritative payment intent")
    return value.strip()


def _as_uuid(value: Any) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except ValueError as exc:
        raise OperatorHistoryOrderError("operator-history order id is malformed") from exc


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
    """Pay and deliver one order from a signature-verified ``checkout.session.completed``.

    Runs inside the webhook's transaction. Safe to run again for the same session:
    a delivered order is a no-op, so a second delivery never creates a second file.
    """
    session_id = session.get("id")
    if not session_id:
        raise OperatorHistoryOrderError("operator-history checkout missing session id")
    authoritative = _retrieve_session(session_id)
    metadata = authoritative.get("metadata") or {}
    order_id = metadata.get("order_id")
    if metadata.get("type") != METADATA_TYPE or not order_id:
        raise OperatorHistoryOrderError("operator-history checkout missing immutable order metadata")
    status = authoritative.get("payment_status")
    if status == "unpaid":
        # A delayed payment method: the later async_payment_succeeded event pays it.
        logger.info("Operator-history session %s completed unpaid; waiting for payment", session_id)
        return
    if status != "paid":
        raise OperatorHistoryOrderError("operator-history checkout completed before payment became valid")
    amount_total = authoritative.get("amount_total")
    currency = authoritative.get("currency")
    if currency != OPERATOR_HISTORY_CURRENCY or amount_total != OPERATOR_HISTORY_PRICE_PENCE:
        raise OperatorHistoryOrderError("operator-history checkout must be paid at GBP 95.00")
    payment_intent = _payment_intent_of(authoritative.get("payment_intent"))

    await conn.execute(_LOCK_PAYMENT, payment_intent)
    fully_refunded = await conn.fetchval(_FULLY_REFUNDED, payment_intent)
    order = await conn.fetchrow(
        "SELECT * FROM operator_history_orders WHERE id = $1 FOR UPDATE", _as_uuid(order_id)
    )
    if not order:
        raise OperatorHistoryOrderError("operator-history checkout does not match a reserved order")
    order = dict(order)
    if order["stripe_checkout_session_id"] not in (None, session_id):
        raise OperatorHistoryOrderError("operator-history checkout does not match the order's session")
    if order["stripe_payment_intent_id"] not in (None, payment_intent):
        raise OperatorHistoryOrderError("operator-history checkout conflicts with durable payment evidence")
    if order["amount_total"] not in (None, amount_total):
        raise OperatorHistoryOrderError("operator-history checkout conflicts with durable payment evidence")
    if (
        metadata.get("user_id") != str(order["user_id"])
        or metadata.get("provider_id") != order["provider_id"]
        or metadata.get("content_sha256") != order["content_sha256"]
        or metadata.get("price_id") != order["stripe_price_id"]
        or metadata.get("price_pence") != str(order["price_pence"])
        or order["price_pence"] != OPERATOR_HISTORY_PRICE_PENCE
        or order["currency"] != OPERATOR_HISTORY_CURRENCY
    ):
        raise OperatorHistoryOrderError("operator-history checkout does not match its pinned order")
    line_items = (authoritative.get("line_items") or {}).get("data", [])
    actual = [((item.get("price") or {}).get("id"), int(item.get("quantity") or 0)) for item in line_items]
    if actual != [(order["stripe_price_id"], 1)]:
        raise OperatorHistoryOrderError(f"operator-history checkout has unexpected line items: {actual!r}")
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
        raise OperatorHistoryOrderError("operator-history checkout has no matching immutable B2B acceptance")

    state = order["state"]
    if state == REFUNDED:
        logger.info("Operator-history order %s is refunded; nothing is delivered", order_id)
        return
    if fully_refunded:
        await _bind_payment(conn, order, session_id, payment_intent, amount_total)
        await conn.execute(
            "UPDATE operator_history_orders SET state = 'refunded', refunded_at = COALESCE(refunded_at, NOW()), "
            "updated_at = NOW() WHERE id = $1 AND state <> 'refunded'",
            order["id"],
        )
        logger.info("Operator-history order %s was refunded before payment was recorded", order_id)
        return
    if state == DELIVERED:
        logger.info("Operator-history order %s already delivered; duplicate event ignored", order_id)
        return

    if state in (PENDING, EXPIRED):
        order = await _bind_payment(conn, order, session_id, payment_intent, amount_total)
    context = {
        "payment_intent": payment_intent,
        "amount_total": amount_total,
        "currency": currency,
        "stripe_checkout_session_id": session_id,
    }
    try:
        await deliver_order(conn, order)
    except Exception as exc:  # noqa: BLE001 - the failure is recorded and Stripe redelivers
        message = f"{type(exc).__name__}: {exc}"[:500]
        logger.exception("Operator-history delivery failed for order %s", order_id)
        # The webhook releases its locks before the failure is written on another
        # connection. Writing it here would wait on this transaction's own row lock.
        raise DeliveryError(str(order_id), message, context) from exc


async def _bind_payment(conn, order: dict[str, Any], session_id: str, payment_intent: str, amount_total: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        UPDATE operator_history_orders
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
# Delivery
# --------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def deliver_order(conn, order: dict[str, Any]) -> bool:
    """Build both files from the pinned record and mark the order delivered.

    The caller holds the order row lock inside a transaction. Everything below runs
    in one savepoint, so a failure leaves no artefact and no state change behind.
    Returns False when the order is already delivered (nothing is done again) and
    raises on any failure.
    """
    if order["state"] == DELIVERED:
        return False
    if order["state"] not in (PAID, FAILED):
        raise OperatorHistoryOrderError(f"an order in state {order['state']} cannot be delivered")
    async with conn.transaction():
        record = _record_of(order)
        if oh.content_sha256(record) != order["content_sha256"]:
            raise OperatorHistoryOrderError("the stored record no longer matches its pinned content_sha256")
        built_on = order["created_at"].astimezone(timezone.utc).date()
        files = {
            "csv": (render.render_csv(record, built_on=built_on), render.CSV_CONTENT_TYPE),
            "pdf": (render.render_pdf(record, built_on=built_on), render.PDF_CONTENT_TYPE),
        }
        digests: dict[str, str] = {}
        for fmt, (data, content_type) in files.items():
            digest = _sha256(data)
            digests[fmt] = digest
            await conn.execute(
                """
                INSERT INTO operator_history_artefacts
                  (order_id, format, filename, content_type, content, byte_size, artefact_sha256)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (order_id, format) DO NOTHING
                """,
                order["id"], fmt, render.deliverable_filename(order["provider_id"], built_on, fmt),
                content_type, data, len(data), digest,
            )
            stored = await conn.fetchval(
                "SELECT artefact_sha256 FROM operator_history_artefacts WHERE order_id = $1 AND format = $2",
                order["id"], fmt,
            )
            if stored != digest:
                raise OperatorHistoryOrderError("a delivered file already exists with different content")
        updated = await conn.fetchval(
            """
            UPDATE operator_history_orders
            SET state = 'delivered', csv_sha256 = $2, pdf_sha256 = $3, delivered_at = NOW(),
                delivery_attempts = delivery_attempts + 1, last_error = NULL, updated_at = NOW()
            WHERE id = $1 AND state IN ('paid', 'failed')
            RETURNING id
            """,
            order["id"], digests["csv"], digests["pdf"],
        )
        if updated is None:
            raise OperatorHistoryOrderError("the order left the paid state during delivery")
        await write_audit_log(
            action="operator_history.order.deliver",
            outcome="success",
            actor={"type": "system", "name": "stripe"},
            target_type="operator_history_order",
            target_id=str(order["id"]),
            metadata={
                "provider_id": order["provider_id"],
                "content_sha256": order["content_sha256"],
                "csv_sha256": digests["csv"],
                "pdf_sha256": digests["pdf"],
                "edition_id": order["edition_id"],
            },
            conn=conn,
            strict=True,
        )
    return True


async def record_delivery_failure(order_id: str, message: str, context: dict[str, Any]) -> None:
    """Leave the order ``paid`` (or ``failed`` after repeated attempts) with the error.

    Runs on a fresh connection after the webhook transaction rolled back, and
    restores the payment evidence that rollback removed.
    """
    payment_intent = context.get("payment_intent")
    session_id = context.get("stripe_checkout_session_id")
    amount_total = context.get("amount_total")
    if (
        not isinstance(payment_intent, str) or not payment_intent.startswith("pi_")
        or not isinstance(session_id, str) or not session_id
        or amount_total != OPERATOR_HISTORY_PRICE_PENCE or context.get("currency") != OPERATOR_HISTORY_CURRENCY
    ):
        raise OperatorHistoryOrderError("operator-history failure recorder rejected an invalid payment context")
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute(_LOCK_PAYMENT, payment_intent)
            order = await conn.fetchrow(
                "SELECT * FROM operator_history_orders WHERE id = $1 FOR UPDATE", _as_uuid(order_id)
            )
            if not order:
                raise OperatorHistoryOrderError("operator-history failure recorder could not find its order")
            if (
                order["stripe_checkout_session_id"] not in (None, session_id)
                or order["stripe_payment_intent_id"] not in (None, payment_intent)
            ):
                raise OperatorHistoryOrderError("operator-history failure recorder found conflicting payment identity")
            if order["state"] in (DELIVERED, REFUNDED):
                return
            if await conn.fetchval(_FULLY_REFUNDED, payment_intent):
                await _bind_payment(conn, dict(order), session_id, payment_intent, amount_total)
                await conn.execute(
                    "UPDATE operator_history_orders SET state = 'refunded', refunded_at = COALESCE(refunded_at, NOW()), "
                    "updated_at = NOW() WHERE id = $1",
                    order["id"],
                )
                return
            bound = await _bind_payment(conn, dict(order), session_id, payment_intent, amount_total)
            attempts = min(int(bound["delivery_attempts"]) + 1, MAX_DELIVERY_ATTEMPTS)
            await conn.execute(
                """
                UPDATE operator_history_orders
                SET delivery_attempts = $2::int, last_error = $3::text, updated_at = NOW(),
                    state = CASE WHEN $2::int >= $4::int THEN 'failed' ELSE state END
                WHERE id = $1
                """,
                order["id"], attempts, message[:500], MAX_DELIVERY_ATTEMPTS,
            )


async def deliver_outstanding(conn, *, apply: bool, include_failed: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    """Finish orders that were paid and not delivered. Dry run unless ``apply``."""
    states = [PAID, FAILED] if include_failed else [PAID]
    rows = await conn.fetch(
        "SELECT id, state, delivery_attempts, last_error FROM operator_history_orders "
        "WHERE state = ANY($1::text[]) ORDER BY updated_at, id LIMIT $2",
        states, limit,
    )
    report: list[dict[str, Any]] = []
    for row in rows:
        item = {"order_id": str(row["id"]), "state": row["state"], "attempts": row["delivery_attempts"],
                "last_error": row["last_error"]}
        if not apply:
            report.append({**item, "result": "would_deliver"})
            continue
        try:
            async with conn.transaction():
                locked = await conn.fetchrow(
                    "SELECT * FROM operator_history_orders WHERE id = $1 AND state = ANY($2::text[]) "
                    "FOR UPDATE SKIP LOCKED",
                    row["id"], states,
                )
                if locked is None:
                    report.append({**item, "result": "skipped"})
                    continue
                if await conn.fetchval(_FULLY_REFUNDED, locked["stripe_payment_intent_id"]):
                    report.append({**item, "result": "skipped_refunded"})
                    continue
                await deliver_order(conn, dict(locked))
            report.append({**item, "result": "delivered"})
        except Exception as exc:  # noqa: BLE001 - recorded, then the next order is tried
            message = f"{type(exc).__name__}: {exc}"[:500]
            logger.exception("Retry delivery failed for operator-history order %s", row["id"])
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE operator_history_orders
                    SET delivery_attempts = LEAST(delivery_attempts + 1, $3::int), last_error = $2::text,
                        updated_at = NOW(),
                        state = CASE WHEN delivery_attempts + 1 >= $3::int THEN 'failed' ELSE state END
                    WHERE id = $1 AND state IN ('paid', 'failed')
                    """,
                    row["id"], message, MAX_DELIVERY_ATTEMPTS,
                )
            report.append({**item, "result": "failed", "error": message})
    return report


# --------------------------------------------------------------------------
# Refunds
# --------------------------------------------------------------------------


async def mark_refunded(conn, payment_intent: str) -> str | None:
    """Move the order bought with this payment to ``refunded`` and withdraw downloads.

    Called from the shared refund handler for a full refund. Changes state only: the
    pinned record and the delivered files stay as they were. Returns the order id.
    """
    row = await conn.fetchrow(
        """
        UPDATE operator_history_orders
        SET state = 'refunded', refunded_at = NOW(), updated_at = NOW()
        WHERE stripe_payment_intent_id = $1 AND state IN ('paid', 'delivered', 'failed')
        RETURNING id
        """,
        payment_intent,
    )
    if row is None:
        return None
    await write_audit_log(
        action="operator_history.order.refund",
        outcome="success",
        actor={"type": "system", "name": "stripe"},
        target_type="operator_history_order",
        target_id=str(row["id"]),
        metadata={"payment_intent": payment_intent},
        conn=conn,
    )
    return str(row["id"])
