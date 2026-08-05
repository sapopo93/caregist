-- Forward-only production migration. Mutation ledger evidence must not be
-- deleted by an application rollback; use a forward fix instead.
DO $$
BEGIN
  RAISE NOTICE 'Migration 045 is intentionally forward-only; mutation ledger evidence was retained.';
END $$;
