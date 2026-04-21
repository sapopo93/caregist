-- Security audit trail for sensitive mutations across auth, billing, admin, and internal actions.

CREATE TABLE IF NOT EXISTS audit_log (
    id            BIGSERIAL PRIMARY KEY,
    action        TEXT NOT NULL,
    outcome       TEXT NOT NULL,
    actor_type    TEXT NOT NULL,
    actor_user_id BIGINT,
    actor_key_id  BIGINT,
    actor_email   TEXT,
    actor_name    TEXT,
    target_type   TEXT,
    target_id     TEXT,
    metadata      JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor_user ON audit_log (actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_target ON audit_log (target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log (created_at DESC);
