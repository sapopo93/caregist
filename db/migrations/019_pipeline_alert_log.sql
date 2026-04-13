-- Deduplicate operational pipeline alerts.

CREATE TABLE IF NOT EXISTS pipeline_alert_log (
  id BIGSERIAL PRIMARY KEY,
  alert_key TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'error',
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_alert_log_key_created
  ON pipeline_alert_log (alert_key, created_at DESC);
