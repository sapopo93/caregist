"""Acceptance tests (CG-AT) for Territory Brief download tokens on a real schema.

The download rules live in one SQL statement inside
``frontend/lib/territory-brief-download.ts``. The TypeScript unit tests feed it a
fake query function, so they cannot show that the statement enforces the limits
the delivery email promises ("30 days and up to 5 downloads"). This test lifts
that exact statement out of the source and runs it on a throwaway Postgres built
from init.sql and every migration. Synthetic data only; everything is rolled back.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from tests.integration.conftest import apply_full_schema, asyncpg

REPO_ROOT = Path(__file__).resolve().parents[2]
DOWNLOAD_TS = REPO_ROOT / "frontend" / "lib" / "territory-brief-download.ts"


def _download_sql() -> str:
    source = DOWNLOAD_TS.read_text(encoding="utf-8")
    match = re.search(r"query\(`(.*?)`,\s*\[hash\]\)", source, re.S)
    assert match, "could not find the download SQL in territory-brief-download.ts"
    return match.group(1)


async def _consume(conn, raw_token: str):
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return await conn.fetchrow(_download_sql(), token_hash)


async def _order(conn, *, status="fulfilled", pdf="territory-briefs/o/brief.pdf", csv="territory-briefs/o/brief.csv"):
    return await conn.fetchval(
        """
        INSERT INTO territory_brief_orders
            (customer_email, stripe_price_id, scope_kind, scope_name, status,
             blob_pdf_pathname, blob_csv_pathname)
        VALUES ('buyer@example.com', 'price_acceptance', 'local_authority', 'Southampton', $1, $2, $3)
        RETURNING id
        """,
        status, pdf, csv,
    )


async def _token(conn, order_id, kind, raw, *, expires="NOW() + INTERVAL '30 days'", max_downloads=5):
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    # created_at is set in the past so that an already-expired token still satisfies
    # the table's CHECK (expires_at > created_at).
    await conn.execute(
        f"""
        INSERT INTO territory_brief_download_tokens
            (token_hash, order_id, artifact_kind, expires_at, max_downloads, created_at)
        VALUES ($1, $2, $3, {expires}, $4, NOW() - INTERVAL '40 days')
        """,
        token_hash, order_id, kind, max_downloads,
    )


@pytest.fixture
async def conn(fresh_db):
    c = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(c)
        tx = c.transaction()
        await tx.start()
        try:
            yield c
        finally:
            await tx.rollback()
    finally:
        await c.close()


TOKEN_PDF = "P" * 43
TOKEN_CSV = "C" * 43


# CG-AT-008 happy: a paid, fulfilled brief downloads as a PDF and as a CSV.
async def test_fulfilled_order_serves_pdf_and_csv_with_the_right_type(conn):
    order = await _order(conn)
    await _token(conn, order, "pdf", TOKEN_PDF)
    await _token(conn, order, "csv", TOKEN_CSV)

    pdf = await _consume(conn, TOKEN_PDF)
    csv = await _consume(conn, TOKEN_CSV)

    assert (pdf["blob_pathname"], pdf["filename"], pdf["content_type"]) == (
        "territory-briefs/o/brief.pdf", "territory-opportunity-brief.pdf", "application/pdf")
    assert (csv["blob_pathname"], csv["filename"], csv["content_type"]) == (
        "territory-briefs/o/brief.csv", "territory-opportunity-brief.csv", "text/csv; charset=utf-8")


# CG-AT-008 negative: the email promises five downloads; the sixth is refused.
async def test_sixth_download_is_refused(conn):
    order = await _order(conn)
    await _token(conn, order, "pdf", TOKEN_PDF)

    for attempt in range(5):
        assert await _consume(conn, TOKEN_PDF) is not None, f"download {attempt + 1} should be allowed"
    assert await _consume(conn, TOKEN_PDF) is None
    assert await conn.fetchval(
        "SELECT download_count FROM territory_brief_download_tokens WHERE order_id = $1", order) == 5


# CG-AT-008 negative: an expired link is refused and not counted.
async def test_expired_token_is_refused(conn):
    order = await _order(conn)
    await _token(conn, order, "pdf", TOKEN_PDF, expires="NOW() - INTERVAL '1 minute'")

    assert await _consume(conn, TOKEN_PDF) is None
    assert await conn.fetchval(
        "SELECT download_count FROM territory_brief_download_tokens WHERE order_id = $1", order) == 0


# CG-AT-008 negative: a refunded, failed or not-yet-fulfilled order never serves a file.
@pytest.mark.parametrize("status", ["pending", "paid", "generating", "failed", "expired", "refunded"])
async def test_unfulfilled_or_refunded_order_never_serves_a_file(conn, status):
    order = await _order(conn, status=status)
    await _token(conn, order, "pdf", TOKEN_PDF)

    assert await _consume(conn, TOKEN_PDF) is None


# CG-AT-008 negative: a fulfilled order whose file reference is missing serves nothing.
async def test_missing_file_reference_serves_nothing(conn):
    order = await _order(conn, pdf=None)
    await _token(conn, order, "pdf", TOKEN_PDF)

    assert await _consume(conn, TOKEN_PDF) is None


# CG-AT-008 negative: a guessed token finds nothing, and one order's token cannot open another's file.
async def test_unknown_token_is_refused_and_tokens_are_per_artifact(conn):
    order = await _order(conn)
    await _token(conn, order, "csv", TOKEN_CSV)

    assert await _consume(conn, "Z" * 43) is None
    served = await _consume(conn, TOKEN_CSV)
    assert served["blob_pathname"].endswith("brief.csv")


# CG-AT-007 contract: the delivered link lifetime and cap match the email wording.
async def test_issued_token_defaults_match_the_email_promise(conn):
    order = await _order(conn)
    await conn.execute(
        """
        INSERT INTO territory_brief_download_tokens (token_hash, order_id, artifact_kind, expires_at)
        VALUES ($1, $2, 'pdf', NOW() + INTERVAL '30 days')
        """,
        hashlib.sha256(b"x").hexdigest(), order,
    )
    row = await conn.fetchrow(
        "SELECT max_downloads, expires_at - created_at AS lifetime FROM territory_brief_download_tokens WHERE order_id = $1",
        order,
    )
    assert row["max_downloads"] == 5
    assert 29 <= row["lifetime"].days <= 30
