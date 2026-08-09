-- Forward-only production migration. Dropping batch and alert evidence would
-- destroy recovery/audit state; use Neon PITR or a forward fix instead.
DO $$
BEGIN
  RAISE NOTICE 'Migration 043 is intentionally forward-only; reconciliation evidence was retained.';
END $$;
