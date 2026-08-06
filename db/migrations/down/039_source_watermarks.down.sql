DROP INDEX IF EXISTS idx_pipeline_runs_source_published;
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_source_checksum_sha256;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS active_records_after;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS active_records_before;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS source_record_count;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS source_checksum_sha256;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS source_retrieved_at;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS source_published_at;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS source_uri;
