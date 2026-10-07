"""Real DB reconciliation; provider responses are explicitly synthetic."""
from types import SimpleNamespace

import asyncpg
import pytest
import stripe

from api.routers.billing import _persist_subscription_state
from tests.integration.conftest import apply_full_schema
from tests.integration.test_subscription_state import _make_owner_workspace, _make_user_with_keys
from tools import reconcile_stripe_subscriptions as reconciliation

pytestmark = pytest.mark.asyncio


async def test_reconciliation_revokes_all_entitlement_stores_after_confirmation(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user = await _make_user_with_keys(conn, 'reconcile@test.invalid', 2, tier='free')
        organization = await _make_owner_workspace(conn, user)
        await _persist_subscription_state(conn, user, 'sub_confirmed', 'business', 'active')
        monkeypatch.setattr(stripe.Subscription, 'list', lambda **kw: SimpleNamespace(
            data=[{'id':'sub_confirmed', 'status':'past_due'}], has_more=False))
        monkeypatch.setattr(stripe.Subscription, 'retrieve', lambda sid: {'id':sid, 'status':'past_due'})
        result = await reconciliation.reconcile(fresh_db, fix=True)
        assert result['fixed'] == 1
        assert await conn.fetchval('SELECT status FROM subscriptions WHERE stripe_subscription_id=$1', 'sub_confirmed') == 'past_due'
        workspace = await conn.fetchrow('SELECT plan_tier,status,included_users FROM organization_subscriptions WHERE organization_id=$1', organization)
        assert tuple(workspace.values()) == ('free', 'past_due', 1)
        assert await conn.fetchval('SELECT count(*) FROM api_keys WHERE user_id=$1 AND is_active', user) == 1
        assert await conn.fetchval('SELECT tier FROM api_keys WHERE user_id=$1 AND is_active', user) == 'free'
    finally:
        await conn.close()


async def test_unconfirmed_orphan_does_not_revoke_paid_customer(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user = await _make_user_with_keys(conn, 'orphan@test.invalid', 1, tier='free')
        await _persist_subscription_state(conn, user, 'sub_missing', 'business', 'active')
        monkeypatch.setattr(stripe.Subscription, 'list', lambda **kw: SimpleNamespace(data=[], has_more=False))
        def missing(sid):
            raise stripe.InvalidRequestError('synthetic missing object', 'id', code='resource_missing')
        monkeypatch.setattr(stripe.Subscription, 'retrieve', missing)
        result = await reconciliation.reconcile(fresh_db, fix=True)
        assert result['fixed'] == 0 and result['status_mismatch'] == 1
        assert await conn.fetchval('SELECT status FROM subscriptions WHERE stripe_subscription_id=$1', 'sub_missing') == 'active'
        assert await conn.fetchval('SELECT tier FROM api_keys WHERE user_id=$1 AND is_active', user) == 'business'
    finally:
        await conn.close()


async def test_reconciliation_rechecks_status_and_does_not_apply_stale_revocation(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user = await _make_user_with_keys(conn, 'race@test.invalid', 1, tier='free')
        await _persist_subscription_state(conn, user, 'sub_race', 'business', 'active')
        monkeypatch.setattr(stripe.Subscription, 'list', lambda **kw: SimpleNamespace(data=[{'id':'sub_race', 'status':'canceled'}], has_more=False))
        monkeypatch.setattr(stripe.Subscription, 'retrieve', lambda sid: {'id':sid, 'status':'active'})
        result = await reconciliation.reconcile(fresh_db, fix=True)
        assert result['fixed'] == 0
        assert await conn.fetchval('SELECT status FROM subscriptions WHERE stripe_subscription_id=$1', 'sub_race') == 'active'
    finally:
        await conn.close()
