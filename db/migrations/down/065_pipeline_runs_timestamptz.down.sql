-- Reverses 065_pipeline_runs_timestamptz.sql: converts back to naive
-- TIMESTAMP, re-expressing the stored instant in UTC clock time (the same
-- assumption the up migration made in reverse). This restores Fix 1's
-- original defect (a naive column that _utc() cannot trust) and is provided
-- for controlled non-production verification only, per db/migrations/README.md
-- production recovery policy -- not for use as a production rollback.
--
-- 051_cqc_freshness_evidence.sql's idx_pipeline_runs_cqc_attempts indexes
-- COALESCE(completed_at, started_at). Verified against a real Postgres 15:
-- ALTER COLUMN ... TYPE TIMESTAMP on either column while that index exists
-- fails with "functions in index expression must be marked IMMUTABLE" (the
-- reverse direction, TIMESTAMP -> TIMESTAMPTZ, does not hit this -- verified
-- the up migration leaves the index valid with no rebuild needed). Drop it
-- first and recreate it verbatim from 051 afterwards.
DROP INDEX IF EXISTS idx_pipeline_runs_cqc_attempts;

ALTER TABLE pipeline_runs
  ALTER COLUMN started_at TYPE TIMESTAMP USING started_at AT TIME ZONE 'UTC';
ALTER TABLE pipeline_runs
  ALTER COLUMN completed_at TYPE TIMESTAMP USING completed_at AT TIME ZONE 'UTC';

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_cqc_attempts
  ON pipeline_runs (COALESCE(completed_at, started_at) DESC)
  WHERE run_type IN ('signal_poll', 'incremental', 'reconciliation');
