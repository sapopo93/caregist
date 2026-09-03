from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from tools import check_new_registration_pipeline as watchdog


@pytest.mark.asyncio
async def test_alert_state_uses_namespaced_deduplicated_upsert():
    conn = AsyncMock()

    await watchdog._record_alert(conn, "source_watermark_stale", "error", {"freshness_ok": False})

    sql, alert_key, severity, details = conn.execute.await_args.args
    assert "ON CONFLICT (alert_key) DO UPDATE" in sql
    assert "occurrence_count = pipeline_alert_state.occurrence_count + 1" in sql
    assert alert_key == "freshness_watchdog:source_watermark_stale"
    assert severity == "error"
    assert '"source": "freshness_watchdog"' in details


@pytest.mark.asyncio
async def test_existing_unresolved_alert_is_counted_without_duplicate_email(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow.return_value = {"resolved_at": None}
    send = Mock()
    monkeypatch.setattr(watchdog, "_send_email", send)

    await watchdog._notify_and_record(conn, "feed_stale", "subject", "body", {"status": "stale"})

    send.assert_not_called()
    conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolved_alert_sends_once_before_reopening(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow.return_value = {"resolved_at": "2026-08-02T10:00:00Z"}
    send = Mock()
    monkeypatch.setattr(watchdog, "_send_email", send)

    await watchdog._notify_and_record(conn, "feed_stale", "subject", "body", {"status": "stale"})

    send.assert_called_once_with("subject", "body")
    conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_delivery_does_not_suppress_the_next_notification(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    monkeypatch.setattr(
        watchdog,
        "_send_email",
        Mock(side_effect=RuntimeError("delivery unavailable")),
    )

    with pytest.raises(RuntimeError, match="delivery unavailable"):
        await watchdog._notify_and_record(
            conn, "feed_stale", "subject", "body", {"status": "stale"}
        )

    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_recovery_resolves_only_watchdog_alerts():
    conn = AsyncMock()

    await watchdog._resolve_watchdog_alerts(conn)

    sql, pattern = conn.execute.await_args.args
    assert "resolved_at = NOW()" in sql
    assert pattern == "freshness_watchdog:%"


def test_alert_recipient_defaults_to_operations_address(monkeypatch):
    for key in ("PIPELINE_ALERT_EMAIL", "MONITOR_ALERT_FAILURE_EMAIL", "ENQUIRY_FROM_EMAIL"):
        monkeypatch.delenv(key, raising=False)

    assert watchdog._alert_email_to() == "ops@caregist.co.uk"
