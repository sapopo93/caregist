"""Acceptance tests (CG-AT) for the Territory Opportunity Brief checkout gate.

The gate must stay fail-closed: a buyer is never sent to Stripe, and no order
row is written, unless every approval and configuration value is present. These
tests cover the paths that the existing checkout tests leave open (the second
master flag, the start-up validator, and the webhook when terms are not approved).

No database, Stripe, network or CQC snapshot is used.
"""

from __future__ import annotations

import hashlib
import sys
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from api.config import Settings
from api.routers import billing
from api.services import territory_brief_delivery, territory_brief_fulfilment
from api.services.territory_brief_fulfilment import TERRITORY_BRIEF_CONSENT_TEXT

CONSENT_SHA = hashlib.sha256(TERRITORY_BRIEF_CONSENT_TEXT.encode("utf-8")).hexdigest()
TERMS_SHA = "a" * 64


def _base_settings(**over) -> Settings:
    values = dict(
        database_url="postgresql://prod",
        api_master_key="master",
        support_internal_token="support",
        webhook_secret_key="webhook-key",
        redis_url="rediss://redis.example.com:6380/0",
        cors_origins="https://caregist.co.uk",
        app_url="https://caregist.co.uk",
    )
    values.update(over)
    return Settings(**values)


@pytest.fixture
def validator_active(monkeypatch):
    """Settings.validate_production returns early when pytest is imported.

    Hide that sentinel so the real start-up validator runs against the settings
    under test. monkeypatch restores sys.modules afterwards.
    """
    monkeypatch.delitem(sys.modules, "pytest")


def _request():
    return billing.TerritoryBriefCheckoutRequest(
        email="buyer@example.com",
        scope_kind="local_authority",
        scope_name="southampton",
        window_days=90,
        shortlist_target=30,
    )


# CG-AT-002 negative: the second master flag also closes the gate.
@pytest.mark.asyncio
async def test_checkout_stays_closed_when_global_billing_flag_is_off(monkeypatch):
    monkeypatch.setattr(billing.settings, "territory_self_serve_checkout_enabled", True)
    monkeypatch.setattr(billing.settings, "billing_checkout_enabled", False)
    create = Mock()
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)
    get_connection = Mock()
    monkeypatch.setattr(billing, "get_connection", get_connection)

    with pytest.raises(HTTPException) as err:
        await billing.create_territory_brief_checkout(_request())

    assert err.value.status_code == 503
    create.assert_not_called()
    get_connection.assert_not_called()


# CG-AT-002 negative: both flags on but the Stripe/Blob/Resend config is missing.
@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["stripe_secret_key", "stripe_price_territory_brief", "blob_read_write_token", "resend_api_key"])
async def test_checkout_stays_closed_when_any_required_secret_is_missing(monkeypatch, missing):
    monkeypatch.setattr(billing.settings, "territory_self_serve_checkout_enabled", True)
    monkeypatch.setattr(billing.settings, "billing_checkout_enabled", True)
    for name in ("stripe_secret_key", "stripe_price_territory_brief", "blob_read_write_token", "resend_api_key"):
        monkeypatch.setattr(billing.settings, name, "" if name == missing else "sk_test_value")
    create = Mock()
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)
    monkeypatch.setattr(billing, "get_connection", Mock())

    with pytest.raises(HTTPException) as err:
        await billing.create_territory_brief_checkout(_request())

    assert err.value.status_code == 503
    create.assert_not_called()


# CG-AT-002 negative: the app refuses to start with the brief gate open and no billing master flag.
def test_startup_refuses_territory_gate_without_billing_master_flag(validator_active):
    cfg = _base_settings(territory_self_serve_checkout_enabled=True, billing_checkout_enabled=False)
    with pytest.raises(RuntimeError, match="requires BILLING_CHECKOUT_ENABLED"):
        cfg.validate_production()


# CG-AT-002 negative: the app refuses to start with the gate open and approval hashes absent.
def test_startup_refuses_territory_gate_without_approved_terms_and_consent_hashes(validator_active):
    cfg = _base_settings(territory_self_serve_checkout_enabled=True, billing_checkout_enabled=True)
    with pytest.raises(RuntimeError, match="TERRITORY_BRIEF_CONSENT_SHA256"):
        cfg.validate_production()


# CG-AT-002 negative: a malformed approval hash is refused at start-up.
def test_startup_refuses_territory_gate_with_malformed_consent_hash(validator_active):
    cfg = _base_settings(
        territory_self_serve_checkout_enabled=True,
        billing_checkout_enabled=True,
        stripe_price_territory_brief="price_x",
        territory_brief_terms_version="v1",
        territory_brief_terms_sha256=TERMS_SHA,
        territory_brief_consent_sha256="not-a-hash",
        blob_read_write_token="tok",
        resend_api_key="re_x",
    )
    with pytest.raises(RuntimeError, match="64-character SHA-256"):
        cfg.validate_production()


# CG-AT-002 default: nothing is open unless somebody sets it.
def test_territory_and_billing_gates_default_to_closed():
    cfg = _base_settings()
    cfg.validate_production()
    assert cfg.territory_self_serve_checkout_enabled is False
    assert cfg.billing_checkout_enabled is False


# CG-AT-004 negative: a paid webhook must not generate a brief while the approved consent wording is absent.
@pytest.mark.asyncio
async def test_webhook_does_not_generate_when_terms_and_consent_are_not_approved(monkeypatch):
    monkeypatch.setattr(billing.settings, "territory_brief_terms_version", "")
    monkeypatch.setattr(billing.settings, "territory_brief_terms_sha256", "")
    monkeypatch.setattr(billing.settings, "territory_brief_consent_sha256", "")
    fulfil = AsyncMock()
    monkeypatch.setattr(billing.territory_brief_fulfilment, "fulfil_territory_brief_order", fulfil)

    session = {"id": "cs_x", "metadata": {"type": territory_brief_fulfilment.METADATA_TYPE}}
    with pytest.raises(HTTPException) as err:
        await billing._handle_checkout_completed(AsyncMock(), session)

    assert err.value.status_code == 503
    fulfil.assert_not_called()


# CG-AT-004 negative: a consent hash that does not match the shipped wording is refused.
def test_consent_hash_that_does_not_match_shipped_wording_is_refused(monkeypatch):
    monkeypatch.setattr(territory_brief_delivery.settings, "territory_brief_terms_version", "v1")
    monkeypatch.setattr(territory_brief_delivery.settings, "territory_brief_terms_sha256", TERMS_SHA)
    monkeypatch.setattr(territory_brief_delivery.settings, "territory_brief_consent_sha256", "c" * 64)
    with pytest.raises(HTTPException) as err:
        territory_brief_delivery.terms_evidence()
    assert err.value.status_code == 503


# CG-AT-004 happy: the approved hash is accepted and returned with the terms version.
def test_matching_consent_hash_is_accepted(monkeypatch):
    monkeypatch.setattr(territory_brief_delivery.settings, "territory_brief_terms_version", "v1")
    monkeypatch.setattr(territory_brief_delivery.settings, "territory_brief_terms_sha256", TERMS_SHA)
    monkeypatch.setattr(territory_brief_delivery.settings, "territory_brief_consent_sha256", CONSENT_SHA)
    assert territory_brief_delivery.terms_evidence() == ("v1", TERMS_SHA, CONSENT_SHA)
