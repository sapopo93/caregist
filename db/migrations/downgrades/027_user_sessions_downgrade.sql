-- Downgrade: 027_user_sessions
-- REVERSIBLE
-- Drops the user_sessions table and its index.
-- Note: 026 must be rolled back first if user_sessions has an FK to api_keys
-- (api_key_id column). All live sessions will be invalidated immediately.
-- Risk: every authenticated session is terminated; users will be signed out.

DROP INDEX IF EXISTS idx_user_sessions_user_active;
DROP TABLE IF EXISTS user_sessions;
