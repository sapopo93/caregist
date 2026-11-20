-- Reverses 077. Non-production verification only: a production recovery uses a
-- forward fix or a Neon recovery point (db/migrations/README.md). Running this
-- deletes every Region Monthly order and entitlement. The stage 1 table
-- region_monthly_builds (076) is not touched.
DROP TRIGGER IF EXISTS region_monthly_entitlements_immutable_truncate ON region_monthly_entitlements;
DROP TRIGGER IF EXISTS region_monthly_entitlements_immutable_row ON region_monthly_entitlements;
DROP TRIGGER IF EXISTS region_monthly_entitlements_guard_insert ON region_monthly_entitlements;
DROP TRIGGER IF EXISTS region_monthly_orders_immutable_truncate ON region_monthly_orders;
DROP TRIGGER IF EXISTS region_monthly_orders_guard_trg ON region_monthly_orders;
DROP TABLE IF EXISTS region_monthly_entitlements;
DROP TABLE IF EXISTS region_monthly_orders;
DROP FUNCTION IF EXISTS region_monthly_entitlements_guard_insert();
DROP FUNCTION IF EXISTS region_monthly_orders_guard();
DROP FUNCTION IF EXISTS region_monthly_orders_reject_change();
