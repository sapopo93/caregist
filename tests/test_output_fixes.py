"""Wave 3 output fixes for the Territory Brief, outbound emails and price copy.

Each test pins one gap from the quality review (H1, H2, H5, H6, H8, M1, M3, C2)
and failed on ``claude/acceptance-caregist`` before the fix.
"""

from __future__ import annotations

import csv
import io
import re
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware.auth import validate_api_key
from api.services.territory_brief import (
    MIN_SHORTLIST,
    OGL_ATTRIBUTION,
    PurchaseContext,
    brief_to_csv,
    generate_territory_opportunity_brief,
)
from api.services.territory_brief_render import render_brief_pdf

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "territory_brief"
GENERATED = datetime(2026, 10, 8, tzinfo=timezone.utc)


def _brief(name: str, target: int = 30):
    return generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": name, "window_days": 365, "shortlist_target": target},
        PurchaseContext(order_reference="wave3", generated_at=GENERATED, terms_version="wave3"),
        locations_source=FIX / "locations_detail.jsonl",
        providers_source=FIX / "providers_detail.jsonl",
    )


def _pdf_text(brief, tmp_path: Path) -> str:
    path = tmp_path / "brief.pdf"
    path.write_bytes(render_brief_pdf(brief))
    return subprocess.run(
        ["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True
    ).stdout


def _csv_rows(brief) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(brief_to_csv(brief))))


@pytest.fixture(scope="module")
def southampton():
    return _brief("Southampton")


@pytest.fixture(scope="module")
def isle_of_wight():
    # The fixture yields 8 organisations here, below the code floor of 10.
    return _brief("Isle of Wight", target=50)


# H1 -------------------------------------------------------------------------


def test_pdf_states_the_real_generation_date_and_the_source_edition(southampton, tmp_path):
    front = _pdf_text(southampton, tmp_path).split("2. Ranked opportunity shortlist")[0]
    assert "generated 08 October 2026" in front
    assert "generated 18 February 2026" not in front
    assert southampton.executive_summary["date_generated"] == "2026-10-08"
    assert southampton.executive_summary["source_edition"] == southampton.as_of_date.isoformat()
    assert f"Source edition {southampton.as_of_date.isoformat()}" in re.sub(r"\s+", " ", front)


# H2 -------------------------------------------------------------------------


def test_cqc_record_links_use_the_public_cqc_location_page(southampton, tmp_path):
    rows = _csv_rows(southampton)
    for row in rows:
        assert row["cqc_record_url"] == f"https://www.cqc.org.uk/location/{row['cqc_location_id']}"
    text = _pdf_text(southampton, tmp_path)
    assert "api.service.cqc.org.uk" not in text
    assert "https://www.cqc.org.uk/location/" in text


# H8 -------------------------------------------------------------------------


def test_csv_carries_open_government_licence_on_every_row(southampton):
    rows = _csv_rows(southampton)
    assert rows
    assert all(row["licence"] == OGL_ATTRIBUTION for row in rows)


# C2 -------------------------------------------------------------------------


def test_short_brief_carries_a_plain_shortfall_notice_in_pdf_and_csv(isle_of_wight, tmp_path):
    shortlisted = len(isle_of_wight.shortlist)
    assert shortlisted < MIN_SHORTLIST  # floor unchanged; the brief is not padded
    notice = isle_of_wight.executive_summary["shortfall_notice"]
    assert notice and f"{shortlisted} organisation(s)" in notice and str(MIN_SHORTLIST) in notice

    pdf = re.sub(r"\s+", " ", _pdf_text(isle_of_wight, tmp_path))
    assert re.sub(r"\s+", " ", notice) in pdf

    rows = _csv_rows(isle_of_wight)
    assert len(rows) == shortlisted
    assert all(row["shortlist_notice"] == notice for row in rows)


def test_full_brief_has_no_shortfall_notice(southampton, tmp_path):
    assert len(southampton.shortlist) >= MIN_SHORTLIST
    assert southampton.executive_summary["shortfall_notice"] is None
    assert "Shortfall" not in _pdf_text(southampton, tmp_path)
    assert all(row["shortlist_notice"] == "" for row in _csv_rows(southampton))


# M3 -------------------------------------------------------------------------


def test_executive_text_points_at_the_right_sections(southampton, tmp_path):
    text = re.sub(r"\s+", " ", _pdf_text(southampton, tmp_path))
    assert "(see section 6)" in text and "(see section 5)" not in text
    assert "sections 1-7 are the executive brief" in text
    assert "Strongest areas of movement" not in text
    assert "Highest-ranked organisations:" in text
    # A local-authority brief has one parent region, so the table would only
    # repeat the territory.
    assert len(southampton.territory_insights["activity_by_sub_area"]) == 1
    assert "Activity by sub-area" not in text


# H5 -------------------------------------------------------------------------


def _conn(row):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=row)

    @asynccontextmanager
    async def get_connection():
        yield conn

    return get_connection


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["homepage", "radius_finder"])
async def test_subscribe_queues_no_email_while_outbound_gate_closed(source):
    queue = AsyncMock()
    with patch("api.routers.subscribe.get_connection", _conn({"id": 1})), \
         patch("api.routers.subscribe.queue_email", queue), \
         patch("api.routers.subscribe.log_event", AsyncMock()), \
         patch("api.config.settings.outbound_communications_enabled", False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            resp = await client.post("/api/v1/subscribe", json={"email": "a@example.com", "source": source})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"success": True, "existing": False}
    queue.assert_not_called()


