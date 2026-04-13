-- Track operational pipeline run history for health checks and alerting.

CREATE TABLE IF NOT EXISTS pipeline_runs (
  id BIGSERIAL PRIMARY KEY,
  run_type TEXT NOT NULL,       -- 'incremental' | 'feed_cycle'
  status TEXT NOT NULL,         -- 'running' | 'completed' | 'failed'
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_type_completed
  ON pipeline_runs (run_type, completed_at DESC);
