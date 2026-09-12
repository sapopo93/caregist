"""Real-Postgres integration test for Territory Opportunity Brief fulfilment.

Runs the whole fulfilment path (`fulfil_territory_brief_order`) against a real
Postgres that has migration 060 applied, inside a transaction that is always
rolled back so nothing persists. Skipped unless TB_PG_URL points at such a DB
(use a disposable Neon branch, never production).

    TB_PG_URL='postgresql://.../neondb?sslmode=require' \
      .venv/bin/python -m pytest tests/test_territory_brief_pg_integration.py -q
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

TB_PG_URL = os.environ.get("TB_PG_URL")
FIXTURE = Path(__file__).parent / "fixtures" / "territory_brief"

pytestmark = pytest.mark.skipif(
    not TB_PG_URL or not (FIXTURE / "locations_detail.jsonl").exists(),
    reason="set TB_PG_URL to a migration-060 Postgres branch (and keep the fixture) to run",
)


@pytest.mark.asyncio
async def test_full_fulfilment_against_real_postgres():
    import asyncpg

    from api.services import territory_brief_fulfilment as tbf
    from api.services.territory_brief import (
        PurchaseContext,
        brief_to_csv,
        generate_territory_opportunity_brief,
    )
    from api.services.territory_brief_render import render_brief_pdf

    consent_sha = hashlib.sha256(tbf.TERRITORY_BRIEF_CONSENT_TEXT.encode()).hexdigest()
    terms_sha = "a" * 64
    cfg = tbf.FulfilmentSettings(
        stripe_price_territory_brief="price_pg_itest",
        terms_version="pg-itest",
        terms_sha256=terms_sha,
        consent_sha256=consent_sha,
        app_url="https://itest.local",
    )

    def _generate(order_row: dict) -> tbf.GeneratedPack:
        brief = generate_territory_opportunity_brief(
            {
                "kind": order_row["scope_kind"],
                "name": order_row["scope_name"],
                "window_days": order_row["scope_window_days"],
                "shortlist_target": order_row["scope_shortlist_target"],
            },
            PurchaseContext(
                order_reference=str(order_row["id"]),
                generated_at=datetime.now(timezone.utc),
                terms_version=cfg.terms_version,
            ),
            locations_source=FIXTURE / "locations_detail.jsonl",
            providers_source=FIXTURE / "providers_detail.jsonl",
        )
        return tbf.GeneratedPack(
            pdf_bytes=render_brief_pdf(brief),
            csv_text=brief_to_csv(brief),
            scope_name=brief.scope.name,
            considered=brief.considered_locations,
            shortlisted=len(brief.shortlist),
        )

    uploads: list[tuple] = []

    def _upload(order_id, kind, data, content_type) -> tbf.BlobRef:
        uploads.append((kind, len(data), content_type))
        return tbf.BlobRef(pathname=f"territory-briefs/{order_id}/pg-itest/brief.{kind}")

    audit_calls: list[dict] = []

    async def _audit(**kw):
        audit_calls.append(kw)

    async def _record_failure(order_id, message):  # pragma: no cover - must not run
        raise AssertionError(f"record_failure should not be called: {message}")

    session = {"id": "cs_pg_itest", "metadata": {"type": tbf.METADATA_TYPE}}

    conn = await asyncpg.connect(TB_PG_URL)
    tx = conn.transaction()
    await tx.start()
    try:
        order = await conn.fetchrow(
            """
            INSERT INTO territory_brief_orders
                (customer_email, stripe_price_id, scope_kind, scope_name,
                 scope_window_days, scope_shortlist_target, stripe_checkout_session_id)
            VALUES ('buyer@example.com', 'price_pg_itest', 'local_authority', 'Southampton',
                    365, 30, 'cs_pg_itest')
            RETURNING id
            """
        )
        order_id = str(order["id"])

        scope = {"kind": "local_authority", "name": "Southampton",
                 "window_days": 365, "shortlist_target": 30}
        authoritative = {
            "id": "cs_pg_itest",
            "metadata": tbf.build_checkout_metadata(order_id, scope, cfg),
            "payment_status": "paid",
            "consent": {"terms_of_service": "accepted"},
            "line_items": {"data": [{"price": {"id": "price_pg_itest"}, "quantity": 1}]},
            "payment_intent": "pi_pg_itest",
            "amount_total": 74500,
            "currency": "gbp",
        }
        deps = tbf.FulfilmentDeps(
            generate=_generate,
            upload=_upload,
            retrieve_session=lambda _sid: authoritative,
            record_failure=_record_failure,
            write_audit_log=_audit,
        )

        # 1. first fulfilment
        await tbf.fulfil_territory_brief_order(conn, session, cfg=cfg, deps=deps)

        row = await conn.fetchrow("SELECT * FROM territory_brief_orders WHERE id = $1", order_id)
        assert row["status"] == "fulfilled"
        assert row["blob_pdf_pathname"] and row["blob_csv_pathname"]
        assert row["artifact_sha256"] and len(row["artifact_sha256"]) == 64
        assert row["paid_at"] is not None and row["fulfilled_at"] is not None

        consent = await conn.fetchrow(
            "SELECT * FROM territory_brief_consents WHERE order_id = $1", order_id
        )
        assert consent["immediate_supply_consented"] is True
        assert consent["terms_version"] == "pg-itest"
        assert consent["consent_text_sha256"] == consent_sha

        tokens = await conn.fetch(
            "SELECT artifact_kind FROM territory_brief_download_tokens WHERE order_id = $1 ORDER BY artifact_kind",
            order_id,
        )
        assert [t["artifact_kind"] for t in tokens] == ["csv", "pdf"]

        emails = await conn.fetch(
            "SELECT idempotency_key, to_email FROM pending_emails WHERE idempotency_key = $1",
            f"territory-brief-delivery:{order_id}",
        )
        assert len(emails) == 1 and emails[0]["to_email"] == "buyer@example.com"

        assert {u[0] for u in uploads} == {"pdf", "csv"}
        assert audit_calls and audit_calls[0]["action"] == "billing.territory_brief.fulfil"

        # 2. idempotent re-run: no duplicates, no error
        await tbf.fulfil_territory_brief_order(conn, session, cfg=cfg, deps=deps)
        assert await conn.fetchval(
            "SELECT count(*) FROM territory_brief_consents WHERE order_id = $1", order_id
        ) == 1
        assert await conn.fetchval(
            "SELECT count(*) FROM territory_brief_download_tokens WHERE order_id = $1", order_id
        ) == 2
        assert await conn.fetchval(
            "SELECT count(*) FROM pending_emails WHERE idempotency_key = $1",
            f"territory-brief-delivery:{order_id}",
        ) == 1

        # 3. consent row is append-only
        with pytest.raises(asyncpg.PostgresError, match="append-only"):
            await conn.execute(
                "UPDATE territory_brief_consents SET terms_version = 'x' WHERE order_id = $1",
                order_id,
            )
    finally:
        await tx.rollback()
        await conn.close()
