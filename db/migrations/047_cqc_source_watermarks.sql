-- Trace the exact authoritative CQC source promoted by a completed reconciliation.

ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS source_uri TEXT;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS source_published_at DATE;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS source_retrieved_at TIMESTAMPTZ;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS source_checksum_sha256 CHAR(64);
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS source_record_count INT;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS active_records_before INT;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS active_records_after INT;

ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_source_checksum_sha256;
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_source_checksum_sha256
  CHECK (
    source_checksum_sha256 IS NULL
    OR source_checksum_sha256 ~ '^[0-9a-f]{64}$'
  );

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source_published
  ON pipeline_runs (source_published_at DESC, completed_at DESC)
  WHERE status = 'completed' AND source_published_at IS NOT NULL;
