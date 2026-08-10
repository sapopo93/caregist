-- Evidence-backed CQC collection coverage and truthful change timing.
-- Additive/forward-only: historical rows remain readable, but only completed
-- reconciliations may act as source-freshness watermarks.

ALTER TABLE pipeline_runs
  ADD COLUMN IF NOT EXISTS source_total_count INT,
  ADD COLUMN IF NOT EXISTS checked_count INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS success_count INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS failure_count INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS source_provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS checkpoint_state JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS reconciled_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS counts_reconciled BOOLEAN;

ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_run_collection_counts;
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_run_collection_counts CHECK (
  source_total_count IS NULL OR source_total_count >= 0
);
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_run_checked_count
  CHECK (checked_count >= 0);
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_run_success_count
  CHECK (success_count >= 0);
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_run_failure_count
  CHECK (failure_count >= 0);
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_run_count_consistency CHECK (
  success_count + failure_count <= checked_count
  AND (source_total_count IS NULL OR checked_count <= source_total_count)
);

-- CQC does not always publish an effective date for a material transition.
-- NULL means "not published"; observed_at remains CareGist's first persisted
-- observation and must never be substituted for an effective date.
ALTER TABLE trusted_event_ledger ALTER COLUMN effective_date DROP NOT NULL;
ALTER TABLE trusted_event_ledger
  ADD COLUMN IF NOT EXISTS effective_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS effective_date_source TEXT;

COMMENT ON COLUMN trusted_event_ledger.effective_date IS
  'CQC-published effective date, when explicitly supplied; never inferred.';
COMMENT ON COLUMN trusted_event_ledger.effective_at IS
  'CQC-published effective timestamp, when explicitly supplied; never inferred.';
COMMENT ON COLUMN trusted_event_ledger.observed_at IS
  'UTC time CareGist first successfully persisted this deduplicated material change.';
COMMENT ON COLUMN pipeline_runs.reconciled_at IS
  'Completion time of count reconciliation; populated only for a successful authoritative run.';

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_cqc_attempts
  ON pipeline_runs (COALESCE(completed_at, started_at) DESC)
  WHERE run_type IN ('signal_poll', 'incremental', 'reconciliation');

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_cqc_watermark
  ON pipeline_runs (source_retrieved_at DESC)
  WHERE run_type = 'reconciliation'
    AND status = 'completed'
    AND counts_reconciled = TRUE
    AND reconciled_at IS NOT NULL;
