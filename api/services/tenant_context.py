"""Organization resolution and database tenant context for Radar routes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from api.database import get_connection


@dataclass(frozen=True)
class OrganizationContext:
    organization_id: UUID
    user_id: int
    role: str
    plan_tier: str
    scope_config: dict


def normalize_scope_config(value: object) -> dict:
    """Return a JSON object regardless of the asyncpg JSON codec in use."""
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Organization scope configuration is invalid JSON.") from exc
    if not isinstance(value, Mapping):
        raise ValueError("Organization scope configuration must be a JSON object.")
    return dict(value)


async def _organization_row(
    conn: asyncpg.Connection,
    user_id: int,
    fallback_tier: str,
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT o.id AS organization_id, om.role,
               COALESCE(os.plan_tier, $2) AS plan_tier,
               COALESCE(os.scope_config, '{}'::jsonb) AS scope_config
        FROM organization_members om
        JOIN organizations o ON o.id = om.organization_id
        LEFT JOIN organization_subscriptions os ON os.organization_id = o.id
        WHERE om.user_id = $1
        ORDER BY om.created_at ASC, o.created_at ASC
        LIMIT 1
        """,
        user_id,
        fallback_tier,
    )


async def _provision_default_organization(
    conn: asyncpg.Connection,
    user_id: int,
    fallback_tier: str,
) -> None:
    """Idempotently provision the tenant workspace for an authenticated user."""
    await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(user_id))
    organization_id = await conn.fetchval(
        """
        INSERT INTO organizations (name, slug, created_by_user_id)
        SELECT COALESCE(NULLIF(BTRIM(name), ''), 'CareGist account'),
               'account-' || id::text, id
        FROM users
        WHERE id = $1
        ON CONFLICT (created_by_user_id) DO UPDATE
          SET updated_at = organizations.updated_at
        RETURNING id
        """,
        user_id,
    )
    if organization_id is None:
        raise HTTPException(status_code=409, detail="Your account could not be provisioned.")

    await conn.execute(
        """
        INSERT INTO organization_members (organization_id, user_id, role)
        VALUES ($1, $2, 'owner')
        ON CONFLICT (organization_id, user_id) DO NOTHING
        """,
        organization_id,
        user_id,
    )
    await conn.execute(
        """
        INSERT INTO organization_subscriptions (
          organization_id, stripe_subscription_id, plan_tier, status,
          included_users, current_period_end
        )
        SELECT $1, subscription.stripe_subscription_id,
               COALESCE(subscription.tier, $3),
               COALESCE(subscription.status, 'active'),
               GREATEST(COALESCE(subscription.max_users, 1), 1),
               subscription.current_period_end
        FROM (SELECT 1) seed
        LEFT JOIN LATERAL (
          SELECT stripe_subscription_id, tier, status, max_users, current_period_end
          FROM subscriptions
          WHERE user_id = $2
          ORDER BY CASE WHEN status IN ('active', 'trialing') THEN 0 ELSE 1 END,
                   created_at DESC
          LIMIT 1
        ) subscription ON TRUE
        ON CONFLICT (organization_id) DO NOTHING
        """,
        organization_id,
        user_id,
        fallback_tier,
    )


async def resolve_organization_context(user_id: int, fallback_tier: str) -> OrganizationContext:
    """Resolve the user's oldest membership as the current beta organization."""
    async with get_connection() as conn:
        row = await _organization_row(conn, user_id, fallback_tier)
        if not row:
            async with conn.transaction():
                await _provision_default_organization(conn, user_id, fallback_tier)
            row = await _organization_row(conn, user_id, fallback_tier)
    if not row:
        raise HTTPException(status_code=409, detail="Your organization workspace has not been provisioned yet.")
    return OrganizationContext(
        organization_id=row["organization_id"],
        user_id=user_id,
        role=row["role"],
        plan_tier=row["plan_tier"] or fallback_tier,
        scope_config=normalize_scope_config(row["scope_config"]),
    )


@asynccontextmanager
async def tenant_connection(context: OrganizationContext) -> AsyncGenerator[asyncpg.Connection, None]:
    """Open a transaction with the user identity visible to Postgres RLS."""
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(context.user_id))
            yield conn
