-- Reverse 076_region_monthly_builds.sql.
-- Non-production verification only (db/migrations/README.md). On production, a
-- built month is a published record: disable the Region Monthly flag and use a
-- forward-fix migration, or Neon point-in-time recovery for corruption.

DROP TRIGGER IF EXISTS region_monthly_builds_immutable_truncate ON region_monthly_builds;
DROP TRIGGER IF EXISTS region_monthly_builds_immutable_row ON region_monthly_builds;
DROP TRIGGER IF EXISTS region_monthly_builds_guard_insert ON region_monthly_builds;
DROP FUNCTION IF EXISTS region_monthly_builds_reject_change();
DROP FUNCTION IF EXISTS region_monthly_builds_guard_insert();
DROP TABLE IF EXISTS region_monthly_builds;
