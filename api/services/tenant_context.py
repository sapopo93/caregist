"""Organization resolution and database tenant context for Radar routes."""

from __future__ import annotations

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


async def resolve_organization_context(user_id: int, fallback_tier: str) -> OrganizationContext:
    """Resolve the user's oldest membership as the current beta organization."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
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
    if not row:
        raise HTTPException(status_code=409, detail="Your organization workspace has not been provisioned yet.")
    return OrganizationContext(
        organization_id=row["organization_id"],
        user_id=user_id,
        role=row["role"],
        plan_tier=row["plan_tier"] or fallback_tier,
        scope_config=dict(row["scope_config"] or {}),
    )


@asynccontextmanager
async def tenant_connection(context: OrganizationContext) -> AsyncGenerator[asyncpg.Connection, None]:
    """Open a transaction with the user identity visible to Postgres RLS."""
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.user_id', $1, true)", str(context.user_id))
            yield conn
