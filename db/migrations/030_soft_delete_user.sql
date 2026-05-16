-- Migration 030: soft-delete + erasure fields on users
-- UK DPA 2018 / GDPR Art 17 (right to erasure) + Art 15 (DSAR)
-- Run once against production. Owner must apply before deploying the
-- account-deletion and DSAR-export endpoints.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deleted_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deletion_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users (deleted_at)
    WHERE deleted_at IS NOT NULL;

COMMENT ON COLUMN users.deleted_at IS
    'NULL = active account. Non-NULL = soft-deleted; account is considered
     erased for all active-user queries. Set by POST /api/v1/account/delete
     or POST /api/v1/admin/users/{id}/erase.';

COMMENT ON COLUMN users.deletion_reason IS
    'Free-text reason recorded at soft-delete time (self-service or admin).';
