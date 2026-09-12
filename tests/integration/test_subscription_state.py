"""Integration tests for subscription state transitions (F-26, F-17).

Drives the real _persist_subscription_state against a Postgres schema and
asserts the resulting DB state: subscription row, key re-tiering, and seat-count
enforcement on downgrade.
"""

from __future__ import annotations

import json

import pytest

from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio


async def _make_user_with_keys(conn, email: str, n_keys: int, tier: str = "business") -> int:
    user_id = await conn.fetchval(
        "INSERT INTO users (email, password_hash, name) VALUES ($1, 'x', 'U') RETURNING id",
        email,
    )
    for i in range(n_keys):
        await conn.execute(
            """
            INSERT INTO api_keys (key_hash, key_prefix, name, email, tier, rate_limit, is_active, user_id)
            VALUES ($1, $2, $3, $4, $5, 60, true, $6)
            """,
            f"{i:064d}", f"p{i}", f"key{i}", email, tier, user_id,
        )
    return user_id


async def _make_owner_workspace(
    conn,
    user_id: int,
    tier: str = "free",
    *,
    scope_config: dict | None = None,
):
    organization_id = await conn.fetchval(
        """
        INSERT INTO organizations (name, slug, created_by_user_id)
        VALUES ('Test workspace', $2, $1)
        RETURNING id
        """,
        user_id,
        f"test-workspace-{user_id}",
    )
    await conn.execute(
        """
        INSERT INTO organization_members (organization_id, user_id, role)
        VALUES ($1, $2, 'owner')
        """,
        organization_id,
        user_id,
    )
    await conn.execute(
        """
        INSERT INTO organization_subscriptions (
          organization_id, plan_tier, status, included_users, scope_config
        ) VALUES ($1, $2, 'active', 1, $3::jsonb)
        """,
        organization_id,
        tier,
        json.dumps(scope_config or {}),
    )
    return organization_id


async def test_upgrade_retiers_all_active_keys(fresh_db):
    from api.routers.billing import _persist_subscription_state
    from api.services.tenant_context import _organization_row

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "up@test.com", 2, tier="free")
        organization_id = await _make_owner_workspace(conn, user_id)

        await _persist_subscription_state(
            conn, user_id, "sub_up", "business", "active", stripe_price_id="price_b"
        )

        sub = await conn.fetchrow(
            "SELECT tier, status FROM subscriptions WHERE stripe_subscription_id = 'sub_up'"
        )
        assert sub["tier"] == "business"
        assert sub["status"] == "active"

        tiers = await conn.fetch(
            "SELECT tier, is_active FROM api_keys WHERE user_id = $1", user_id
        )
        # business max_users is 10, so both keys stay active and are re-tiered.
        assert all(r["tier"] == "business" and r["is_active"] for r in tiers)
        organization_subscription = await conn.fetchrow(
            """
            SELECT stripe_subscription_id, plan_tier, status, included_users
            FROM organization_subscriptions
            WHERE organization_id = $1
            """,
            organization_id,
        )
        assert dict(organization_subscription) == {
            "stripe_subscription_id": "sub_up",
            "plan_tier": "business",
            "status": "active",
            "included_users": 10,
        }
        context_row = await _organization_row(conn, user_id, "free")
        assert context_row["plan_tier"] == "business"
    finally:
        await conn.close()


async def test_first_paid_subscription_supersedes_registration_free_row(fresh_db):
    from api.routers.billing import _persist_subscription_state

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "registered@test.com", 1, tier="free")
        await conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status) VALUES ($1, 'free', 'active')",
            user_id,
        )

        await _persist_subscription_state(
            conn,
            user_id,
            "sub_radar_regional",
            "radar-regional",
            "active",
            stripe_price_id="price_radar_regional",
        )

        rows = await conn.fetch(
            "SELECT stripe_subscription_id, tier, status FROM subscriptions "
            "WHERE user_id = $1 ORDER BY created_at, id",
            user_id,
        )
        assert [dict(row) for row in rows] == [
            {"stripe_subscription_id": None, "tier": "free", "status": "superseded"},
            {
                "stripe_subscription_id": "sub_radar_regional",
                "tier": "radar-regional",
                "status": "active",
            },
        ]
        assert await conn.fetchval(
            "SELECT tier FROM api_keys WHERE user_id = $1 AND is_active = TRUE",
            user_id,
        ) == "radar-regional"
    finally:
        await conn.close()


async def test_downgrade_deactivates_excess_keys(fresh_db):
    from api.routers.billing import _persist_subscription_state

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "down@test.com", 3, tier="business")

        # Downgrade to free (max_users = 1): keep the oldest key, deactivate rest.
        await _persist_subscription_state(
            conn, user_id, "sub_down", "free", "active", stripe_price_id="price_f"
        )

        active = await conn.fetch(
            "SELECT name, tier FROM api_keys WHERE user_id = $1 AND is_active = true ORDER BY created_at",
            user_id,
        )
        assert len(active) == 1
        assert active[0]["name"] == "key0"   # the original/primary key survives
        assert active[0]["tier"] == "free"   # and is re-tiered

        inactive = await conn.fetchval(
            "SELECT COUNT(*) FROM api_keys WHERE user_id = $1 AND is_active = false", user_id
        )
        assert inactive == 2
    finally:
        await conn.close()


