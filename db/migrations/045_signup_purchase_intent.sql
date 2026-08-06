-- Retain a structured signup purchase intent across email verification devices.
-- Raw URLs are deliberately not stored; the API maps these enums to allowlisted
-- same-origin paths after the email token has been verified.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS signup_intent_type VARCHAR(20),
  ADD COLUMN IF NOT EXISTS signup_intent_value VARCHAR(40);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'users_signup_purchase_intent_valid'
      AND conrelid = 'users'::regclass
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT users_signup_purchase_intent_valid CHECK (
        (signup_intent_type IS NULL AND signup_intent_value IS NULL)
        OR (signup_intent_type = 'plan' AND signup_intent_value IN ('alerts-pro', 'data-starter', 'data-pro', 'data-business'))
        OR (signup_intent_type = 'provider_tier' AND signup_intent_value IN ('enhanced', 'sponsored'))
      );
  END IF;
END
$$;
