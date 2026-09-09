"""Release-gate tests for the Territory Opportunity Brief checkout route and the
webhook routing branch that delivers it.

Fulfilment itself (idempotency, retry, tamper rejection) is covered by
``tests/test_territory_brief_fulfilment.py``; pack generation by
``tests/test_territory_brief*.py``. This file covers the wiring added in
``api/routers/billing.py`` + ``api/services/territory_brief_delivery.py``:
fail-closed behaviour, pre-payment scope validation, and that a completed
``territory_opportunity_brief`` checkout is routed to the fulfilment handler.
"""

from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from api.routers import billing
from api.services import territory_brief_delivery
from api.services.territory_brief_fulfilment import TERRITORY_BRIEF_CONSENT_TEXT

CONSENT_SHA = hashlib.sha256(TERRITORY_BRIEF_CONSENT_TEXT.encode("utf-8")).hexdigest()
TERMS_SHA = "a" * 64

CATALOGUE = {
    "local_authority": {"southampton": "Southampton"},
    "region": {"south east": "South East"},
}


def _request(**overrides):
    payload = {
        "email": "Buyer@Example.com",
        "scope_kind": "local_authority",
        "scope_name": "southampton",
        "window_days": 90,
        "shortlist_target": 30,
    }
    payload.update(overrides)
    return billing.TerritoryBriefCheckoutRequest(**payload)


class _Conn:
    def __init__(self, order_id="11111111-1111-1111-1111-111111111111"):
        self.order_id = order_id
        self.executions: list[tuple] = []

    async def fetchrow(self, *_args):
        return {"id": self.order_id}

    async def execute(self, *args):
        self.executions.append(args)
        return "UPDATE 1"


@pytest.fixture
def brief_settings(monkeypatch):
    monkeypatch.setattr(billing.settings, "territory_self_serve_checkout_enabled", True)
    monkeypatch.setattr(billing.settings, "stripe_secret_key", "sk_test_brief")
    monkeypatch.setattr(billing.settings, "stripe_price_territory_brief", "price_territory_brief")
    monkeypatch.setattr(billing.settings, "blob_read_write_token", "vercel_blob_rw_test")
    monkeypatch.setattr(billing.settings, "resend_api_key", "re_test")
    monkeypatch.setattr(billing.settings, "territory_brief_terms_version", "tb-2026-09-09")
    monkeypatch.setattr(billing.settings, "territory_brief_terms_sha256", TERMS_SHA)
    monkeypatch.setattr(billing.settings, "territory_brief_consent_sha256", CONSENT_SHA)
    monkeypatch.setattr(billing.settings, "app_url", "https://caregist.co.uk")
    monkeypatch.setattr(territory_brief_delivery, "scope_catalogue", lambda: CATALOGUE)


