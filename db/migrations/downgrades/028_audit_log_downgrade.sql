-- Downgrade: 028_audit_log
-- REVERSIBLE
-- Drops the audit_log table and its indexes.
-- Risk: destroys all security audit history (auth, billing, admin events);
-- compliance/security impact if audit trail is required.

DROP INDEX IF EXISTS idx_audit_log_ts;
DROP INDEX IF EXISTS idx_audit_log_target;
DROP INDEX IF EXISTS idx_audit_log_actor_user;
DROP INDEX IF EXISTS idx_audit_log_action;
DROP TABLE IF EXISTS audit_log;
