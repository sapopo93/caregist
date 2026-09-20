-- Additive: record a batch's unconfirmed deactivation candidates on the batch row.
--
-- Reviewer finding (FIX 3): finalization absorbed API-UNCONFIRMED candidates into
-- the expected active count, so an API failure or an unfamiliar registration
-- status could silently become the explanation for a change in the active set.
-- Finalization now refuses while unconfirmed candidates remain, and only
-- finalizes them when the operator explicitly acknowledges them
-- (incremental_update.py --acknowledge-unconfirmed-deactivations). When that
-- acknowledgement is used, the count of unconfirmed candidates is written here
-- and the full decision record (ids, classifications, expected vs observed
-- active count) is stored as JSON, so the batch row itself shows what was
-- accepted rather than absorbed.
--
-- NOTE: these columns RECORD an acknowledgement; they never widen the guard.
-- An unacknowledged/unexplained mismatch still refuses the batch, and the
-- acknowledged ids are counted only because the operator named them.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS only, no backfill, no row rewritten.

ALTER TABLE reconciliation_batches
  ADD COLUMN IF NOT EXISTS deactivation_unconfirmed_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE reconciliation_batches
  ADD COLUMN IF NOT EXISTS deactivation_confirmation JSONB;
