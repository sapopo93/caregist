-- Align the persisted signup-intent constraint with the current Radar catalogue.
--
-- Legacy values remain accepted for historical rows, while the API's strict
-- RegisterRequest enum prevents new callers from selecting retired products.

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_signup_purchase_intent_valid;

ALTER TABLE users
  ADD CONSTRAINT users_signup_purchase_intent_valid CHECK (
    (signup_intent_type IS NULL AND signup_intent_value IS NULL)
    OR (
      signup_intent_type = 'plan'
      AND signup_intent_value IN (
        'alerts-pro', 'data-starter', 'data-pro', 'data-business',
        'radar-regional', 'radar-national'
      )
    )
    OR (
      signup_intent_type = 'provider_tier'
      AND signup_intent_value IN ('enhanced', 'sponsored')
    )
  );
