-- CareGist Growth Features Migration
-- Run once against the production database
-- Creates tables for: analytics, email subscribers, saved comparisons,
-- provider monitors, rating history, API applications, email queue, postcode cache

-- 1. Analytics events (cross-cutting)
CREATE TABLE IF NOT EXISTS analytics_events (
  id BIGSERIAL PRIMARY KEY,
  event_type VARCHAR(50) NOT NULL,
  event_source VARCHAR(50),
  user_id INT REFERENCES users(id) ON DELETE SET NULL,
  email VARCHAR(255),
  provider_id VARCHAR(20),
  meta JSONB DEFAULT '{}',
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ae_type ON analytics_events (event_type);
CREATE INDEX IF NOT EXISTS idx_ae_created ON analytics_events (created_at);

-- 2. Email subscribers (Tasks 1, 7, 8)
CREATE TABLE IF NOT EXISTS email_subscribers (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  source VARCHAR(50) NOT NULL DEFAULT 'homepage',
  postcode VARCHAR(10),
  meta JSONB DEFAULT '{}',
  unsubscribed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(email, source)
);
CREATE INDEX IF NOT EXISTS idx_es_email ON email_subscribers (email);

-- 3. Saved comparisons (Task 3)
CREATE TABLE IF NOT EXISTS saved_comparisons (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  share_token VARCHAR(32) UNIQUE NOT NULL,
  slug_list TEXT[] NOT NULL,
  title VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sc_user ON saved_comparisons (user_id);
CREATE INDEX IF NOT EXISTS idx_sc_token ON saved_comparisons (share_token);

-- 4. Provider monitors (Task 4)
CREATE TABLE IF NOT EXISTS provider_monitors (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  provider_id VARCHAR(20) NOT NULL REFERENCES care_providers(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, provider_id)
);
CREATE INDEX IF NOT EXISTS idx_pm_user ON provider_monitors (user_id);
CREATE INDEX IF NOT EXISTS idx_pm_provider ON provider_monitors (provider_id);

-- 5. Provider rating history (Task 4)
CREATE TABLE IF NOT EXISTS provider_rating_history (
  id SERIAL PRIMARY KEY,
  provider_id VARCHAR(20) NOT NULL REFERENCES care_providers(id),
  overall_rating VARCHAR(50),
  inspection_date DATE,
  report_url VARCHAR(500),
  recorded_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(provider_id, inspection_date)
);
CREATE INDEX IF NOT EXISTS idx_prh_provider ON provider_rating_history (provider_id);

-- 6. Alter provider_claims (Task 5)
ALTER TABLE provider_claims ADD COLUMN IF NOT EXISTS fast_track BOOLEAN DEFAULT false;
ALTER TABLE provider_claims ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ DEFAULT NOW();

-- 7. API applications (Task 6)
CREATE TABLE IF NOT EXISTS api_applications (
  id SERIAL PRIMARY KEY,
  company_name VARCHAR(255) NOT NULL,
  contact_name VARCHAR(255) NOT NULL,
  contact_email VARCHAR(255) NOT NULL,
  use_case TEXT NOT NULL,
  expected_volume VARCHAR(50),
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  reviewed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_aa_status ON api_applications (status);

-- 8. Pending emails queue (lightweight async email)
CREATE TABLE IF NOT EXISTS pending_emails (
  id SERIAL PRIMARY KEY,
  to_email VARCHAR(255) NOT NULL,
  subject VARCHAR(500) NOT NULL,
  html_body TEXT NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  attempts INT DEFAULT 0,
  processing_started_at TIMESTAMPTZ,
  send_after TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  sent_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_pe_status ON pending_emails (status, send_after);
CREATE INDEX IF NOT EXISTS idx_pe_processing ON pending_emails (status, processing_started_at);

-- 9. Postcode geocode cache (Task 7)
CREATE TABLE IF NOT EXISTS postcode_cache (
  postcode VARCHAR(10) PRIMARY KEY,
  latitude DECIMAL(10,7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Seed initial rating history from current provider data
INSERT INTO provider_rating_history (provider_id, overall_rating, inspection_date)
SELECT id, overall_rating, last_inspection_date
FROM care_providers
WHERE overall_rating IS NOT NULL AND last_inspection_date IS NOT NULL
ON CONFLICT (provider_id, inspection_date) DO NOTHING;
