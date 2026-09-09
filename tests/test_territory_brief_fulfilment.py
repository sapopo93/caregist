"""Unit tests for Stripe-confirmed Territory Opportunity Brief fulfilment.

No database, Stripe, CQC snapshot or network: the connection is a recording
fake and every collaborator is injected.
"""

from __future__ import annotations

import hashlib

import pytest

from api.services import territory_brief_fulfilment as fulfil
from api.services.territory_brief_fulfilment import (
    FulfilmentDeps,
    FulfilmentSettings,
    GeneratedPack,
    TerritoryBriefFulfilmentError,
    build_checkout_metadata,
    fulfil_territory_brief_order,
)

TERMS_SHA = "a" * 64
CONSENT_SHA = "b" * 64
PRICE = "price_territory_brief_test"

CFG = FulfilmentSettings(
    stripe_price_territory_brief=PRICE,
    terms_version="business-terms-2.2",
    terms_sha256=TERMS_SHA,
    consent_sha256=CONSENT_SHA,
    app_url="https://www.caregist.co.uk",
)

ORDER_ID = "11111111-1111-1111-1111-111111111111"


class FakeConn:
    def __init__(self, order_row):
        self._order_row = order_row
        self.execches: list[tuple] = []

    async def fetchrow(self, *_args):
        return self._order_row

    async def execute(self, *args):
        self.execches.append(args)
        return "UPDATE 1"

    def sql_log(self) -> str:
        return "\n".join(call[0] for call in self.execches)


def _order(**over):
    row = {
        "id": ORDER_ID,
        "customer_email": "buyer@example.com",
        "stripe_price_id": PRICE,
        "status": "pending",
        "scope_kind": "local_authority",
        "scope_name": "Southampton",
        "scope_window_days": 90,
        "scope_shortlist_target": 30,
        "generation_attempts": 0,
    }
    row.update(over)
    return row


def _session(**over):
    meta = {
        "type": fulfil.METADATA_TYPE,
        "order_id": ORDER_ID,
        "price_id": PRICE,
        "scope_kind": "local_authority",
        "scope_name": "Southampton",
        "scope_window_days": "90",
        "scope_shortlist_target": "30",
        "terms_version": "business-terms-2.2",
        "terms_sha256": TERMS_SHA,
        "consent_text_sha256": CONSENT_SHA,
    }
    meta.update(over.pop("metadata", {}))
    base = {
        "id": "cs_test_123",
        "metadata": meta,
        "payment_status": "paid",
        "consent": {"terms_of_service": "accepted"},
        "line_items": {"data": [{"price": {"id": PRICE}, "quantity": 1}]},
        "payment_intent": "pi_test_123",
        "amount_total": 79500,
        "currency": "gbp",
    }
    base.update(over)
    return base


def _deps(*, session=None, generate=None, fail_uploads=False, failures=None, audits=None):
    failures = failures if failures is not None else []
    audits = audits if audits is not None else []

    def _generate(order_row):
        if generate == "raise":
            raise RuntimeError("boom in generator")
        return GeneratedPack(
            pdf_bytes=b"%PDF-1.4 fake",
            csv_text="rank,organisation\n1,Acme Care Ltd\n",
            scope_name=order_row["scope_name"],
            considered=38,
            shortlisted=30,
        )

    def _upload(order_id, kind, data, content_type):
        if fail_uploads:
            raise RuntimeError("blob down")
        return fulfil.BlobRef(pathname=f"territory-briefs/{order_id}/xyz/brief.{kind}")

    async def _record_failure(order_id, message):
        failures.append((order_id, message))

    async def _audit(**kwargs):
        audits.append(kwargs)

    return FulfilmentDeps(
        generate=_generate,
        upload=_upload,
        retrieve_session=lambda sid: session or _session(),
        record_failure=_record_failure,
        write_audit_log=_audit,
    )


@pytest.mark.asyncio
async def test_happy_path_generates_uploads_entitles_and_emails():
    conn = FakeConn(_order())
    failures, audits = [], []
    deps = _deps(failures=failures, audits=audits)

    await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)

    sql = conn.sql_log()
    assert "SET status = 'generating'" in sql
    assert "INSERT INTO territory_brief_consents" in sql
    assert "SET status = 'fulfilled'" in sql
    token_inserts = [c for c in conn.execches if "territory_brief_download_tokens" in c[0]]
    assert len(token_inserts) == 2
    assert {c[3] for c in token_inserts} == {"pdf", "csv"}
    email_insert = next(c for c in conn.execches if "INSERT INTO pending_emails" in c[0])
    assert "Southampton" in email_insert[3]
    assert email_insert[4] == f"territory-brief-delivery:{ORDER_ID}"
    assert "/api/export?token=" in email_insert[3]
    assert not failures
    assert audits and audits[0]["action"] == "billing.territory_brief.fulfil"


