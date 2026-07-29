CREATE TABLE IF NOT EXISTS leads (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  region TEXT NOT NULL DEFAULT '',
  service_type TEXT NOT NULL DEFAULT '',
  rating TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads (email);

CREATE TABLE IF NOT EXISTS export_access_tokens (
  token TEXT PRIMARY KEY,
  lead_id BIGINT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  region TEXT NOT NULL DEFAULT '',
  service_type TEXT NOT NULL DEFAULT '',
  rating TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days',
  last_downloaded_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_export_access_tokens_expires_at
  ON export_access_tokens (expires_at);
