-- F-51: email verification tokens previously never expired. Add an expiry
-- column so issued tokens become invalid after a fixed window and users are
-- offered a re-send. Existing unverified accounts get a fresh 24h window from
-- the time this migration runs so no in-flight verification is silently broken.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS verification_token_expires_at TIMESTAMPTZ;

UPDATE users
SET verification_token_expires_at = NOW() + INTERVAL '24 hours'
WHERE verification_token IS NOT NULL
  AND is_verified = false
  AND verification_token_expires_at IS NULL;