@pytest.mark.asyncio
async def test_duplicate_delivery_on_fulfilled_order_is_a_noop():
    conn = FakeConn(_order(status="fulfilled"))
    deps = _deps()
    await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert conn.execches == []  # nothing mutated


@pytest.mark.asyncio
async def test_generation_failure_records_failure_and_reraises_without_fulfilling():
    conn = FakeConn(_order())
    failures = []
    deps = _deps(generate="raise", failures=failures)
    with pytest.raises(TerritoryBriefFulfilmentError, match="generation failed"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    sql = conn.sql_log()
    assert "SET status = 'generating'" in sql
    assert "SET status = 'fulfilled'" not in sql
    assert failures and failures[0][0] == ORDER_ID
    assert "boom in generator" in failures[0][1]


@pytest.mark.asyncio
async def test_blob_upload_failure_is_treated_as_retryable_failure():
    conn = FakeConn(_order())
    failures = []
    deps = _deps(fail_uploads=True, failures=failures)
    with pytest.raises(TerritoryBriefFulfilmentError):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert "SET status = 'fulfilled'" not in conn.sql_log()
    assert failures


@pytest.mark.asyncio
async def test_exhausted_attempts_stop_retrying():
    conn = FakeConn(_order(generation_attempts=5))
    deps = _deps()
    with pytest.raises(TerritoryBriefFulfilmentError, match="manual review"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "session_over, match",
    [
        ({"payment_status": "unpaid"}, "before payment became valid"),
        ({"consent": {}}, "no Stripe terms acceptance"),
        ({"metadata": {"type": "full_dataset"}}, "immutable order metadata"),
        ({"metadata": {"terms_sha256": "c" * 64}}, "legal evidence does not match"),
        ({"metadata": {"consent_text_sha256": "d" * 64}}, "legal evidence does not match"),
        ({"line_items": {"data": [{"price": {"id": "price_other"}, "quantity": 1}]}}, "unexpected line items"),
        ({"line_items": {"data": [{"price": {"id": PRICE}, "quantity": 2}]}}, "unexpected line items"),
        ({"metadata": {"scope_name": "Kent"}}, "scope does not match"),
    ],
)
async def test_rejects_tampered_or_wrong_product_events(session_over, match):
    conn = FakeConn(_order())
    deps = _deps(session=_session(**session_over))
    with pytest.raises(TerritoryBriefFulfilmentError, match=match):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)
    assert "SET status = 'fulfilled'" not in conn.sql_log()


@pytest.mark.asyncio
async def test_refunded_order_cannot_be_fulfilled():
    conn = FakeConn(_order(status="refunded"))
    deps = _deps()
    with pytest.raises(TerritoryBriefFulfilmentError, match="refunded"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)


@pytest.mark.asyncio
async def test_order_not_matching_reserved_row_is_rejected():
    conn = FakeConn(_order(stripe_price_id="price_wrong"))
    deps = _deps()
    with pytest.raises(TerritoryBriefFulfilmentError, match="does not match its reserved local order"):
        await fulfil_territory_brief_order(conn, {"id": "cs_test_123"}, cfg=CFG, deps=deps)


def test_generated_pack_sha_is_stable_and_content_bound():
    a = GeneratedPack(b"pdf-a", "csv-a", "X", 1, 1)
    b = GeneratedPack(b"pdf-a", "csv-a", "X", 1, 1)
    c = GeneratedPack(b"pdf-a", "csv-DIFFERENT", "X", 1, 1)
    assert a.sha256 == b.sha256 != c.sha256
    assert a.sha256 == hashlib.sha256(b"pdf-a" + b"csv-a").hexdigest()


def test_build_checkout_metadata_is_flat_strings():
    meta = build_checkout_metadata(ORDER_ID, {"kind": "region", "name": "South East"}, CFG)
    assert meta["type"] == fulfil.METADATA_TYPE
    assert all(isinstance(v, str) for v in meta.values())
    assert meta["terms_sha256"] == TERMS_SHA
