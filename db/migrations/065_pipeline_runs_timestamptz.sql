-- Fix 1 of the 2026-09-23 freshness audit is a no-op without this migration.
--
-- db/init.sql originally created pipeline_runs.started_at/completed_at as
-- naive TIMESTAMP. Migration 020_pipeline_runs.sql re-declares the table as
-- TIMESTAMPTZ, but it is `CREATE TABLE IF NOT EXISTS`, so on every database
-- that ran init.sql before 020 (production included) it is a no-op and the
-- columns stay naive TIMESTAMP.
--
-- api/services/cqc_freshness.py's _utc() treats a naive datetime as
-- unprovable and returns None rather than guessing a timezone. asyncpg
-- returns pipeline_runs.started_at as naive on this schema, so
-- _in_progress_within_grace() always fails closed and Fix 1's grace window
-- never engages. Verified live: /api/v1/health/freshness showed
-- latestAttempt.startedAt = null in production, and PR #73's CI migration
-- replay caught the same thing against a freshly-applied schema.
--
-- init.sql sets `SET timezone = 'UTC'` for the session that creates and
-- writes these rows, and every writer uses NOW() under that session, so the
-- stored naive values are UTC clock time with no offset recorded. Converting
-- with `AT TIME ZONE 'UTC'` (interpret-as-UTC, not shift) is therefore exact,
-- not a guess.
--
-- Approved by Henry (2026-09-23): a same-meaning type correction of an
-- operational tracking table, not user data, needed to make an existing,
-- already-approved fix take effect. Idempotent: the DO block only runs the
-- ALTER when the column is still `timestamp without time zone`, so this is
-- safe to apply more than once and safe on a database that already has
-- TIMESTAMPTZ (e.g. one that only ever ran 020's CREATE TABLE path).
--
-- 051_cqc_freshness_evidence.sql's idx_pipeline_runs_cqc_attempts indexes
-- COALESCE(completed_at, started_at). Verified against a real Postgres 15:
-- an ALTER COLUMN ... TYPE on either column while a round trip has already
-- rebuilt that index fails with "functions in index expression must be
-- marked IMMUTABLE". Drop it up front and recreate it verbatim from 051
-- afterwards so this is safe regardless of what state the index was built in.

DROP INDEX IF EXISTS idx_pipeline_runs_cqc_attempts;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pipeline_runs'
      AND column_name = 'started_at'
      AND data_type = 'timestamp without time zone'
  ) THEN
    ALTER TABLE pipeline_runs
      ALTER COLUMN started_at TYPE TIMESTAMPTZ USING started_at AT TIME ZONE 'UTC';
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pipeline_runs'
      AND column_name = 'completed_at'
      AND data_type = 'timestamp without time zone'
  ) THEN
    ALTER TABLE pipeline_runs
      ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC';
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_cqc_attempts
  ON pipeline_runs (COALESCE(completed_at, started_at) DESC)
  WHERE run_type IN ('signal_poll', 'incremental', 'reconciliation');

COMMENT ON COLUMN pipeline_runs.started_at IS
  'TIMESTAMPTZ. Historically naive TIMESTAMP on databases that ran init.sql before this migration; converted assuming the writing session was UTC (init.sql sets SET timezone = ''UTC''). See migration 065.';
COMMENT ON COLUMN pipeline_runs.completed_at IS
  'TIMESTAMPTZ. Historically naive TIMESTAMP on databases that ran init.sql before this migration; converted assuming the writing session was UTC (init.sql sets SET timezone = ''UTC''). See migration 065.';
