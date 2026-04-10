-- Trusted event ledger and launch wedge primitives for the
-- "newly registered UK care providers" recurring intelligence feed.

CREATE TABLE IF NOT EXISTS trusted_event_ledger (
  id BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  provider_id VARCHAR(20),
  location_id VARCHAR(20),
  event_type TEXT NOT NULL,
  effective_date DATE NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  old_value JSONB,
  new_value JSONB,
  source TEXT NOT NULL,
  confidence_score NUMERIC(5,4) NOT NULL DEFAULT 1.0000,
  dedupe_key TEXT NOT NULL UNIQUE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tel_event_date ON trusted_event_ledger (event_type, effective_date DESC);
CREATE INDEX IF NOT EXISTS idx_tel_provider ON trusted_event_ledger (provider_id);
CREATE INDEX IF NOT EXISTS idx_tel_location ON trusted_event_ledger (location_id);
CREATE INDEX IF NOT EXISTS idx_tel_observed_at ON trusted_event_ledger (observed_at DESC);

CREATE TABLE IF NOT EXISTS saved_feed_filters (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  feed_type TEXT NOT NULL DEFAULT 'new_registration',
  name VARCHAR(120) NOT NULL,
  filters JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, feed_type, name)
);

CREATE INDEX IF NOT EXISTS idx_saved_feed_filters_user_feed ON saved_feed_filters (user_id, feed_type);

CREATE TABLE IF NOT EXISTS feed_digest_subscriptions (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) ON DELETE CASCADE,
  email VARCHAR(255) NOT NULL,
  feed_type TEXT NOT NULL DEFAULT 'new_registration',
  filters JSONB NOT NULL DEFAULT '{}'::jsonb,
  frequency TEXT NOT NULL DEFAULT 'weekly',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  unsubscribe_token TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, feed_type, frequency)
);

CREATE INDEX IF NOT EXISTS idx_feed_digest_subscriptions_active
  ON feed_digest_subscriptions (feed_type, active)
  WHERE active = TRUE;

CREATE TABLE IF NOT EXISTS feed_digest_delivery_log (
  id SERIAL PRIMARY KEY,
  subscription_id INT NOT NULL REFERENCES feed_digest_subscriptions(id) ON DELETE CASCADE,
  digest_key TEXT NOT NULL,
  event_count INT NOT NULL DEFAULT 0,
  pending_email_id INT REFERENCES pending_emails(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(subscription_id, digest_key)
);

ALTER TABLE webhook_subscriptions
  ADD COLUMN IF NOT EXISTS filter_config JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS webhook_delivery_log (
  id BIGSERIAL PRIMARY KEY,
  subscription_id INT NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  event_dedupe_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  attempt_count INT NOT NULL DEFAULT 0,
  response_status INT,
  last_error TEXT,
  last_attempt_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(subscription_id, event_type, event_dedupe_key)
);

CREATE INDEX IF NOT EXISTS idx_webhook_delivery_log_event ON webhook_delivery_log (event_type, created_at DESC);

-- Backfill the ledger with canonical new-registration events from the
-- existing provider snapshot so the feed can launch off a durable history.
INSERT INTO trusted_event_ledger (
  entity_type,
  entity_id,
  provider_id,
  location_id,
  event_type,
  effective_date,
  observed_at,
  old_value,
  new_value,
  source,
  confidence_score,
  dedupe_key,
  metadata
)
SELECT
  'care_provider',
  cp.id,
  cp.provider_id,
  cp.id,
  'new_registration',
  cp.registration_date,
  COALESCE(cp.last_updated, cp.updated_at, cp.created_at, NOW()),
  NULL,
  jsonb_build_object(
    'name', cp.name,
    'slug', cp.slug,
    'status', cp.status,
    'type', cp.type,
    'registration_date', cp.registration_date,
    'region', cp.region,
    'local_authority', cp.local_authority,
    'postcode', cp.postcode,
    'service_types', cp.service_types
  ),
  'care_providers_snapshot',
  0.9900,
  CONCAT('new_registration:', cp.id, ':', cp.registration_date::text),
  jsonb_build_object(
    'name', cp.name,
    'slug', cp.slug,
    'status', cp.status,
    'type', cp.type,
    'town', cp.town,
    'county', cp.county,
    'region', cp.region,
    'local_authority', cp.local_authority,
    'postcode', cp.postcode,
    'service_types', cp.service_types
  )
FROM care_providers cp
WHERE cp.registration_date IS NOT NULL
ON CONFLICT (dedupe_key) DO NOTHING;
