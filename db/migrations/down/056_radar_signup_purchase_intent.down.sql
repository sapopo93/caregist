-- Controlled non-production rollback for migration 056.
-- Fail closed if current Radar intent rows exist; removing their allowed value
-- would otherwise make the restored constraint impossible to validate.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM users
    WHERE signup_intent_type = 'plan'
      AND signup_intent_value IN ('radar-regional', 'radar-national')
  ) THEN
    RAISE EXCEPTION
      'Cannot roll back migration 056 while Radar signup purchase intents exist';
  END IF;
END
$$;

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_signup_purchase_intent_valid;

ALTER TABLE users
  ADD CONSTRAINT users_signup_purchase_intent_valid CHECK (
    (signup_intent_type IS NULL AND signup_intent_value IS NULL)
    OR (
      signup_intent_type = 'plan'
      AND signup_intent_value IN (
        'alerts-pro', 'data-starter', 'data-pro', 'data-business'
      )
    )
    OR (
      signup_intent_type = 'provider_tier'
      AND signup_intent_value IN ('enhanced', 'sponsored')
    )
  );
