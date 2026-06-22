-- Downgrade: 029_password_reset_token_entropy
-- NOT REVERSIBLE
-- This migration changed the token column from VARCHAR(10) to TEXT to hold
-- high-entropy URL-safe tokens. Reverting the type to VARCHAR(10) would truncate
-- any in-flight token values longer than 10 characters, silently corrupting them.
-- Application code generating long tokens would also fail CHECK/insert validation.
-- Rolling back requires a snapshot taken before this migration was applied.

-- NOT REVERSIBLE -- restore from snapshot per workflows/restore-from-snapshot.md
