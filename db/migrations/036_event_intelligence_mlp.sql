-- Event-intelligence MLP additive schema.
-- G1 note: generated only; apply to staging/production requires APPROVED_MIGRATION.

CREATE TABLE IF NOT EXISTS cqc_snapshots (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL CHECK (source IN ('bulk', 'api')),
  captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_file_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'completed',
  row_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cqc_provider_snapshots (
  snapshot_id BIGINT NOT NULL REFERENCES cqc_snapshots(id) ON DELETE CASCADE,
  cqc_provider_id TEXT NOT NULL,
  name TEXT,
  registration_status TEXT,
  registration_date DATE,
  linked_org_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  row_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (snapshot_id, cqc_provider_id)
);

CREATE TABLE IF NOT EXISTS cqc_location_snapshots (
  snapshot_id BIGINT NOT NULL REFERENCES cqc_snapshots(id) ON DELETE CASCADE,
  cqc_location_id TEXT NOT NULL,
  cqc_provider_id TEXT,
  name TEXT,
  registration_status TEXT,
  registration_date DATE,
  region TEXT,
  local_authority TEXT,
  service_types JSONB NOT NULL DEFAULT '[]'::jsonb,
  regulated_activities JSONB NOT NULL DEFAULT '[]'::jsonb,
  specialisms JSONB NOT NULL DEFAULT '[]'::jsonb,
  bed_count INT,
  latest_rating TEXT,
  rating_publication_date DATE,
  is_archived BOOLEAN NOT NULL DEFAULT FALSE,
  row_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (snapshot_id, cqc_location_id)
);

CREATE TABLE IF NOT EXISTS market_events (
  id BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('provider', 'location', 'group')),
  subject_id TEXT NOT NULL,
  occurred_at DATE NOT NULL,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  snapshot_id BIGINT REFERENCES cqc_snapshots(id) ON DELETE SET NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  dedup_key TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_events_type_occurred
  ON market_events (event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_events_subject
  ON market_events (subject_type, subject_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS location_signals (
  subject_id TEXT PRIMARY KEY,
  score_version TEXT NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  inspection_age_score INT NOT NULL CHECK (inspection_age_score BETWEEN 0 AND 100),
  rating_limbo_score INT NOT NULL CHECK (rating_limbo_score BETWEEN 0 AND 100),
  supplier_lead_score INT NOT NULL CHECK (supplier_lead_score BETWEEN 0 AND 100),
  inputs JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_location_signals_supplier_lead
  ON location_signals (supplier_lead_score DESC, computed_at DESC);
