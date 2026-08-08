-- Downgrade: 022_admin_audit_log
-- REVERSIBLE
-- Drops the admin_audit_log table and its indexes.
-- Risk: destroys all recorded admin-moderation audit history; compliance impact if audit trail is required.

DROP INDEX IF EXISTS idx_admin_audit_log_ts;
DROP INDEX IF EXISTS idx_admin_audit_log_actor;
DROP INDEX IF EXISTS idx_admin_audit_log_entity;
DROP TABLE IF EXISTS admin_audit_log;
