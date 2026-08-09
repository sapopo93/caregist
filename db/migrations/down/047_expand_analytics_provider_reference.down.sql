-- Forward-only production migration. Narrowing provider_id back to
-- VARCHAR(20) would truncate any analytics_events rows written with a longer
-- canonical slug. Use a forward fix instead.
DO $$
BEGIN
  RAISE NOTICE 'Migration 047 is intentionally forward-only; analytics_events.provider_id widening was retained.';
END $$;
