-- Forward-only production migration. Evidence, referrals, placements, contracts,
-- commissions and review decisions are business records and are not deleted.
DO $$
BEGIN
  RAISE NOTICE 'Migration 058 is intentionally forward-only; CRM intelligence records were retained.';
END
$$;

