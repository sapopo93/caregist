-- Audit trail for all admin moderation actions.
-- Records who did what, to which entity, and when.

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id          BIGSERIAL PRIMARY KEY,
    action      TEXT NOT NULL,          -- 'claim.approved', 'claim.rejected', 'review.approved', etc.
    entity_type TEXT NOT NULL,          -- 'claim', 'review', 'enquiry'
    entity_id   INT NOT NULL,
    actor       TEXT NOT NULL,          -- admin key name from auth
    metadata    JSONB,                  -- additional context (provider_id, old_status, etc.)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_entity ON admin_audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_actor  ON admin_audit_log (actor);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_ts     ON admin_audit_log (created_at DESC);
