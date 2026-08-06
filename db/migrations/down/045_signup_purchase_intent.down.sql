-- Forward-only production migration. Signup purchase intent is not sensitive
-- enough to require destructive rollback; use a forward fix instead.
DO $$
BEGIN
  RAISE NOTICE 'Migration 045 is intentionally forward-only.';
END $$;
