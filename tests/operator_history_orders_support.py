"""Shared test doubles for the Operator History paid path. No network, no real Stripe.

``StripeStub`` replaces the four Stripe calls the product makes
(``checkout.Session.create`` / ``retrieve`` / ``expire`` and ``Price.retrieve``) the
way the other billing tests do: by replacing the attributes on the ``stripe`` module.
It records every call, so a test can assert that a refusal made zero gateway calls.
Webhook signatures are computed locally with the real Stripe signing scheme, so the
real ``stripe.Webhook.construct_event`` check runs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from typing import Any

import stripe

PRICE_ID = "price_operator_history_test"
WEBHOOK_SECRET = "whsec_operator_history_test"
PAYMENT_INTENT_PREFIX = "pi_oh_test_"


def valid_price(**overrides: Any) -> dict[str, Any]:
    price = {
        "id": PRICE_ID, "active": True, "livemode": False, "currency": "gbp", "unit_amount": 9500,
        "type": "one_time", "recurring": None, "lookup_key": "operator_history_gbp_oneoff_v1",
        "product": {"id": "prod_oh_test", "active": True},
    }
    price.update(overrides)
    return price


class StripeStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.by_key: dict[str, tuple[dict[str, Any], SimpleNamespace]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.expired: list[str] = []
        self.price = valid_price()
        self.charges: dict[str, dict[str, Any]] = {}
        self.amount_total: int | None = None  # tamper knob for the authoritative session
        self.currency = "gbp"
        self.payment_status = "paid"
        self._counter = 0

    # -- the calls --------------------------------------------------------
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
        session_id = f"cs_test_oh_{self._counter}"
        session = SimpleNamespace(id=session_id, url=f"https://checkout.stripe.test/c/pay/{session_id}")
        self.by_key[key] = (params, session)
        self.sessions[session_id] = params
        return session

    def retrieve(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("session.retrieve", {"id": session_id, **kwargs}))
        return self.session_object(session_id)

    def expire(self, session_id: str, **kwargs: Any) -> None:
        self.calls.append(("session.expire", {"id": session_id}))
        self.expired.append(session_id)

    def price_retrieve(self, price_id: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("price.retrieve", {"id": price_id}))
        return dict(self.price)

    def charge_retrieve(self, charge_id: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("charge.retrieve", {"id": charge_id}))
        return self.charges[charge_id]

    # -- helpers ----------------------------------------------------------
    @property
    def gateway_calls(self) -> list[str]:
        return [name for name, _ in self.calls]

    @property
    def creates(self) -> int:
        return self.gateway_calls.count("session.create")

    @property
    def live_sessions(self) -> list[str]:
        return [sid for sid in self.sessions if sid not in self.expired]

    def payment_intent_for(self, session_id: str) -> str:
        return PAYMENT_INTENT_PREFIX + session_id

    def session_object(self, session_id: str) -> dict[str, Any]:
        params = self.sessions[session_id]
        return {
            "id": session_id,
            "object": "checkout.session",
            "metadata": dict(params["metadata"]),
            "payment_status": self.payment_status,
            "amount_total": 9500 if self.amount_total is None else self.amount_total,
            "currency": self.currency,
            "payment_intent": self.payment_intent_for(session_id),
            "line_items": {"data": [{"price": {"id": item["price"]}, "quantity": item["quantity"]}
                                    for item in params["line_items"]]},
            "customer_details": {"email": params["customer_email"]},
        }

    def install(self, monkeypatch) -> "StripeStub":
        monkeypatch.setattr(stripe.checkout.Session, "create", self.create)
        monkeypatch.setattr(stripe.checkout.Session, "retrieve", self.retrieve)
        monkeypatch.setattr(stripe.checkout.Session, "expire", self.expire)
        monkeypatch.setattr(stripe.Price, "retrieve", self.price_retrieve)
        monkeypatch.setattr(stripe.Charge, "retrieve", self.charge_retrieve)
        return self


def signed_event(event: dict[str, Any], *, secret: str = WEBHOOK_SECRET, timestamp: int | None = None) -> tuple[bytes, str]:
    """The raw body and the ``Stripe-Signature`` header, signed the way Stripe signs."""
    payload = json.dumps(event, sort_keys=True).encode("utf-8")
    stamp = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return payload, f"t={stamp},v1={digest}"


def completed_event(stub: StripeStub, session_id: str, *, event_id: str, event_type: str = "checkout.session.completed") -> dict[str, Any]:
    return {
        "id": event_id, "object": "event", "type": event_type, "api_version": "2024-06-20",
        "data": {"object": stub.session_object(session_id)},
    }


def refund_event(payment_intent: str, *, event_id: str, full: bool = True, charge_id: str = "ch_oh_test") -> dict[str, Any]:
    return {
        "id": event_id, "object": "event", "type": "charge.refunded", "api_version": "2024-06-20",
        "data": {"object": {
            "object": "charge", "id": charge_id, "amount": 9500,
            "amount_refunded": 9500 if full else 4000, "refunded": full, "payment_intent": payment_intent,
        }},
    }


def sample_record(**overrides: Any) -> dict[str, Any]:
    """A small record with the stage 1 shape, built without a database."""
    from datetime import date

    from api.services import operator_history as oh

    source = {"label": "CQC registration date", "url": "https://www.cqc.org.uk/location/1-L-A"}
    rating_source = {"label": "CQC inspection report", "url": "https://www.cqc.org.uk/location/1-L-A/reports/1"}
    observation = {"label": "CareGist observation of CQC's active directory", "url": None}
    record: dict[str, Any] = {
        "schema_version": oh.RECORD_SCHEMA_VERSION,
        "provider_id": "1-1000001",
        "provider": {
            "legal_name": "Alpha Care Ltd",
            "edition": {
                "retrieved_on": "2026-09-01", "source_as_of": "2026-08-31",
                "providers_sha256": "1" * 64, "locations_sha256": "2" * 64,
            },
            "earlier_names": [{
                "name": "Alpha Homes Ltd", "first_edition_retrieved_on": "2026-06-01",
                "last_edition_retrieved_on": "2026-07-01",
            }],
        },
        "history_cutoff": "2026-09-03",
        "summary": {
            "locations_total": 2, "on_active_directory": 1, "no_longer_on_active_directory": 1,
            "status_not_held": 0, "earliest_registration_date": "2015-06-01",
            "latest_registration_date": "2018-02-20", "rating_records": 2,
            "earliest_inspection_date": "2019-05-01", "latest_inspection_date": "2019-05-01",
            "closures_observed": 1, "reinstatements_observed": 0, "first_closure_observed_on": "2026-08-12",
        },
        "locations": [
            {
                "location_id": "1-L-A", "name": "=HYPERLINK(\"http://x\")", "registration_date": "2015-06-01",
                "registration_source": source, "service_types": ["Homecare", "Residential social care"],
                "status": {"state": "on_active_directory", "label": oh.STATUS_LABELS["on_active_directory"],
                           "recorded_status": "ACTIVE", "first_observed_absent_on": None,
                           "latest_reinstatement_observed_on": None, "observations": []},
                "rating_history": [
                    {"inspection_date": "2019-05-01", "rating": "Good", "is_published_rating": True,
                     "recorded_on": "2026-03-31", "source": rating_source},
                    {"inspection_date": "2022-01-01", "rating": "Not Yet Inspected", "is_published_rating": False,
                     "recorded_on": "2026-04-03", "source": rating_source},
                ],
            },
            {
                "location_id": "1-L-B", "name": "Alpha Court", "registration_date": "2018-02-20",
                "registration_source": {**source, "url": "https://www.cqc.org.uk/location/1-L-B"},
                "service_types": [],
                "status": {"state": "no_longer_on_active_directory",
                           "label": oh.STATUS_LABELS["no_longer_on_active_directory"],
                           "recorded_status": "INACTIVE", "first_observed_absent_on": "2026-08-12",
                           "latest_reinstatement_observed_on": None,
                           "observations": [{"kind": "closure_observed", "observed_on": "2026-08-12", "source": observation}]},
                "rating_history": [],
            },
        ],
        "events": [
            {"date": "2015-06-01", "kind": "registration", "location_id": "1-L-A", "location_name": "Alpha House",
             "text": oh.EVENT_TEXT["registration"], "source": source},
            {"date": "2018-02-20", "kind": "registration", "location_id": "1-L-B", "location_name": "Alpha Court",
             "text": oh.EVENT_TEXT["registration"], "source": {**source, "url": "https://www.cqc.org.uk/location/1-L-B"}},
            {"date": "2019-05-01", "kind": "rating_published", "location_id": "1-L-A", "location_name": "Alpha House",
             "rating": "Good", "text": oh.EVENT_TEXT["rating_published"].format(rating="Good"), "source": rating_source},
            {"date": "2026-08-12", "kind": "closure_observed", "location_id": "1-L-B", "location_name": "Alpha Court",
             "text": oh.EVENT_TEXT["closure_observed"], "source": observation},
        ],
        "limits": oh.build_limits(
            first_rating_recorded_on=date(2026, 3, 31), earliest_edition_on=date(2026, 6, 1),
            first_status_observed_on=date(2026, 8, 10), history_cutoff=date(2026, 9, 3),
        ),
    }
    record.update(overrides)
    record["content_sha256"] = oh.content_sha256(record)
    return record
