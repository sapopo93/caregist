-- Downgrade: 020_pipeline_runs
-- REVERSIBLE
-- Drops the pipeline_runs table and its index.
-- Risk: destroys all historical run data; coordinate with alerting consumers first.

DROP INDEX IF EXISTS idx_pipeline_runs_type_completed;
DROP TABLE IF EXISTS pipeline_runs;
