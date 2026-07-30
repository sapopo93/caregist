"""Regression tests for the monitor alert cron script."""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from tools import send_monitor_alerts


def test_alerts_pro_receives_monitor_alert_emails_without_webhooks():
    assert "alerts-pro" in send_monitor_alerts.ALERT_TIERS
    assert "alerts-pro" not in send_monitor_alerts.WEBHOOK_TIERS


def test_monitor_alerts_read_rating_changes_table():
    source = inspect.getsource(send_monitor_alerts.run)

    assert "FROM rating_changes rc" in source
    assert "rc.old_rating" in source
    assert "rc.new_rating" in source
    assert "rc.detected_at" in source


def test_monitor_alert_dry_run_crosses_db_boundary_without_writes_or_delivery(monkeypatch, capsys):
    monitor = {
        "monitor_id": 5,
        "user_id": 7,
        "provider_id": "LOC1",
        "created_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
        "last_alert_sent_at": None,
        "email": "proof@example.invalid",
        "user_name": "Proof User",
        "tier": "business",
        "provider_name": "Alpha Care",
        "town": "London",
        "slug": "alpha-care",
        "current_rating": "Outstanding",
    }
    rating_change = {
        "provider_id": "LOC1",
        "previous_rating": "Good",
        "new_rating": "Outstanding",
        "changed_at": datetime(2026, 7, 29, tzinfo=timezone.utc),
    }

    class ControlledCursor:
        def __init__(self):
            self.rows = []

        def execute(self, sql, params=None):
            if "FROM provider_monitors" in sql:
                self.rows = [monitor]
            elif "FROM rating_changes" in sql:
                self.rows = [rating_change]
            else:
                raise AssertionError(f"dry run attempted a write or unexpected query: {sql}")

        def fetchall(self):
            return self.rows

    cursor = ControlledCursor()
    conn = Mock()
    conn.cursor.return_value = cursor
    monkeypatch.setattr(send_monitor_alerts, "get_database_url", lambda: "postgresql://proof.invalid/db")
    monkeypatch.setattr(send_monitor_alerts, "get_connection", lambda _url: conn)

    send_monitor_alerts.run(dry_run=True)

    output = capsys.readouterr().out
    assert "[DRY RUN] Would send to proof@example.invalid" in output
    assert "Would deliver webhooks" in output
    conn.commit.assert_not_called()
    conn.close.assert_called_once()


def test_monitor_watermark_update_contains_one_where_clause():
    source = inspect.getsource(send_monitor_alerts.run)
    update = source.split("UPDATE provider_monitors", 1)[1].split('"""', 1)[0]
    assert update.count("WHERE") == 1


def test_monitor_email_escapes_provider_and_user_content():
    rendered = send_monitor_alerts.build_email_html(
        '<img src=x onerror="alert(1)">',
        [{
            "name": "<script>alert(1)</script>",
            "town": "<b>Town</b>",
            "slug": 'bad\" onclick=\"alert(1)',
            "previous_rating": "Good",
            "new_rating": "Outstanding",
        }],
    )

    assert "<script>" not in rendered
    assert "<img src=x" not in rendered
    assert "onclick=\"alert" not in rendered
def test_monitor_delivery_fails_closed_before_database_access(monkeypatch):
    monkeypatch.delenv("OUTBOUND_DELIVERY_ENABLED", raising=False)
    monkeypatch.setattr(
        send_monitor_alerts,
        "get_database_url",
        lambda: (_ for _ in ()).throw(AssertionError("database must not be accessed")),
    )

    with pytest.raises(RuntimeError, match="Human Gate"):
        send_monitor_alerts.run(dry_run=False)
