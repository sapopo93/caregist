-- Forward-only production migration. Contract acceptance evidence must not be
-- deleted by an application rollback; use a forward fix instead.
DO $$
BEGIN
  RAISE NOTICE 'Migration 044 is intentionally forward-only; contract evidence was retained.';
END $$;
