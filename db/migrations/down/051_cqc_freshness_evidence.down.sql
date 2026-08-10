DROP INDEX IF EXISTS idx_pipeline_runs_cqc_watermark;
DROP INDEX IF EXISTS idx_pipeline_runs_cqc_attempts;

ALTER TABLE trusted_event_ledger DROP COLUMN IF EXISTS effective_date_source;
ALTER TABLE trusted_event_ledger DROP COLUMN IF EXISTS effective_at;
-- effective_date intentionally remains nullable: restoring NOT NULL could fail
-- after truthful events without a CQC-published effective date are recorded.

ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_run_count_consistency;
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_run_failure_count;
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_run_success_count;
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_run_checked_count;
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_run_collection_counts;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS counts_reconciled;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS reconciled_at;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS checkpoint_state;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS source_provenance;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS failure_count;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS success_count;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS checked_count;
ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS source_total_count;
