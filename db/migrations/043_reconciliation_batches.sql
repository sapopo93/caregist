-- Authoritative, resumable CQC reconciliation batches.
-- Migration number 034 is intentionally reserved by the two historic applied files.

CREATE TABLE IF NOT EXISTS reconciliation_batches (
  id UUID PRIMARY KEY,
  pipeline_run_id BIGINT UNIQUE REFERENCES pipeline_runs(id),
  source_uri TEXT NOT NULL,
  source_published_at DATE NOT NULL,
  source_retrieved_at TIMESTAMPTZ NOT NULL,
  source_checksum_sha256 CHAR(64) NOT NULL,
  manifest_checksum_sha256 CHAR(64) NOT NULL,
  location_count INT NOT NULL CHECK (location_count > 0),
  shard_count INT NOT NULL CHECK (shard_count > 0),
  status TEXT NOT NULL CHECK (status IN ('prepared', 'running', 'failed', 'completed')),
  active_records_before INT NOT NULL,
  active_records_after INT,
  records_inserted INT NOT NULL DEFAULT 0,
  records_updated INT NOT NULL DEFAULT 0,
  records_deactivated INT NOT NULL DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  CHECK (source_checksum_sha256 ~ '^[0-9a-f]{64}$'),
  CHECK (manifest_checksum_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS reconciliation_shards (
  batch_id UUID NOT NULL REFERENCES reconciliation_batches(id) ON DELETE RESTRICT,
  shard_index INT NOT NULL CHECK (shard_index >= 0),
  status TEXT NOT NULL CHECK (status IN ('running', 'failed', 'completed')),
  manifest_checksum_sha256 CHAR(64) NOT NULL,
  expected_count INT NOT NULL CHECK (expected_count >= 0),
  next_offset INT NOT NULL DEFAULT 0 CHECK (next_offset >= 0),
  processed_count INT NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
  records_inserted INT NOT NULL DEFAULT 0,
  records_updated INT NOT NULL DEFAULT 0,
  fetch_failures INT NOT NULL DEFAULT 0,
  clean_failures INT NOT NULL DEFAULT 0,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  error_message TEXT,
  PRIMARY KEY (batch_id, shard_index),
  CHECK (manifest_checksum_sha256 ~ '^[0-9a-f]{64}$'),
  CHECK (next_offset <= expected_count),
  CHECK (processed_count <= expected_count)
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_batches_status_created
  ON reconciliation_batches (status, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_one_active_reconciliation_batch
  ON reconciliation_batches ((1))
  WHERE status IN ('prepared', 'running');

CREATE OR REPLACE FUNCTION enforce_reconciliation_shard_index()
RETURNS TRIGGER AS $$
DECLARE
  configured_shards INT;
BEGIN
  SELECT shard_count INTO configured_shards FROM reconciliation_batches WHERE id = NEW.batch_id;
  IF configured_shards IS NULL OR NEW.shard_index >= configured_shards THEN
    RAISE EXCEPTION 'shard index % is outside batch shard count %', NEW.shard_index, configured_shards;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reconciliation_shard_index ON reconciliation_shards;
CREATE TRIGGER trg_reconciliation_shard_index
BEFORE INSERT OR UPDATE OF shard_index, batch_id ON reconciliation_shards
FOR EACH ROW EXECUTE FUNCTION enforce_reconciliation_shard_index();

CREATE TABLE IF NOT EXISTS pipeline_alert_state (
  alert_key TEXT PRIMARY KEY,
  severity TEXT NOT NULL,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  occurrence_count BIGINT NOT NULL DEFAULT 1 CHECK (occurrence_count > 0),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pipeline_alert_state_unresolved
  ON pipeline_alert_state (last_seen_at DESC)
  WHERE resolved_at IS NULL;
