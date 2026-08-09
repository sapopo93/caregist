-- Forward-only production migration. billing_operations is the idempotent
-- Stripe mutation ledger; dropping it would let a retried request re-enter
-- Stripe with a fresh idempotency key. Use a forward fix instead.
DO $$
BEGIN
  RAISE NOTICE 'Migration 046 is intentionally forward-only; billing_operations evidence was retained.';
END $$;
