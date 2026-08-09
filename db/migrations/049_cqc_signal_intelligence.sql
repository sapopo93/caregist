-- Canonical CQC signal-intelligence schema.
-- Additive only: legacy feed and heuristic tables remain readable for one
-- compatibility release while all new product work uses trusted_event_ledger.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS source_snapshots (
  id BIGSERIAL PRIMARY KEY,
  source_type TEXT NOT NULL CHECK (source_type IN ('cqc_location_index', 'cqc_report_index', 'cqc_location_detail', 'cqc_directory_csv')),
  source_uri TEXT NOT NULL,
  source_published_at TIMESTAMPTZ,
  source_checked_at TIMESTAMPTZ NOT NULL,
  checksum_sha256 CHAR(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
  record_count INTEGER CHECK (record_count IS NULL OR record_count >= 0),
  status TEXT NOT NULL DEFAULT 'verified' CHECK (status IN ('verified', 'rejected')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_type, checksum_sha256)
);

ALTER TABLE trusted_event_ledger
  ADD COLUMN IF NOT EXISTS public_event_id UUID DEFAULT gen_random_uuid(),
  ADD COLUMN IF NOT EXISTS schema_version SMALLINT NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS entity_level TEXT NOT NULL DEFAULT 'location',
  ADD COLUMN IF NOT EXISTS source_snapshot_id BIGINT REFERENCES source_snapshots(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS source_published_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS source_checked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS source_url TEXT,
  ADD COLUMN IF NOT EXISTS source_snapshot_sha256 CHAR(64),
  ADD COLUMN IF NOT EXISTS explanation_status TEXT NOT NULL DEFAULT 'not_requested';

UPDATE trusted_event_ledger
SET public_event_id = gen_random_uuid()
WHERE public_event_id IS NULL;

ALTER TABLE trusted_event_ledger
  ALTER COLUMN public_event_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_tel_public_event_id
  ON trusted_event_ledger (public_event_id);
CREATE INDEX IF NOT EXISTS idx_tel_radar_cursor
  ON trusted_event_ledger (observed_at DESC, public_event_id DESC)
  WHERE event_type IN ('new_registration', 'rating_changed');

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'trusted_event_ledger_entity_level_valid'
      AND conrelid = 'trusted_event_ledger'::regclass
  ) THEN
    ALTER TABLE trusted_event_ledger
      ADD CONSTRAINT trusted_event_ledger_entity_level_valid
      CHECK (entity_level IN ('service', 'location', 'provider', 'group'));
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'trusted_event_ledger_explanation_status_valid'
      AND conrelid = 'trusted_event_ledger'::regclass
  ) THEN
    ALTER TABLE trusted_event_ledger
      ADD CONSTRAINT trusted_event_ledger_explanation_status_valid
      CHECK (explanation_status IN ('not_requested', 'pending', 'published', 'failed_review', 'disabled'));
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'trusted_event_ledger_snapshot_sha_valid'
      AND conrelid = 'trusted_event_ledger'::regclass
  ) THEN
    ALTER TABLE trusted_event_ledger
      ADD CONSTRAINT trusted_event_ledger_snapshot_sha_valid
      CHECK (source_snapshot_sha256 IS NULL OR source_snapshot_sha256 ~ '^[0-9a-f]{64}$');
  END IF;
END
$$;

