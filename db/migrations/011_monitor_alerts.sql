-- Add last_alert_sent_at watermark to provider_monitors
-- Used by send_monitor_alerts.py to track which changes have been dispatched per user
ALTER TABLE provider_monitors ADD COLUMN IF NOT EXISTS last_alert_sent_at TIMESTAMPTZ;
