"""Shared test fixtures for API tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg pool and connection."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock()

    pool = AsyncMock()
    pool.acquire = MagicMock()

    # Make acquire work as async context manager
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = cm

    return pool, conn


@pytest.fixture
def patch_db(mock_pool):
    """Patch the database module to use a mock pool."""
    pool, conn = mock_pool
    with patch("api.database._pool", pool):
        yield conn


@pytest.fixture
def api_headers():
    """Default API headers with dev key."""
    return {"X-API-Key": "change_me_in_production"}


@pytest.fixture
def app():
    """Create test FastAPI app."""
    from api.main import app
    return app