ALTER TABLE care_providers
  ADD COLUMN IF NOT EXISTS registered_manager_absent_date DATE,
  ADD COLUMN IF NOT EXISTS signal_checked_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS cqc_location_index_entries (
  location_id VARCHAR(20) PRIMARY KEY,
  first_seen_at TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL,
  last_snapshot_id BIGINT REFERENCES source_snapshots(id) ON DELETE SET NULL,
  is_present BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_cqc_location_index_last_seen
  ON cqc_location_index_entries (last_seen_at);

CREATE TABLE IF NOT EXISTS report_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cqc_location_id VARCHAR(20) NOT NULL REFERENCES care_providers(id) ON DELETE CASCADE,
  source_snapshot_id BIGINT REFERENCES source_snapshots(id) ON DELETE SET NULL,
  source_url TEXT NOT NULL,
  source_published_at TIMESTAMPTZ,
  blob_uri TEXT NOT NULL,
  sha256 CHAR(64) NOT NULL UNIQUE CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  media_type TEXT NOT NULL DEFAULT 'application/pdf',
  byte_count BIGINT CHECK (byte_count IS NULL OR byte_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_evidence_spans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_document_id UUID NOT NULL REFERENCES report_documents(id) ON DELETE CASCADE,
  page_number INTEGER CHECK (page_number IS NULL OR page_number > 0),
  heading TEXT,
  quote_text TEXT NOT NULL,
  quote_sha256 CHAR(64) NOT NULL CHECK (quote_sha256 ~ '^[0-9a-f]{64}$'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_explanations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id BIGINT NOT NULL REFERENCES trusted_event_ledger(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('pending', 'published', 'failed_review', 'disabled')),
  facts JSONB NOT NULL DEFAULT '[]'::jsonb,
  interpretation JSONB NOT NULL DEFAULT '[]'::jsonb,
  model_version TEXT,
  prompt_version TEXT,
  reviewed_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (event_id, model_version, prompt_version)
);

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(160) NOT NULL,
  slug VARCHAR(180) NOT NULL UNIQUE,
  created_by_user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization_members (
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (organization_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_organization_members_user
  ON organization_members (user_id, organization_id);

CREATE TABLE IF NOT EXISTS organization_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  stripe_subscription_id VARCHAR(100),
  plan_tier TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  scope_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  included_users INTEGER NOT NULL DEFAULT 1 CHECK (included_users > 0),
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id),
  UNIQUE (stripe_subscription_id)
);

CREATE TABLE IF NOT EXISTS saved_signal_views (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  name VARCHAR(120) NOT NULL,
  filters JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, name)
);

CREATE TABLE IF NOT EXISTS provider_lists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  name VARCHAR(120) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, name)
);

CREATE TABLE IF NOT EXISTS provider_list_items (
  provider_list_id UUID NOT NULL REFERENCES provider_lists(id) ON DELETE CASCADE,
  cqc_location_id VARCHAR(20) NOT NULL REFERENCES care_providers(id) ON DELETE CASCADE,
  added_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (provider_list_id, cqc_location_id)
);

CREATE TABLE IF NOT EXISTS event_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  event_id BIGINT NOT NULL REFERENCES trusted_event_ledger(id) ON DELETE CASCADE,
  action_type TEXT NOT NULL CHECK (action_type IN ('opened', 'saved', 'exported', 'dismissed', 'requested_detail')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, user_id, event_id, action_type)
);

CREATE TABLE IF NOT EXISTS event_outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  event_id BIGINT NOT NULL REFERENCES trusted_event_ledger(id) ON DELETE CASCADE,
  outcome_type TEXT NOT NULL CHECK (outcome_type IN ('contacted', 'meeting_booked', 'engagement_won', 'not_relevant')),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS delivery_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  delivery_type TEXT NOT NULL CHECK (delivery_type IN ('email', 'webhook')),
  endpoint TEXT NOT NULL,
  signing_secret_ciphertext TEXT,
  signing_secret_key_id TEXT,
  previous_signing_secret_ciphertext TEXT,
  previous_signing_secret_key_id TEXT,
  previous_secret_valid_until TIMESTAMPTZ,
  event_types TEXT[] NOT NULL DEFAULT ARRAY['new_registration', 'rating_changed']::TEXT[],
  filter_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, delivery_type, endpoint)
);

