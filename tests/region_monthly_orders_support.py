"""Shared test doubles for the Region Monthly paid path. No network, no real Stripe.

``RegionMonthlyStripeStub`` replaces the Stripe calls the product makes
(``checkout.Session.create`` / ``retrieve`` / ``expire`` and ``Price.retrieve``) by
replacing the attributes on the ``stripe`` module, the way the Operator History tests
do. It records every call, so a test can assert that a refusal made zero gateway
calls. Webhook signatures are computed locally with the real Stripe signing scheme, so
the real ``stripe.Webhook.construct_event`` check runs.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any

import stripe

from api.services import region_monthly as rm
from tests.operator_history_orders_support import WEBHOOK_SECRET, StripeStub, signed_event

__all__ = [
    "PRICE_IDS", "WEBHOOK_SECRET", "RegionMonthlyStripeStub", "signed_event", "completed_event", "refund_event",
    "valid_price", "sample_build", "AS_OF",
]

PRICE_IDS = {
    "single": "price_rm_single_test",
    "six": "price_rm_six_test",
    "twelve": "price_rm_twelve_test",
}
PAYMENT_INTENT_PREFIX = "pi_rm_test_"
AS_OF = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def valid_price(kind: str, **overrides: Any) -> dict[str, Any]:
    price = {
        "id": PRICE_IDS[kind], "active": True, "livemode": False, "currency": "gbp",
        "unit_amount": rm.PURCHASE_KINDS[kind].price_pence, "type": "one_time", "recurring": None,
        "lookup_key": f"region_monthly_{kind}_gbp_oneoff_v1",
        "product": {"id": f"prod_rm_{kind}_test", "active": True},
    }
    price.update(overrides)
    return price


class RegionMonthlyStripeStub(StripeStub):
    def __init__(self) -> None:
        super().__init__()
        self.prices = {PRICE_IDS[kind]: valid_price(kind) for kind in PRICE_IDS}
        self.fail_expire = False

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(("session.create", kwargs))
        key = kwargs["idempotency_key"]
        params = {k: v for k, v in kwargs.items() if k != "idempotency_key"}
        if key in self.by_key:
            first_params, session = self.by_key[key]
            if first_params != params:
                raise stripe.StripeError("Keys for idempotent requests can only be used with the same parameters.")
            return session
        self._counter += 1
        session_id = f"cs_test_rm_{self._counter}"
        session = SimpleNamespace(id=session_id, url=f"https://checkout.stripe.test/c/pay/{session_id}")
        self.by_key[key] = (params, session)
        self.sessions[session_id] = params
        return session

    def expire(self, session_id: str, **kwargs: Any) -> None:
        self.calls.append(("session.expire", {"id": session_id}))
        if self.fail_expire:
            raise stripe.StripeError("This Checkout Session cannot be expired.")
        self.expired.append(session_id)

    def price_retrieve(self, price_id: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("price.retrieve", {"id": price_id}))
        return dict(self.prices[price_id])

    def set_price(self, kind: str, **overrides: Any) -> None:
        self.prices[PRICE_IDS[kind]] = valid_price(kind, **overrides)

    def payment_intent_for(self, session_id: str) -> str:
        return PAYMENT_INTENT_PREFIX + session_id

    def session_object(self, session_id: str) -> dict[str, Any]:
        params = self.sessions[session_id]
        paid = int(params["metadata"]["price_pence"]) if self.amount_total is None else self.amount_total
        return {
            "id": session_id,
            "object": "checkout.session",
            "metadata": dict(params["metadata"]),
            "payment_status": self.payment_status,
            "amount_total": paid,
            "currency": self.currency,
            "payment_intent": self.payment_intent_for(session_id),
            "line_items": {"data": [{"price": {"id": item["price"]}, "quantity": item["quantity"]}
                                    for item in params["line_items"]]},
            "customer_details": {"email": params["customer_email"]},
        }


def completed_event(stub: StripeStub, session_id: str, *, event_id: str, event_type: str = "checkout.session.completed") -> dict[str, Any]:
    return {
        "id": event_id, "object": "event", "type": event_type, "api_version": "2024-06-20",
        "data": {"object": stub.session_object(session_id)},
    }


def refund_event(payment_intent: str, *, event_id: str, amount: int, full: bool = True, charge_id: str = "ch_rm_test") -> dict[str, Any]:
    return {
        "id": event_id, "object": "event", "type": "charge.refunded", "api_version": "2024-06-20",
        "data": {"object": {
            "object": "charge", "id": charge_id, "amount": amount,
            "amount_refunded": amount if full else amount // 3, "refunded": full, "payment_intent": payment_intent,
        }},
    }


def sample_build(period_month: date = date(2026, 9, 1), *, region: str = "London", service_slug: str | None = None,
                 build_version: int = 1, **overrides: Any) -> dict[str, Any]:
    """A build row with the stage 1 shape, made without a database."""
    coverage = rm.metric_coverage(period_month)
    metrics: dict[str, Any] = {
        "new_registrations": 6, "ratings_published": None, "closures_observed": None, "reinstatements_observed": None,
    }
    if coverage["ratings_published"]["status"] != rm.NOT_AVAILABLE_AFTER:
        metrics["ratings_published"] = {
            "outstanding": 1, "good": 2, "requires_improvement": 1, "inadequate": 1,
            "no_published_rating_value": 2, "total": 7,
        }
    if coverage["closures_observed"]["status"] != rm.NOT_CAPTURED_BEFORE:
        metrics["closures_observed"] = 2
        metrics["reinstatements_observed"] = 1
    build: dict[str, Any] = {
        "period_month": period_month, "region": region, "service_slug": service_slug,
        "build_version": build_version, "schema_version": rm.SCHEMA_VERSION,
        "built_at": datetime(2026, 11, 7, 6, 30, 5, 123456, tzinfo=timezone.utc),
        "built_from_data_cutoff": AS_OF,
        "metrics": metrics, "coverage": coverage, "limits": list(rm.LIMITS),
    }
    build.update(overrides)
    build["content_sha256"] = rm.content_sha256(rm.canonical_content(
        build["period_month"], build["region"], build["service_slug"], build["metrics"], build["coverage"],
        build["limits"], build["schema_version"],
    ))
    return build