async def test_subscription_deleted_downgrades_to_free(fresh_db):
    from api.routers.billing import _handle_subscription_deleted, _persist_subscription_state
    from api.services.tenant_context import _organization_row

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "del@test.com", 1, tier="business")
        organization_id = await _make_owner_workspace(conn, user_id, tier="business")
        await _persist_subscription_state(
            conn, user_id, "sub_del", "business", "active", stripe_price_id="price_b"
        )

        await _handle_subscription_deleted(conn, {"id": "sub_del"})

        sub = await conn.fetchrow(
            "SELECT tier, status FROM subscriptions WHERE stripe_subscription_id = 'sub_del'"
        )
        assert sub["tier"] == "free"
        assert sub["status"] == "canceled"
        key = await conn.fetchrow("SELECT tier FROM api_keys WHERE user_id = $1", user_id)
        assert key["tier"] == "free"
        organization_subscription = await conn.fetchrow(
            """
            SELECT stripe_subscription_id, plan_tier, status, included_users
            FROM organization_subscriptions
            WHERE organization_id = $1
            """,
            organization_id,
        )
        assert dict(organization_subscription) == {
            "stripe_subscription_id": "sub_del",
            "plan_tier": "free",
            "status": "canceled",
            "included_users": 1,
        }
        context_row = await _organization_row(conn, user_id, "business")
        assert context_row["plan_tier"] == "free"
    finally:
        await conn.close()


async def test_past_due_sync_preserves_scope_and_other_owner_workspace(fresh_db, monkeypatch):
    from api.routers import billing

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "past-due@test.com", 1, tier="free")
        owned_organization_id = await _make_owner_workspace(
            conn,
            user_id,
            scope_config={"regions": ["South East"]},
        )

        other_user_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash, name) VALUES ('owner@test.com', 'x', 'Owner') RETURNING id"
        )
        shared_organization_id = await _make_owner_workspace(
            conn,
            other_user_id,
            tier="business",
            scope_config={"regions": ["London"]},
        )
        await conn.execute(
            """
            INSERT INTO organization_members (organization_id, user_id, role)
            VALUES ($1, $2, 'member')
            """,
            shared_organization_id,
            user_id,
        )

        monkeypatch.setitem(billing.PRICE_TO_TIER, "price_radar_regional_test", "radar-regional")
        await billing._persist_subscription_state(
            conn,
            user_id,
            "sub_past_due",
            "radar-regional",
            "active",
            stripe_price_id="price_radar_regional_test",
        )
        await billing._handle_subscription_updated(
            conn,
            {
                "id": "sub_past_due",
                "status": "past_due",
                "items": {
                    "data": [
                        {"price": {"id": "price_radar_regional_test"}, "quantity": 1},
                    ],
                },
            },
        )

        owned = await conn.fetchrow(
            """
            SELECT plan_tier, status, included_users, scope_config
            FROM organization_subscriptions
            WHERE organization_id = $1
            """,
            owned_organization_id,
        )
        assert owned["plan_tier"] == "free"
        assert owned["status"] == "past_due"
        assert owned["included_users"] == 1
        assert json.loads(owned["scope_config"]) == {"regions": ["South East"]}

        shared = await conn.fetchrow(
            """
            SELECT plan_tier, status, scope_config
            FROM organization_subscriptions
            WHERE organization_id = $1
            """,
            shared_organization_id,
        )
        assert shared["plan_tier"] == "business"
        assert shared["status"] == "active"
        assert json.loads(shared["scope_config"]) == {"regions": ["London"]}
        assert await conn.fetchval(
            "SELECT tier FROM api_keys WHERE user_id = $1 AND is_active = TRUE",
            user_id,
        ) == "free"
    finally:
        await conn.close()


async def test_subscription_sync_rolls_back_all_entitlement_stores(fresh_db):
    from api.routers.billing import _persist_subscription_state

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "rollback@test.com", 1, tier="free")
        organization_id = await _make_owner_workspace(conn, user_id)

        transaction = conn.transaction()
        await transaction.start()
        await _persist_subscription_state(
            conn,
            user_id,
            "sub_rollback",
            "business",
            "active",
            stripe_price_id="price_business",
        )
        await transaction.rollback()

        assert await conn.fetchval(
            "SELECT COUNT(*) FROM subscriptions WHERE stripe_subscription_id = 'sub_rollback'"
        ) == 0
        assert await conn.fetchval(
            "SELECT tier FROM api_keys WHERE user_id = $1 AND is_active = TRUE",
            user_id,
        ) == "free"
        assert await conn.fetchval(
            "SELECT plan_tier FROM organization_subscriptions WHERE organization_id = $1",
            organization_id,
        ) == "free"
    finally:
        await conn.close()
