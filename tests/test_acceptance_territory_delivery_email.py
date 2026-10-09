"""Acceptance tests (CG-AT) for the Territory Brief delivery email and fulfilment refusals.

Reuses the recording fake from tests/test_territory_brief_fulfilment.py. The email
is the buyer's only route to the files, so its links, limits and legal wording are
asserted against what the token rows and consent rows actually record.
"""

from __future__ import annotations

import re
from dataclasses import replace

import pytest

from api.services.territory_brief_fulfilment import (
    TerritoryBriefFulfilmentError,
    fulfil_territory_brief_order,
)
from tests.test_territory_brief_fulfilment import CFG, ORDER_ID, FakeConn, _deps, _order, _session


async def _fulfil(order=None, deps=None):
    conn = FakeConn(order or _order())
    await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps or _deps())
    return conn


def _email(conn) -> tuple:
    return next(c for c in conn.execches if "INSERT INTO pending_emails" in c[0])


# CG-AT-007 happy: one email, to the paying address, with a separate download link for PDF and CSV.
@pytest.mark.asyncio
async def test_delivery_email_has_distinct_pdf_and_csv_links_to_the_buyer():
    conn = await _fulfil()
    _sql, to_email, subject, body, key = _email(conn)

    assert to_email == "buyer@example.com"
    assert subject == "Your CareGist Territory Opportunity Brief is ready"
    assert key == f"territory-brief-delivery:{ORDER_ID}"
    links = re.findall(r'href="(https://www\.caregist\.co\.uk/api/export\?token=[A-Za-z0-9_-]{43})"', body)
    assert len(links) == 2 and links[0] != links[1]
    assert "Download the brief (PDF)" in body and "Download the shortlist (CSV)" in body


# CG-AT-007 contract: the lifetime and cap in the email equal what is written to the token rows.
@pytest.mark.asyncio
async def test_email_limits_match_token_rows_written():
    conn = await _fulfil()
    body = _email(conn)[3]
    token_sql = next(c[0] for c in conn.execches if "INSERT INTO territory_brief_download_tokens" in c[0])

    assert "30 days and up to 5 downloads" in body
    assert "INTERVAL '30 days'" in token_sql


# CG-AT-007 contract: the email states the counts the brief really has, and the licence line.
@pytest.mark.asyncio
async def test_email_counts_and_attribution():
    conn = await _fulfil()
    body = _email(conn)[3]

    assert "covers 38 organisation(s)" in body and "30 are shortlisted and ranked" in body
    assert "Contains public sector information licensed under the Open Government Licence v3.0" in body
    assert "business-terms-2.2" in body
    assert "You expressly requested immediate supply" in body
    assert "does not affect your rights if the Brief is faulty or not as described" in body.replace("\n", " ")


# CG-AT-007 negative: a scope name carrying markup cannot inject HTML into the email.
@pytest.mark.asyncio
async def test_email_escapes_a_hostile_scope_name():
    base = _deps()

    def _generate(order_row):
        pack = base.generate(order_row)
        return replace(pack, scope_name="<script>alert(1)</script>")

    conn = await _fulfil(deps=replace(base, generate=_generate))
    body = _email(conn)[3]

    assert "<script>" not in body
    assert "&lt;script&gt;" in body


# CG-AT-007 negative: raw download tokens are never stored, only their hashes.
@pytest.mark.asyncio
async def test_raw_tokens_are_not_written_to_the_database():
    conn = await _fulfil()
    body = _email(conn)[3]
    raw_tokens = re.findall(r"token=([A-Za-z0-9_-]{43})", body)
    stored = [c[1] for c in conn.execches if "INSERT INTO territory_brief_download_tokens" in c[0]]

    assert len(raw_tokens) == 2 and len(stored) == 2
    for raw in raw_tokens:
        assert raw not in stored
    assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in stored)


# CG-AT-004 negative: an unpaid session produces no files, no tokens and no email.
@pytest.mark.asyncio
async def test_unpaid_session_delivers_nothing():
    conn = FakeConn(_order())
    deps = _deps(session=_session(payment_status="unpaid"))
    with pytest.raises(TerritoryBriefFulfilmentError):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)

    assert not any("INSERT INTO pending_emails" in c[0] for c in conn.execches)
    assert not any("territory_brief_download_tokens" in c[0] for c in conn.execches)


# CG-AT-004 negative: without the ticked terms checkbox the consent cannot be recorded, so nothing is delivered.
@pytest.mark.asyncio
async def test_session_without_accepted_terms_delivers_nothing():
    conn = FakeConn(_order())
    deps = _deps(session=_session(consent={"terms_of_service": None}))
    with pytest.raises(TerritoryBriefFulfilmentError):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)

    assert not any("INSERT INTO pending_emails" in c[0] for c in conn.execches)
