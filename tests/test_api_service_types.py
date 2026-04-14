from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.mark.asyncio
async def test_service_types_returns_fallback_when_db_fails():
    conn = AsyncMock()
    conn.fetch.side_effect = RuntimeError("db unavailable")

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.regions.get_connection", mock_get_connection):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/service-types")

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert len(body["data"]) > 0
    assert body["data"][0]["provider_count"] == 0
