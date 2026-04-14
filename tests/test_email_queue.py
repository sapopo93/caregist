from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from api.utils import email_queue


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


def test_next_failure_status_switches_to_failed_on_third_attempt():
    assert email_queue._next_failure_status(0) == "pending"
    assert email_queue._next_failure_status(1) == "pending"
    assert email_queue._next_failure_status(2) == "failed"
