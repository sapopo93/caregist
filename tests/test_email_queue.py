from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from api.utils import email_queue


@pytest.fixture(autouse=True)
def outbound_open(monkeypatch):
    monkeypatch.setattr(email_queue.settings, "outbound_communications_enabled", True)


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeAsyncClient:
    def __init__(self, response_status: int):
        self._response_status = response_status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse(self._response_status)


@pytest.mark.asyncio
async def test_process_email_queue_marks_terminal_failures_as_failed():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.email_queue.get_connection", mock_get_connection), \
         patch("api.utils.email_queue._claim_pending_emails", new=AsyncMock(return_value=[
             {
                 "id": 99,
                 "to_email": "ops@caregist.co.uk",
                 "subject": "Digest",
                 "html_body": "<p>Hello</p>",
                 "attempts": 2,
             }
         ])), \
         patch("httpx.AsyncClient", return_value=_FakeAsyncClient(500)), \
         patch.object(email_queue.settings, "resend_api_key", "re_test"), \
         patch.object(email_queue.settings, "enquiry_from_email", "noreply@caregist.co.uk"):
        sent = await email_queue.process_email_queue(batch_size=1)

    assert sent == 0
    assert conn.execute.await_count == 1
    args = conn.execute.await_args.args
    assert "status = $2" in args[0]
    assert args[1] == 99
    assert args[2] == "failed"


@pytest.mark.asyncio
async def test_process_email_queue_reschedules_non_terminal_failures_with_backoff():
    conn = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.utils.email_queue.get_connection", mock_get_connection), \
         patch("api.utils.email_queue._claim_pending_emails", new=AsyncMock(return_value=[
             {
                 "id": 100,
                 "to_email": "ops@caregist.co.uk",
                 "subject": "Digest",
                 "html_body": "<p>Hello</p>",
                 "attempts": 0,
             }
         ])), \
         patch("httpx.AsyncClient", return_value=_FakeAsyncClient(500)), \
         patch.object(email_queue.settings, "resend_api_key", "re_test"), \
         patch.object(email_queue.settings, "enquiry_from_email", "noreply@caregist.co.uk"):
        sent = await email_queue.process_email_queue(batch_size=1)

    assert sent == 0
    args = conn.execute.await_args.args
    assert "send_after = NOW() + make_interval(secs => $3)" in args[0]
    assert args[1] == 100
    assert args[2] == "pending"
    assert args[3] == 300


@pytest.mark.asyncio
async def test_process_email_queue_sends_stable_provider_idempotency_key():
    conn = AsyncMock()
    captured: dict = {}

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    class SuccessResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "provider-message-1"}

    class CapturingClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            captured.update(kwargs)
            return SuccessResponse()

    with patch("api.utils.email_queue.get_connection", mock_get_connection), \
         patch("api.utils.email_queue._claim_pending_emails", new=AsyncMock(return_value=[
             {
                 "id": 101,
                 "to_email": "ops@caregist.co.uk",
                 "subject": "Campaign",
                 "html_body": "<p>Hello</p>",
                 "attempts": 0,
                 "idempotency_key": "crm-campaign:stable-delivery",
             }
         ])), \
         patch("httpx.AsyncClient", CapturingClient), \
         patch.object(email_queue.settings, "resend_api_key", "re_test"), \
         patch.object(email_queue.settings, "enquiry_from_email", "noreply@caregist.co.uk"):
        sent = await email_queue.process_email_queue(batch_size=1)

    assert sent == 1
    assert captured["headers"]["Idempotency-Key"] == "crm-campaign:stable-delivery"
    update_args = conn.execute.await_args.args
    assert update_args[1:] == (101, "provider-message-1")


def test_next_failure_status_switches_to_failed_on_third_attempt():
    assert email_queue._next_failure_status(0) == "pending"
    assert email_queue._next_failure_status(1) == "pending"
    assert email_queue._next_failure_status(2) == "failed"


@pytest.mark.asyncio
async def test_closed_outbound_preserves_pending_queue_without_claiming(monkeypatch):
    monkeypatch.setattr(email_queue.settings, "outbound_communications_enabled", False)
    monkeypatch.setattr(email_queue.settings, "resend_api_key", "re_synthetic")
    with patch.object(email_queue, "get_connection") as db, \
         patch("httpx.AsyncClient") as sender:
        assert await email_queue.process_email_queue() == 0
    db.assert_not_called()
    sender.assert_not_called()


@pytest.mark.asyncio
async def test_outbound_closed_after_claim_defers_without_spending_retry(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(email_queue.settings, "resend_api_key", "re_synthetic")

    @asynccontextmanager
    async def connection():
        yield conn

    async def claim(*args):
        monkeypatch.setattr(email_queue.settings, "outbound_communications_enabled", False)
        return [{"id": 102}]

    client = AsyncMock()
    client.__aenter__.return_value = client
    monkeypatch.setattr(email_queue, "get_connection", connection)
    monkeypatch.setattr(email_queue, "_claim_pending_emails", claim)
    with patch("httpx.AsyncClient", return_value=client):
        assert await email_queue.process_email_queue() == 0
    client.post.assert_not_awaited()
    sql, row_id = conn.execute.await_args.args
    assert row_id == 102
    assert "status = 'pending'" in sql
    assert "processing_started_at = NULL" in sql
    assert "attempts" not in sql and "send_after" not in sql
