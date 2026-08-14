"""Integration tests for subscription state transitions (F-26, F-17).

Drives the real _persist_subscription_state against a Postgres schema and
asserts the resulting DB state: subscription row, key re-tiering, and seat-count
enforcement on downgrade.
"""

from __future__ import annotations

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


async def test_upgrade_retiers_all_active_keys(fresh_db):
    from api.routers.billing import _persist_subscription_state

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "up@test.com", 2, tier="free")

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

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        user_id = await _make_user_with_keys(conn, "del@test.com", 1, tier="business")
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
    finally:
        await conn.close()
