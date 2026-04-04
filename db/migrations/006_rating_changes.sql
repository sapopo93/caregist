-- Rating changes tracking for weekly movers email
CREATE TABLE IF NOT EXISTS rating_changes (
  id SERIAL PRIMARY KEY,
  provider_id VARCHAR(20) NOT NULL,
  provider_name TEXT,
  slug TEXT,
  town TEXT,
  postcode VARCHAR(10),
  region TEXT,
  old_rating VARCHAR(50),
  new_rating VARCHAR(50),
  inspection_date DATE,
  detected_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rc_detected ON rating_changes (detected_at);
CREATE INDEX IF NOT EXISTS idx_rc_region ON rating_changes (region);
CREATE INDEX IF NOT EXISTS idx_rc_postcode ON rating_changes (postcode);

-- Weekly digest log to prevent duplicate sends
CREATE TABLE IF NOT EXISTS weekly_digest_log (
  id SERIAL PRIMARY KEY,
  week_key VARCHAR(10) NOT NULL,
  subscriber_count INT DEFAULT 0,
  emails_queued INT DEFAULT 0,
  changes_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(week_key)
);
