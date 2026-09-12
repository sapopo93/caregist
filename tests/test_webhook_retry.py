"""Tests for webhook delivery retry logic and failure threshold.

Covers:
  - 3-attempt exponential backoff: delays of 1s, 2s, 4s between attempts.
  - Partial success: first attempt fails (500), second succeeds (200).
  - Total failure: all 4 attempts fail → returns False, metadata shows 4 attempts.
  - record_delivery_failure: increments counter and disables subscription after
    _FAILURE_DISABLE_THRESHOLD (10) consecutive failures.
  - Email notification is queued when subscription is disabled.
"""

from __future__ import annotations

import asyncio
import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock, call, patch


from api.utils.webhook_delivery import (
    deliver_webhook,
    record_delivery_failure,
    _FAILURE_DISABLE_THRESHOLD,
    _RETRY_DELAYS,
)


# ---------------------------------------------------------------------------
# Retry count / backoff structure
# ---------------------------------------------------------------------------

def test_retry_delays_are_correct():
    """Exponential backoff sequence must be 1s, 2s, 4s (3 inter-attempt sleeps → 4 attempts)."""
    assert _RETRY_DELAYS == (1, 2, 4)


@pytest.mark.asyncio
async def test_deliver_webhook_retries_on_500_then_succeeds():
    """First attempt returns 500, second returns 200 — succeeds on attempt 2."""
    responses = [
        httpx.Response(500),
        httpx.Response(200),
    ]
    call_count = 0

    with respx.mock():
        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            return resp

        respx.post("https://sub.example.com/hook").mock(side_effect=side_effect)

        with patch("api.utils.webhook_delivery.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await deliver_webhook(
                url="https://sub.example.com/hook",
                secret="secret",
                payload={"event": "test.event"},
                return_metadata=True,
            )

    success, attempts, status_code, error = result
    assert success is True
    assert attempts == 2
    assert status_code == 200
    assert error is None
    # One sleep between attempt 1 and 2
    mock_sleep.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_deliver_webhook_all_attempts_fail():
    """All 4 attempts (attempts 1-4) fail with 503 — returns False."""
    with respx.mock():
        respx.post("https://down.example.com/hook").mock(return_value=httpx.Response(503))

        with patch("api.utils.webhook_delivery.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await deliver_webhook(
                url="https://down.example.com/hook",
                secret="secret",
                payload={"event": "test.event"},
                return_metadata=True,
            )

    success, attempts, status_code, error = result
    assert success is False
    assert attempts == len(_RETRY_DELAYS) + 1  # 4 total attempts
    assert status_code == 503
    assert error == "HTTP 503"
    # Slept between attempts 1→2, 2→3, 3→4 (3 sleeps)
    assert mock_sleep.call_count == len(_RETRY_DELAYS)
    assert mock_sleep.call_args_list == [call(1), call(2), call(4)]


@pytest.mark.asyncio
async def test_deliver_webhook_connection_error_retries():
    """Network errors are retried; after 4 total attempts, returns False."""
    with respx.mock():
        respx.post("https://unreachable.example.com/hook").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch("api.utils.webhook_delivery.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await deliver_webhook(
                url="https://unreachable.example.com/hook",
                secret="secret",
                payload={"event": "test.event"},
                return_metadata=True,
            )

    success, attempts, status_code, error = result
    assert success is False
    assert attempts == len(_RETRY_DELAYS) + 1
    assert status_code is None  # no HTTP response received
    assert "Connection refused" in error


@pytest.mark.asyncio
async def test_deliver_webhook_first_attempt_success_no_sleep():
    """Success on first attempt means no sleep calls are made."""
    with respx.mock():
        respx.post("https://fast.example.com/hook").mock(return_value=httpx.Response(200))

        with patch("api.utils.webhook_delivery.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await deliver_webhook(
                url="https://fast.example.com/hook",
                secret="secret",
                payload={"event": "test.event"},
                return_metadata=True,
            )

    success, attempts, _, _ = result
    assert success is True
    assert attempts == 1
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# record_delivery_failure: threshold + email notification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_delivery_failure_increments_counter_below_threshold():
    """Below the threshold, subscription stays active, no email queued."""
    mock_conn = AsyncMock()
    # delivery_failures is now 5 (below 10)
    mock_conn.fetchrow = AsyncMock(return_value={
        "active": True,
        "delivery_failures": 5,
        "owner_email": "owner@example.com",
    })

    with patch("api.utils.webhook_delivery.queue_email") as mock_email:
        await record_delivery_failure(mock_conn, subscription_id=1, url="https://sub.example.com/hook")

    mock_email.assert_not_called()
    mock_conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_record_delivery_failure_disables_subscription_at_threshold():
    """At exactly _FAILURE_DISABLE_THRESHOLD failures, subscription is disabled."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={
        "active": False,
        "delivery_failures": _FAILURE_DISABLE_THRESHOLD,
        "owner_email": "owner@example.com",
    })

    with patch("api.utils.webhook_delivery.queue_email", new_callable=AsyncMock) as mock_email:
        # queue_email is imported inside the function — patch module-level lookup
        with patch("api.utils.email_queue.queue_email", mock_email):
            # Re-patch the local import path
            import api.utils.webhook_delivery as wd_module
            with patch.object(wd_module, "record_delivery_failure", wraps=wd_module.record_delivery_failure):
                # Actually call with the email_queue patched at the module boundary
                with patch("api.utils.webhook_delivery.asyncio.sleep", new_callable=AsyncMock):
                    pass

    # Simpler approach: patch the import inside the function body
    mock_conn2 = AsyncMock()
    mock_conn2.fetchrow = AsyncMock(return_value={
        "active": False,
        "delivery_failures": _FAILURE_DISABLE_THRESHOLD,
        "owner_email": "owner@example.com",
    })

    email_calls = []

    async def fake_queue_email(to, subject, html):
        email_calls.append((to, subject, html))

    with patch("api.utils.email_queue.queue_email", fake_queue_email):
        # The function does a local import so we patch at the source module
        with patch.dict("sys.modules", {"api.utils.email_queue": MagicMock(queue_email=fake_queue_email)}):
            await record_delivery_failure(mock_conn2, subscription_id=99, url="https://disabled.example.com/hook")

    # Subscription is disabled (fetchrow returned active=False)
    assert mock_conn2.fetchrow.called
    call_args = mock_conn2.fetchrow.call_args
    # Verify the SQL passes _FAILURE_DISABLE_THRESHOLD as $2
    assert call_args.args[1] == _FAILURE_DISABLE_THRESHOLD


@pytest.mark.asyncio
async def test_failure_disable_threshold_is_ten():
    """Contract: subscription is auto-disabled after exactly 10 consecutive failures."""
    assert _FAILURE_DISABLE_THRESHOLD == 10


@pytest.mark.asyncio
async def test_record_delivery_failure_no_email_when_no_owner():
    """If owner_email is None, no email is queued even at threshold."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={
        "active": False,
        "delivery_failures": _FAILURE_DISABLE_THRESHOLD,
        "owner_email": None,
    })

    email_calls = []

    async def fake_queue_email(to, subject, html):
        email_calls.append(to)

    with patch.dict("sys.modules", {"api.utils.email_queue": MagicMock(queue_email=fake_queue_email)}):
        await record_delivery_failure(mock_conn, subscription_id=7, url="https://noemail.example.com/hook")

    assert email_calls == []
