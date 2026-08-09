"""Release-gate tests for one-time full-dataset checkout and fulfilment."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from api.routers import billing


TERMS_SHA = "b" * 64


class _Conn:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.executions: list[tuple] = []

    async def fetchrow(self, *_args):
        return next(self.rows)

    async def execute(self, *args):
        self.executions.append(args)
        return "UPDATE 1"


@pytest.fixture
def dataset_settings(monkeypatch):
    monkeypatch.setattr(billing.settings, "full_dataset_checkout_enabled", True)
    monkeypatch.setattr(billing.settings, "stripe_secret_key", "sk_test_dataset")
    monkeypatch.setattr(billing.settings, "stripe_price_full_dataset", "price_full_dataset")
    monkeypatch.setattr(billing.settings, "resend_api_key", "re_test")
    monkeypatch.setattr(billing.settings, "digital_content_terms_version", "digital-2026-08-08")
    monkeypatch.setattr(billing.settings, "digital_content_terms_sha256", TERMS_SHA)
    monkeypatch.setattr(billing.settings, "app_url", "https://caregist.co.uk")


@pytest.mark.asyncio
async def test_dataset_checkout_fails_before_stripe_when_no_active_artifact(monkeypatch, dataset_settings):
    conn = _Conn([None])

    @asynccontextmanager
    async def connection():
        yield conn

    create = Mock()
    monkeypatch.setattr(billing, "get_connection", connection)
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    with pytest.raises(HTTPException, match="No payment has been taken") as error:
        await billing.create_dataset_checkout(billing.DatasetCheckoutRequest(email="Buyer@Example.com"))

    assert error.value.status_code == 503
    create.assert_not_called()


@pytest.mark.asyncio
async def test_dataset_checkout_requires_stripe_waiver_and_binds_artifact(monkeypatch, dataset_settings):
    artifact = {
        "id": "11111111-1111-1111-1111-111111111111",
        "record_count": 56746,
        "sha256": "c" * 64,
        "source_watermark": SimpleNamespace(isoformat=lambda: "2026-08-09T08:00:00+00:00"),
    }
    first = _Conn([artifact, {"id": "22222222-2222-2222-2222-222222222222"}])
    second = _Conn([])
    connections = iter([first, second])

    @asynccontextmanager
    async def connection():
        yield next(connections)

    session = SimpleNamespace(id="cs_dataset", url="https://checkout.stripe.test/dataset")
    create = Mock(return_value=session)
    monkeypatch.setattr(billing, "get_connection", connection)
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    result = await billing.create_dataset_checkout(billing.DatasetCheckoutRequest(email="Buyer@Example.com"))

    assert result["record_count"] == 56746
    kwargs = create.call_args.kwargs
    assert kwargs["mode"] == "payment"
    assert kwargs["line_items"] == [{"price": "price_full_dataset", "quantity": 1}]
    assert kwargs["consent_collection"] == {"terms_of_service": "required"}
    assert "expressly request immediate supply" in kwargs["custom_text"]["terms_of_service_acceptance"]["message"]
    assert "lose my statutory right to cancel" in kwargs["custom_text"]["terms_of_service_acceptance"]["message"]
    assert kwargs["metadata"]["artifact_id"] == artifact["id"]
    assert "payment_method_types" not in kwargs


@pytest.mark.asyncio
async def test_paid_dataset_fulfilment_records_consent_token_and_email(monkeypatch, dataset_settings):
    order = {
        "id": "22222222-2222-2222-2222-222222222222",
        "artifact_id": "11111111-1111-1111-1111-111111111111",
        "customer_email": "buyer@example.com",
        "stripe_price_id": "price_full_dataset",
        "status": "pending",
    }
    conn = _Conn([order])
    metadata = {
        "type": "full_dataset",
        "order_id": order["id"],
        "artifact_id": order["artifact_id"],
        "price_id": "price_full_dataset",
        "terms_version": "digital-2026-08-08",
        "terms_sha256": TERMS_SHA,
        "consent_text_sha256": billing.hashlib.sha256(
            billing.FULL_DATASET_CONSENT_TEXT.encode("utf-8")
        ).hexdigest(),
    }
    authoritative = {
        "id": "cs_dataset",
        "metadata": metadata,
        "payment_status": "paid",
        "consent": {"terms_of_service": "accepted"},
        "line_items": {"data": [{"price": {"id": "price_full_dataset"}, "quantity": 1}]},
        "payment_intent": "pi_dataset",
        "amount_total": 19900,
        "currency": "gbp",
    }
    monkeypatch.setattr(billing.stripe.checkout.Session, "retrieve", lambda *_args, **_kwargs: authoritative)
    monkeypatch.setattr(billing, "write_audit_log", AsyncMock())
    monkeypatch.setattr(billing, "_new_dataset_download_token", lambda: ("raw-token", "d" * 64))

    await billing._handle_checkout_completed(conn, {"id": "cs_dataset", "metadata": metadata})

    sql = "\n".join(call[0] for call in conn.executions)
    assert "INSERT INTO digital_content_consents" in sql
    assert "INSERT INTO dataset_download_tokens" in sql
    assert "INSERT INTO pending_emails" in sql
    email_insert = next(call for call in conn.executions if "INSERT INTO pending_emails" in call[0])
    assert "raw-token" in email_insert[2]
    assert "Open Government Licence v3.0" in email_insert[2]


@pytest.mark.asyncio
async def test_dataset_fulfilment_rejects_missing_stripe_consent(monkeypatch, dataset_settings):
    metadata = {"type": "full_dataset", "order_id": "order", "artifact_id": "artifact"}
    monkeypatch.setattr(
        billing.stripe.checkout.Session,
        "retrieve",
        lambda *_args, **_kwargs: {
            "metadata": metadata,
            "payment_status": "paid",
            "consent": {},
        },
    )
    with pytest.raises(RuntimeError, match="no Stripe terms acceptance"):
        await billing._handle_checkout_completed(_Conn([]), {"id": "cs_dataset", "metadata": metadata})
