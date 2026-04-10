from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware.auth import validate_api_key


HEADERS = {"X-API-Key": "change_me_in_production"}


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def patched_db(mock_conn):
    @asynccontextmanager
    async def mock_get_connection():
        yield mock_conn

    app.dependency_overrides[validate_api_key] = lambda: {
        "tier": "business",
        "remaining": {
            "burst_remaining": 10,
            "daily_remaining": 100,
            "rolling_7d_remaining": 100,
            "monthly_remaining": 100,
        },
        "user_id": 1,
        "email": "ops@caregist.co.uk",
    }
    with patch("api.routers.providers.get_connection", mock_get_connection):
        yield mock_conn
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_xlsx_export_includes_total_count_header(patched_db):
    mock_conn = patched_db
    mock_conn.fetch.return_value = [
        {
            "name": "Sunrise Care Home",
            "slug": "sunrise-care-home",
            "type": "Social Care Org",
            "status": "ACTIVE",
            "town": "Bournemouth",
            "county": "Dorset",
            "postcode": "BH1 1AA",
            "region": "South West",
            "local_authority": "Bournemouth",
            "overall_rating": "Good",
            "service_types": "Care home service with nursing",
            "specialisms": "Dementia",
            "number_of_beds": 25,
            "quality_score": 82,
            "quality_tier": "GOOD",
            "phone": "01202000000",
            "website": "https://example.com",
            "last_inspection_date": "2025-01-01",
            "inspection_report_url": "https://example.com/report",
        }
    ]
    mock_conn.fetchrow.return_value = {"total": 1}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/providers/export.xlsx?region=London", headers=HEADERS)

    assert resp.status_code == 200
    assert resp.headers["x-total-count"] == "1"
    assert resp.headers["content-disposition"] == "attachment; filename=caregist_export.xlsx"
