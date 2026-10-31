-- A confirmed Brief may contain any 1-50 distinct providers, without padding.
-- Discover the CHECK by column/definition: repaired legacy schemas can have a
-- different constraint name. Do not edit previously applied migration files.
DO $$
DECLARE check_row RECORD;
BEGIN
  FOR check_row IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'territory_brief_orders'::regclass AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%scope_shortlist_target%'
  LOOP
    EXECUTE format('ALTER TABLE territory_brief_orders DROP CONSTRAINT %I', check_row.conname);
  END LOOP;
END $$;
ALTER TABLE territory_brief_orders
  ADD CONSTRAINT territory_brief_orders_shortlist_1_50_check
  CHECK (scope_shortlist_target BETWEEN 1 AND 50);
