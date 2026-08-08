-- Downgrade: 024_profile_completeness_function
-- REVERSIBLE
-- Drops the calculate_profile_completeness function.
-- Risk: application code calling this function will fail immediately;
-- the profile_completeness column is NOT dropped (added by migration 010).
-- The backfill (score values in the column) cannot be un-computed without a snapshot,
-- but the column itself remains valid after the function is dropped.
-- Callers should fall back to the inline CASE logic from migration 010.

DROP FUNCTION IF EXISTS calculate_profile_completeness(TEXT, JSONB, TEXT, TEXT, BOOLEAN, TEXT);
