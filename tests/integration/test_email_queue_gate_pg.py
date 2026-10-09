"""Closed marketing preserves pending mail and permits verified paid delivery."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import asyncpg

from api.utils import email_queue
from tests.integration.conftest import apply_full_schema


async def test_closed_outbound_sends_only_actual_fulfilled_order_email(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        orders = {}
        for label, status in (("fulfilled", "fulfilled"), ("wrong_recipient", "fulfilled"),
                              ("paid", "paid"), ("refunded", "refunded")):
            orders[label] = await conn.fetchval(
                """INSERT INTO territory_brief_orders
                   (customer_email, stripe_price_id, scope_kind, scope_name, status)
                   VALUES ('buyer@example.com', 'price_test', 'local_authority', 'Southampton', $1)
                   RETURNING id""", status,
            )
        for address, key in [
            ("buyer@example.com", f"territory-brief-delivery:{orders['fulfilled']}"),
            ("buyer@example.com", "marketing:delayed"),
            ("other@example.com", f"territory-brief-delivery:{orders['fulfilled']}-forged"),
            ("other@example.com", f"territory-brief-delivery:{orders['wrong_recipient']}"),
            ("buyer@example.com", f"territory-brief-delivery:{orders['paid']}"),
            ("buyer@example.com", f"territory-brief-delivery:{orders['refunded']}"),
        ]:
            await conn.execute(
                """INSERT INTO pending_emails (to_email, subject, html_body, idempotency_key)
                   VALUES ($1, 'Synthetic test', '<p>Fixture</p>', $2)""", address, key,
            )

        @asynccontextmanager
        async def connection():
            yield conn

        monkeypatch.setattr(email_queue, "get_connection", connection)
        monkeypatch.setattr(email_queue.settings, "outbound_communications_enabled", False)
        monkeypatch.setattr(email_queue.settings, "resend_api_key", "re_synthetic")
        client = AsyncMock()
        client.__aenter__.return_value = client
        response = client.post.return_value
        response.status_code = 200
        response.json = lambda: {"id": "synthetic-message"}
        with patch("httpx.AsyncClient", return_value=client):
            assert await email_queue.process_email_queue() == 1
        assert client.post.await_count == 1
        assert client.post.await_args.kwargs["json"]["to"] == ["buyer@example.com"]
        rows = await conn.fetch("SELECT status, attempts FROM pending_emails ORDER BY id")
        assert [r["status"] for r in rows] == ["sent"] + ["pending"] * 5
        assert all(r["attempts"] == 0 for r in rows)

        late_order = await conn.fetchval(
            """INSERT INTO territory_brief_orders
               (customer_email, stripe_price_id, scope_kind, scope_name, status)
               VALUES ('buyer@example.com', 'price_test', 'local_authority', 'Southampton', 'fulfilled')
               RETURNING id""",
        )
        late_email = await conn.fetchval(
            """INSERT INTO pending_emails (to_email, subject, html_body, idempotency_key)
               VALUES ('buyer@example.com', 'Synthetic late refund', '<p>Fixture</p>', $1)
               RETURNING id""", f"territory-brief-delivery:{late_order}",
        )
        claim = email_queue._claim_pending_emails

        async def refund_after_claim(connection, batch_size):
            claimed = await claim(connection, batch_size)
            assert [row["id"] for row in claimed] == [late_email]
            await connection.execute("UPDATE territory_brief_orders SET status = 'refunded' WHERE id = $1", late_order)
            return claimed

        monkeypatch.setattr(email_queue, "_claim_pending_emails", refund_after_claim)
        with patch("httpx.AsyncClient", return_value=client):
            assert await email_queue.process_email_queue() == 0
        assert client.post.await_count == 1  # No second external request.
        deferred = await conn.fetchrow(
            "SELECT status, attempts, processing_started_at FROM pending_emails WHERE id = $1", late_email,
        )
        assert deferred["status"] == "pending" and deferred["attempts"] == 0
        assert deferred["processing_started_at"] is None
    finally:
        await conn.close()
