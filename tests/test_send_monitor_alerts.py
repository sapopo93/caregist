"""Regression tests for the monitor alert cron script."""

from __future__ import annotations

import inspect

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
