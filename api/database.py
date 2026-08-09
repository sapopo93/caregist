"""Async database connection pool using asyncpg."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from api.config import settings

logger = logging.getLogger("caregist.db")

_pool: asyncpg.Pool | None = None


def pool_limits(environ: Mapping[str, str] | None = None) -> tuple[int, int]:
    """Keep each Vercel instance within managed Postgres connection limits."""
    env = environ or os.environ
    if env.get("VERCEL") == "1":
        return 1, 3
    return 2, 20


async def init_pool() -> None:
    global _pool
    min_size, max_size = pool_limits()
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=min_size,
        max_size=max_size,
        command_timeout=settings.query_timeout_ms / 1000,
    )
    logger.info("Database pool initialized (min=%s, max=%s)", min_size, max_size)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn
