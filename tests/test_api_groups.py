from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetchval = AsyncMock()
    return conn


@pytest.fixture
def patched_groups_db(mock_conn):
    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    with patch("api.routers.groups.get_connection", mock_get_connection):
        yield mock_conn


@pytest.mark.asyncio
async def test_public_groups_list_works_without_api_key(patched_groups_db):
    conn = patched_groups_db
    conn.fetch.return_value = [
        {
            "provider_id": "1-102643122",
            "group_name": "Voyage 1 Limited",
            "slug": "voyage-1-limited",
            "location_count": 279,
            "outstanding_count": 12,
            "good_count": 199,
            "ri_count": 19,
            "inadequate_count": 0,
            "not_inspected_count": 49,
            "avg_quality_score": 98.7,
            "pct_good_or_outstanding": 91.7,
            "total_beds": 1900,
            "regions": ["London"],
            "provider_types": ["Social Care Org"],
            "latest_inspection": "2024-01-24",
        }
    ]
    conn.fetchval.return_value = 1
    remaining = {
        "burst_remaining": 1,
        "daily_remaining": 19,
        "rolling_7d_remaining": 59,
        "monthly_remaining": 299,
    }

    with patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value=remaining)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/groups?min_locations=3&per_page=5")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["group_name"] == "Voyage 1 Limited"

    list_query = conn.fetch.await_args.args[0]
    count_query = conn.fetchval.await_args.args[0]
    assert "group_name IS NOT NULL" in list_query
    assert "BTRIM(group_name) <> ''" in list_query
    assert "group_name IS NOT NULL" in count_query
    assert "BTRIM(group_name) <> ''" in count_query


@pytest.mark.asyncio
async def test_public_group_detail_works_without_api_key_and_excludes_unnamed_groups(patched_groups_db):
    conn = patched_groups_db
    conn.fetchrow.side_effect = [
        {
            "provider_id": "1-102643122",
            "group_name": "Voyage 1 Limited",
            "slug": "voyage-1-limited",
            "location_count": 279,
            "outstanding_count": 12,
            "good_count": 199,
            "ri_count": 19,
            "inadequate_count": 0,
            "not_inspected_count": 49,
            "avg_quality_score": 98.7,
            "pct_good_or_outstanding": 91.7,
            "total_beds": 1900,
            "regions": ["London"],
            "provider_types": ["Social Care Org"],
            "latest_inspection": "2024-01-24",
        },
        {"avg_quality_score": 82.1, "pct_good_or_outstanding": 74.2},
    ]
    conn.fetch.return_value = []
    remaining = {
        "burst_remaining": 1,
        "daily_remaining": 19,
        "rolling_7d_remaining": 59,
        "monthly_remaining": 299,
    }

    with patch("api.middleware.auth.check_rate_limit", AsyncMock(return_value=remaining)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/groups/voyage-1-limited")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["group_name"] == "Voyage 1 Limited"

    detail_query = conn.fetchrow.await_args_list[0].args[0]
    assert "group_name IS NOT NULL" in detail_query
    assert "BTRIM(group_name) <> ''" in detail_query
