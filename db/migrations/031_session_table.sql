-- Migration 031: opaque server-side sessions table
-- Supports F#1 fix: cookie value is session_id (not bearer token).
-- Forge PR #5 owns 030; this is 031.
--
-- Pre-merge step: run this migration before deploying the API.
-- Rollback:       DROP TABLE IF EXISTS sessions CASCADE;
--                 (safe pre-launch; no live customers)

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT        PRIMARY KEY,
    user_id      BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at   TIMESTAMPTZ,
    user_agent   TEXT,
    ip_address   INET
);

CREATE INDEX idx_sessions_user_id       ON sessions(user_id);
CREATE INDEX idx_sessions_expires_active ON sessions(expires_at) WHERE revoked_at IS NULL;
