"""Release-gate tests for one-time full-dataset checkout and fulfilment."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from api.routers import billing


TERMS_SHA = "b" * 64
MIGRATION_048 = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "048_full_dataset_fulfilment.sql"
).read_text(encoding="utf-8")


class _Conn:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.executions: list[tuple] = []

    async def fetchrow(self, *_args):
        return next(self.rows)

    async def execute(self, *args):
        self.executions.append(args)
        return "UPDATE 1"


def test_legacy_fulfilment_migration_is_safe_after_schema_drift():
    """A manually provisioned legacy schema must not block later migrations."""
    assert MIGRATION_048.count("CREATE TABLE IF NOT EXISTS") == 4
    assert MIGRATION_048.count("CREATE INDEX IF NOT EXISTS") == 2
    assert MIGRATION_048.count("CREATE UNIQUE INDEX IF NOT EXISTS") == 1
    assert "DROP TRIGGER IF EXISTS digital_content_consents_immutable" in MIGRATION_048


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
async def test_dataset_checkout_is_retired_before_database_or_stripe(monkeypatch, dataset_settings):
    create = Mock()
    connection = Mock()
    monkeypatch.setattr(billing, "get_connection", connection)
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    with pytest.raises(HTTPException, match="no longer sold") as error:
        await billing.create_dataset_checkout(billing.DatasetCheckoutRequest(email="Buyer@Example.com"))

    assert error.value.status_code == 410
    connection.assert_not_called()
    create.assert_not_called()


@pytest.mark.asyncio
async def test_dataset_checkout_cannot_be_reenabled_by_legacy_flags(monkeypatch, dataset_settings):
    create = Mock()
    monkeypatch.setattr(billing, "get_connection", Mock())
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)

    with pytest.raises(HTTPException) as error:
        await billing.create_dataset_checkout(billing.DatasetCheckoutRequest(email="Buyer@Example.com"))

    assert error.value.status_code == 410
    create.assert_not_called()


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