@pytest.mark.asyncio
async def test_checkout_disabled_returns_503_before_touching_stripe_or_db(monkeypatch):
    monkeypatch.setattr(billing.settings, "territory_self_serve_checkout_enabled", False)
    create = Mock()
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)
    monkeypatch.setattr(billing, "get_connection", Mock())

    with pytest.raises(HTTPException) as err:
        await billing.create_territory_brief_checkout(_request())

    assert err.value.status_code == 503
    create.assert_not_called()
    billing.get_connection.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_unconfigured_returns_503(monkeypatch, brief_settings):
    monkeypatch.setattr(billing.settings, "blob_read_write_token", "")
    create = Mock()
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    with pytest.raises(HTTPException) as err:
        await billing.create_territory_brief_checkout(_request())

    assert err.value.status_code == 503
    create.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_awaiting_approved_consent_wording_returns_503(monkeypatch, brief_settings):
    # Approved hash set to something the shipped placeholder text cannot match.
    monkeypatch.setattr(billing.settings, "territory_brief_consent_sha256", "b" * 64)
    create = Mock()
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    with pytest.raises(HTTPException) as err:
        await billing.create_territory_brief_checkout(_request())

    assert err.value.status_code == 503
    create.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_rejects_unknown_territory_without_taking_payment(monkeypatch, brief_settings):
    create = Mock()
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)
    monkeypatch.setattr(billing, "get_connection", Mock())

    with pytest.raises(HTTPException) as err:
        await billing.create_territory_brief_checkout(_request(scope_name="Atlantis"))

    assert err.value.status_code == 422
    create.assert_not_called()
    billing.get_connection.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_reserves_order_and_returns_hosted_url(monkeypatch, brief_settings):
    conn = _Conn()

    @asynccontextmanager
    async def fake_get_connection():
        yield conn

    monkeypatch.setattr(billing, "get_connection", fake_get_connection)
    session = Mock(url="https://checkout.stripe.com/c/pay/cs_test_brief", id="cs_test_brief")
    create = Mock(return_value=session)
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    result = await billing.create_territory_brief_checkout(_request(scope_name="SOUTHAMPTON"))

    assert result["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_brief"
    assert result["scope"] == {"kind": "local_authority", "name": "Southampton", "window_days": 90}
    assert result["price_gbp"] == 795

    kwargs = create.call_args.kwargs
    assert kwargs["mode"] == "payment"
    assert kwargs["line_items"] == [{"price": "price_territory_brief", "quantity": 1}]
    assert kwargs["consent_collection"] == {"terms_of_service": "required"}
    assert kwargs["metadata"]["type"] == "territory_opportunity_brief"
    assert kwargs["metadata"]["scope_name"] == "Southampton"  # canonicalised, not the raw input
    assert kwargs["metadata"]["terms_version"] == "tb-2026-09-09"
    assert kwargs["idempotency_key"] == f"caregist-territory-brief-{conn.order_id}"

    # order row updated with the checkout session id
    assert any("stripe_checkout_session_id" in call[0] for call in conn.executions)


@pytest.mark.asyncio
async def test_checkout_marks_order_expired_when_stripe_creation_fails(monkeypatch, brief_settings):
    conn = _Conn()

    @asynccontextmanager
    async def fake_get_connection():
        yield conn

    monkeypatch.setattr(billing, "get_connection", fake_get_connection)
    monkeypatch.setattr(
        billing.stripe.checkout.Session,
        "create",
        Mock(side_effect=RuntimeError("stripe down")),
    )

    with pytest.raises(RuntimeError, match="stripe down"):
        await billing.create_territory_brief_checkout(_request())

    assert any(
        "SET status = 'expired'" in call[0] and "territory_brief_orders" in call[0]
        for call in conn.executions
    )


def test_checkout_request_rejects_client_supplied_price_fields():
    with pytest.raises(ValueError):
        billing.TerritoryBriefCheckoutRequest(
            email="b@example.com",
            scope_kind="local_authority",
            scope_name="Southampton",
            price_id="price_attacker",  # extra="forbid"
        )


@pytest.mark.asyncio
async def test_webhook_routes_territory_brief_type_to_fulfilment(monkeypatch):
    fulfil = AsyncMock()
    monkeypatch.setattr(billing.territory_brief_fulfilment, "fulfil_territory_brief_order", fulfil)
    monkeypatch.setattr(billing.territory_brief_delivery, "fulfilment_settings", lambda: "CFG")
    monkeypatch.setattr(billing.territory_brief_delivery, "fulfilment_deps", lambda: "DEPS")

    session = {"id": "cs_brief", "metadata": {"type": "territory_opportunity_brief", "order_id": "o1"}}
    await billing._handle_checkout_completed(Mock(), session)

    fulfil.assert_awaited_once()
    assert fulfil.await_args.kwargs == {"cfg": "CFG", "deps": "DEPS"}


@pytest.mark.asyncio
async def test_webhook_territory_brief_branch_does_not_require_user_id(monkeypatch):
    """A brief checkout has no logged-in user; the B2B user_id gate must not fire."""
    monkeypatch.setattr(
        billing.territory_brief_fulfilment, "fulfil_territory_brief_order", AsyncMock()
    )
    monkeypatch.setattr(billing.territory_brief_delivery, "fulfilment_settings", lambda: None)
    monkeypatch.setattr(billing.territory_brief_delivery, "fulfilment_deps", lambda: None)

    session = {"id": "cs_brief", "metadata": {"type": "territory_opportunity_brief", "order_id": "o1"}}
    await billing._handle_checkout_completed(Mock(), session)  # must not raise "missing user_id"


FIXTURE = Path(__file__).parent / "fixtures" / "territory_brief" / "locations_detail.jsonl"


@pytest.mark.skipif(not FIXTURE.exists(), reason="territory_brief fixture not present")
def test_generate_pack_maps_brief_to_generated_pack(monkeypatch):
    fixture_dir = FIXTURE.parent
    monkeypatch.setattr(territory_brief_delivery, "_LOCATIONS_SNAPSHOT", fixture_dir / "locations_detail.jsonl")
    monkeypatch.setattr(territory_brief_delivery, "_PROVIDERS_SNAPSHOT", fixture_dir / "providers_detail.jsonl")
    monkeypatch.setattr(territory_brief_delivery.settings, "territory_brief_terms_version", "itest")

    pack = territory_brief_delivery.generate_pack(
        {
            "id": "itest-pack-0001",
            "scope_kind": "local_authority",
            "scope_name": "Southampton",
            "scope_window_days": 365,
            "scope_shortlist_target": 30,
        }
    )

    assert pack.pdf_bytes[:4] == b"%PDF"
    assert pack.scope_name == "Southampton"
    assert pack.shortlisted > 0
    assert pack.considered >= pack.shortlisted
    assert "rank,organisation" in pack.csv_text.splitlines()[0]
