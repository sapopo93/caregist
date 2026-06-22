-- Downgrade: 026_hash_api_keys
-- NOT REVERSIBLE
-- This migration hashed all plaintext API keys using SHA-256 (one-way) and then NULLed the
-- original key column. The plaintext keys are permanently gone; they cannot be recovered
-- from the hash. Rolling back the schema objects alone would leave every API key non-functional.
-- The api_rate_usage_daily api_key column was also hashed in-place.

-- NOT REVERSIBLE -- restore from snapshot per workflows/restore-from-snapshot.md
