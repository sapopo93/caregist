-- Refuse rollback rather than invalidating or deleting existing smaller orders.
ALTER TABLE territory_brief_orders DROP CONSTRAINT territory_brief_orders_shortlist_1_50_check;
ALTER TABLE territory_brief_orders
  ADD CONSTRAINT territory_brief_orders_scope_shortlist_target_check
  CHECK (scope_shortlist_target BETWEEN 10 AND 50);