CREATE TABLE IF NOT EXISTS delivery_outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  delivery_subscription_id UUID NOT NULL REFERENCES delivery_subscriptions(id) ON DELETE CASCADE,
  event_id BIGINT NOT NULL REFERENCES trusted_event_ledger(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'delivered', 'dead_letter')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  locked_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (delivery_subscription_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_delivery_outbox_ready
  ON delivery_outbox (available_at, created_at)
  WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS delivery_attempts (
  id BIGSERIAL PRIMARY KEY,
  outbox_id UUID NOT NULL REFERENCES delivery_outbox(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
  response_status INTEGER,
  error_message TEXT,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (outbox_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS delivery_cursors (
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  consumer_key VARCHAR(120) NOT NULL,
  last_event_id BIGINT REFERENCES trusted_event_ledger(id) ON DELETE SET NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (organization_id, consumer_key)
);

INSERT INTO organizations (name, slug, created_by_user_id)
SELECT COALESCE(NULLIF(BTRIM(name), ''), 'CareGist account'), 'account-' || id::text, id
FROM users
ON CONFLICT (created_by_user_id) DO NOTHING;

INSERT INTO organization_members (organization_id, user_id, role)
SELECT o.id, o.created_by_user_id, 'owner'
FROM organizations o
ON CONFLICT (organization_id, user_id) DO NOTHING;

INSERT INTO organization_subscriptions (
  organization_id, stripe_subscription_id, plan_tier, status,
  included_users, current_period_end
)
SELECT o.id, s.stripe_subscription_id, s.tier, s.status,
       GREATEST(COALESCE(s.max_users, 1), 1), s.current_period_end
FROM organizations o
JOIN LATERAL (
  SELECT sub.*
  FROM subscriptions sub
  WHERE sub.user_id = o.created_by_user_id
  ORDER BY CASE WHEN sub.status IN ('active', 'trialing') THEN 0 ELSE 1 END,
           sub.created_at DESC
  LIMIT 1
) s ON TRUE
ON CONFLICT (organization_id) DO NOTHING;

-- Replace the purchase-intent allowlist without removing historical values.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_signup_purchase_intent_valid;
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
    OR (signup_intent_type = 'provider_tier' AND signup_intent_value IN ('enhanced', 'sponsored'))
  );

-- Tenant-owned business tables are protected by RLS. The API also scopes every
-- statement by organization_id; RLS is the database-level second boundary.
DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'organization_subscriptions', 'saved_signal_views', 'provider_lists',
    'provider_list_items', 'event_actions', 'event_outcomes',
    'delivery_subscriptions', 'delivery_outbox', 'delivery_attempts',
    'delivery_cursors'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
  END LOOP;
END
$$;

CREATE OR REPLACE FUNCTION caregist_current_user_id()
RETURNS INTEGER
LANGUAGE SQL
STABLE
AS $$
  SELECT NULLIF(current_setting('caregist.user_id', TRUE), '')::INTEGER
$$;

CREATE OR REPLACE FUNCTION caregist_is_organization_member(target_organization_id UUID)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM organization_members
    WHERE organization_id = target_organization_id
      AND user_id = caregist_current_user_id()
  )
$$;

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'organization_subscriptions', 'saved_signal_views', 'provider_lists',
    'event_actions', 'event_outcomes', 'delivery_subscriptions',
    'delivery_outbox', 'delivery_cursors'
  ] LOOP
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (caregist_is_organization_member(organization_id)) WITH CHECK (caregist_is_organization_member(organization_id))',
      table_name || '_tenant_policy', table_name
    );
  END LOOP;
END
$$;

CREATE POLICY provider_list_items_tenant_policy ON provider_list_items
  USING (
    EXISTS (
      SELECT 1 FROM provider_lists pl
      WHERE pl.id = provider_list_id
        AND caregist_is_organization_member(pl.organization_id)
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM provider_lists pl
      WHERE pl.id = provider_list_id
        AND caregist_is_organization_member(pl.organization_id)
    )
  );

CREATE POLICY delivery_attempts_tenant_policy ON delivery_attempts
  USING (
    EXISTS (
      SELECT 1 FROM delivery_outbox outbox
      WHERE outbox.id = outbox_id
        AND caregist_is_organization_member(outbox.organization_id)
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM delivery_outbox outbox
      WHERE outbox.id = outbox_id
        AND caregist_is_organization_member(outbox.organization_id)
    )
  );

CREATE POLICY delivery_subscriptions_worker_policy ON delivery_subscriptions
  USING (current_setting('caregist.worker', TRUE) = 'delivery');
CREATE POLICY delivery_outbox_worker_policy ON delivery_outbox
  USING (current_setting('caregist.worker', TRUE) = 'delivery')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'delivery');
CREATE POLICY delivery_attempts_worker_policy ON delivery_attempts
  USING (current_setting('caregist.worker', TRUE) = 'delivery')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'delivery');

COMMENT ON TABLE source_snapshots IS
  'Immutable evidence metadata for approved CQC source observations.';
COMMENT ON COLUMN trusted_event_ledger.public_event_id IS
  'Opaque stable identifier exposed to Radar and Intelligence Feed customers.';
COMMENT ON COLUMN care_providers.registered_manager_absent_date IS
  'Public CQC absence date only; it must not be labelled as a vacancy.';