@pytest.mark.asyncio
async def test_subscribe_still_queues_welcome_email_when_gate_open():
    queue = AsyncMock()
    with patch("api.routers.subscribe.get_connection", _conn({"id": 1})), \
         patch("api.routers.subscribe.queue_email", queue), \
         patch("api.routers.subscribe.log_event", AsyncMock()), \
         patch("api.config.settings.outbound_communications_enabled", True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            resp = await client.post("/api/v1/subscribe", json={"email": "a@example.com"})
    assert resp.status_code == 200
    assert queue.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("gate_open,expected", [(False, 0), (True, 1)])
async def test_api_application_email_follows_outbound_gate(gate_open, expected):
    queue = AsyncMock()
    with patch("api.routers.api_applications.get_connection", _conn({"id": 7})), \
         patch("api.routers.api_applications.queue_email", queue), \
         patch("api.routers.api_applications.log_event", AsyncMock()), \
         patch("api.config.settings.outbound_communications_enabled", gate_open):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            resp = await client.post("/api/v1/api-applications", json={
                "company_name": "Acme", "contact_name": "Jo", "contact_email": "jo@example.com",
                "use_case": "Research",
            })
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"] == {"id": 7}
    assert queue.await_count == expected


# H6 -------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("fast_track", [False, True])
async def test_claim_email_and_api_state_the_same_turnaround(fast_track):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[
        {"id": "L1", "is_claimed": False},
        None,
        {"id": 1, "provider_id": "L1", "status": "pending", "claimant_name": "J",
         "claimant_email": "jane@care.co.uk", "created_at": "2026-01-01"},
    ])

    @asynccontextmanager
    async def get_connection():
        yield conn

    queue = AsyncMock()
    app.dependency_overrides[validate_api_key] = lambda: {
        "tier": "starter", "remaining": {}, "user_id": 1, "email": "jane@care.co.uk",
    }
    try:
        with patch("api.routers.claims.get_connection", get_connection), \
             patch("api.routers.claims.settings.provider_claims_enabled", True), \
             patch("api.routers.claims.settings.outbound_communications_enabled", True), \
             patch("api.utils.email_queue.queue_email", queue), \
             patch("api.utils.analytics.log_event", AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
                resp = await client.post("/api/v1/providers/p/claim", json={
                    "claimant_name": "Jane Smith", "claimant_email": "jane@care.co.uk",
                    "claimant_role": "Registered Manager", "fast_track": fast_track,
                    "proof_of_association": "I am the registered manager, CQC 12345",
                }, headers={"X-API-Key": "test-master-key-for-pytest"})
    finally:
        app.dependency_overrides = {}
    assert resp.status_code == 201, resp.text
    assert "2 business days" in resp.json()["message"]
    bodies = [call.args[2] for call in queue.await_args_list]
    assert bodies, "no claim email queued"
    assert "2 business days" in bodies[0]
    assert "24" not in bodies[0]
    assert not any("higher-visibility placement" in body for body in bodies)


# M1 -------------------------------------------------------------------------


@pytest.mark.parametrize("rel", [
    "frontend/app/pricing/page.tsx",
    "frontend/app/page.tsx",
    "frontend/app/pricing/territory/page.tsx",
])
def test_buyer_pages_read_the_brief_price_from_the_constant(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert not re.search(r"(?:£|&pound;)\s?745\b", text), rel
    assert "TERRITORY_BRIEF_PRICE_GBP" in text


# --- Re-check follow-up: marketing follow-ups after a saved comparison or a CSV export (H5) ---

def _business_auth():
    return {
        "tier": "business",
        "remaining": {"burst_remaining": 10, "daily_remaining": 100, "rolling_7d_remaining": 100, "monthly_remaining": 100},
        "user_id": 1,
        "email": "ops@example.com",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("gate_open,expected", [(False, 0), (True, 1)])
async def test_comparison_follow_up_email_follows_outbound_gate(gate_open, expected):
    from api.middleware.auth import validate_api_key

    queue = AsyncMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=lambda sql, *a: {"email": "ops@example.com"} if "FROM users" in sql else {"id": 9, "share_token": "t", "slug_list": ["a", "b"], "title": None})

    @asynccontextmanager
    async def get_conn():
        yield conn

    app.dependency_overrides[validate_api_key] = _business_auth
    try:
        with patch("api.routers.comparisons.get_connection", get_conn), \
             patch("api.utils.email_queue.queue_email", queue), \
             patch("api.utils.analytics.log_event", AsyncMock()), \
             patch("api.config.settings.outbound_communications_enabled", gate_open):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
                resp = await client.post("/api/v1/comparisons", json={"slug_list": ["a", "b"]}, headers={"X-API-Key": "k"})
    finally:
        app.dependency_overrides = {}
    assert resp.status_code == 201, resp.text
    assert queue.await_count == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("gate_open,expected", [(False, 0), (True, 1)])
async def test_csv_export_follow_up_email_follows_outbound_gate(gate_open, expected):
    from api.middleware.auth import validate_api_key

    queue = AsyncMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"name": "Sunrise Care Home", "slug": "sunrise", "region": "London", "overall_rating": "Good"}])
    conn.fetchrow = AsyncMock(return_value={"total": 1})

    @asynccontextmanager
    async def get_conn():
        yield conn

    app.dependency_overrides[validate_api_key] = _business_auth
    try:
        with patch("api.routers.providers.get_connection", get_conn), \
             patch("api.routers.providers.settings.directory_export_delivery_enabled", True), \
             patch("api.utils.email_queue.queue_email", queue), \
             patch("api.utils.analytics.log_event", AsyncMock()), \
             patch("api.config.settings.outbound_communications_enabled", gate_open):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
                resp = await client.get("/api/v1/providers/export.csv?region=London", headers={"X-API-Key": "k"})
    finally:
        app.dependency_overrides = {}
    assert resp.status_code == 200, resp.text
    assert queue.await_count == expected
