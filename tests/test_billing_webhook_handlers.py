"""Focused tests for Stripe webhook handler failure semantics."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from api.routers import billing


class _Conn:
    async def fetchrow(self, *args, **kwargs):
        return {"user_id": 123}

    async def execute(self, *args, **kwargs):
        return "UPDATE 1"


def test_profile_tier_normalizes_legacy_premium_to_enhanced():
    assert billing._normalize_profile_tier("premium") == "enhanced"
    assert billing._normalize_profile_tier("provider_pro") == "enhanced"


@pytest.mark.asyncio
async def test_checkout_completed_missing_user_id_raises_for_retry():
    with pytest.raises(RuntimeError, match="missing user_id"):
        await billing._handle_checkout_completed(
            _Conn(),
            {
                "metadata": {"tier": "starter", "price_id": "price_starter"},
                "subscription": "sub_123",
            },
        )


@pytest.mark.asyncio
async def test_checkout_completed_accepts_alerts_pro_metadata(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts_pro", "alerts-pro")
    persist = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(billing, "_persist_subscription_state", persist)
    monkeypatch.setattr(billing, "write_audit_log", audit)

    await billing._handle_checkout_completed(
        _Conn(),
        {
            "metadata": {
                "user_id": "123",
                "tier": "alerts-pro",
                "price_id": "price_alerts_pro",
            },
            "subscription": "sub_alerts",
            "customer": "cus_alerts",
        },
    )

    persist.assert_awaited_once()
    assert persist.await_args.args[1:5] == (123, "sub_alerts", "alerts-pro", "active")
    assert persist.await_args.kwargs["stripe_price_id"] == "price_alerts_pro"
    audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscription_updated_unknown_price_raises_for_retry(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_starter", "starter")

    with pytest.raises(RuntimeError, match="cannot map base price"):
        await billing._handle_subscription_updated(
            _Conn(),
            {
                "id": "sub_123",
                "status": "active",
                "items": {
                    "data": [
                        {"price": {"id": "price_new_plan"}, "quantity": 1},
                    ],
                },
            },
        )


@pytest.mark.asyncio
async def test_subscription_updated_accepts_alerts_pro_price(monkeypatch):
    monkeypatch.setitem(billing.PRICE_TO_TIER, "price_alerts_pro", "alerts-pro")
    persist = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(billing, "_persist_subscription_state", persist)
    monkeypatch.setattr(billing, "write_audit_log", audit)

    await billing._handle_subscription_updated(
        _Conn(),
        {
            "id": "sub_alerts",
            "status": "active",
            "items": {
                "data": [
                    {"price": {"id": "price_alerts_pro"}, "quantity": 1},
                ],
            },
        },
    )

    persist.assert_awaited_once()
    assert persist.await_args.args[1:5] == (123, "sub_alerts", "alerts-pro", "active")
    assert persist.await_args.kwargs["stripe_price_id"] == "price_alerts_pro"
    audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_checkout_missing_metadata_raises_for_retry():
    with pytest.raises(RuntimeError, match="missing slug or tier"):
        await billing._handle_profile_checkout_completed(
            _Conn(),
            {
                "metadata": {"type": "profile", "slug": "provider-slug"},
                "subscription": "sub_123",
            },
        )


@pytest.mark.asyncio
async def test_profile_checkout_completed_normalizes_legacy_premium_tier(monkeypatch):
    audit = AsyncMock()
    monkeypatch.setattr(billing, "write_audit_log", audit)

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 1")
    await billing._handle_profile_checkout_completed(
        conn,
        {
            "metadata": {"type": "profile", "slug": "provider-slug", "tier": "premium"},
            "subscription": "sub_profile",
        },
    )

    execute_args = conn.execute.await_args.args
    assert execute_args[1] == "enhanced"
    assert execute_args[2] == "sub_profile"
    assert execute_args[3] == "provider-slug"
    audit.assert_awaited_once()
