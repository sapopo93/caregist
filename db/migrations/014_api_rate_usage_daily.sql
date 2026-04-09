CREATE TABLE IF NOT EXISTS api_rate_usage_daily (
  api_key VARCHAR(64) NOT NULL,
  usage_date DATE NOT NULL,
  request_count INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (api_key, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_api_rate_usage_daily_date ON api_rate_usage_daily (usage_date);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_active ON api_keys (user_id, is_active);
