-- Rebuild the Territory Brief tables where they predate migration 060.
--
-- Production's territory_brief_orders and territory_brief_download_tokens
-- existed before 060 ran (20 Sep 2026), so 060's CREATE TABLE IF NOT EXISTS
-- skipped them and left an older design: no scope_* columns, no retry or
-- PDF/CSV blob columns, and no artifact_kind on the tokens. The fulfilment and
-- download code on main cannot run against that shape. Found 30 Oct 2026, when
-- migration 072 failed on the missing artifact_kind column.
--
-- Where any Brief table lacks a column the code needs, this drops the five Brief
-- tables and recreates them as 060 + 071 + 072 define them. It refuses if any of
-- them holds a row, so it can only ever discard empty tables. Where the shape
-- is already current (fresh databases, staging, CI) it changes nothing.
--
-- Approved by the founder on 30 Oct 2026 (production tables held 0 rows; Neon
-- recovery branch br-floral-paper-abjaq0oa taken first).

CREATE OR REPLACE FUNCTION prevent_territory_brief_consent_mutation()
RETURNS TRIGGER AS $fn$
BEGIN
  RAISE EXCEPTION 'territory_brief_consents is append-only';
END;
$fn$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION prevent_territory_brief_scope_mutation()
RETURNS TRIGGER AS $fn$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'territory_brief_scope_versions rows are retained as evidence';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.order_id IS DISTINCT FROM OLD.order_id
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.supersedes_version IS DISTINCT FROM OLD.supersedes_version
     OR NEW.rule_version IS DISTINCT FROM OLD.rule_version
     OR NEW.buyer_objective IS DISTINCT FROM OLD.buyer_objective
     OR NEW.provider_exclusion_count IS DISTINCT FROM OLD.provider_exclusion_count
     OR NEW.location_exclusion_count IS DISTINCT FROM OLD.location_exclusion_count
     OR NEW.scope_sha256 IS DISTINCT FROM OLD.scope_sha256
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'territory_brief_scope_versions is frozen once written; add a new version instead';
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

DO $$
DECLARE
  required CONSTANT TEXT[][] := ARRAY[
    ['territory_brief_orders', 'id'],
    ['territory_brief_orders', 'stripe_checkout_session_id'],
    ['territory_brief_orders', 'stripe_payment_intent_id'],
    ['territory_brief_orders', 'customer_email'],
    ['territory_brief_orders', 'stripe_price_id'],
    ['territory_brief_orders', 'amount_total'],
    ['territory_brief_orders', 'currency'],
    ['territory_brief_orders', 'scope_kind'],
    ['territory_brief_orders', 'scope_name'],
    ['territory_brief_orders', 'scope_window_days'],
    ['territory_brief_orders', 'scope_shortlist_target'],
    ['territory_brief_orders', 'status'],
    ['territory_brief_orders', 'generation_attempts'],
    ['territory_brief_orders', 'last_error'],
    ['territory_brief_orders', 'blob_pdf_pathname'],
    ['territory_brief_orders', 'blob_csv_pathname'],
    ['territory_brief_orders', 'artifact_sha256'],
    ['territory_brief_orders', 'created_at'],
    ['territory_brief_orders', 'updated_at'],
    ['territory_brief_orders', 'paid_at'],
    ['territory_brief_orders', 'fulfilled_at'],
    ['territory_brief_orders', 'blob_zip_pathname'],
    ['territory_brief_orders', 'package_sha256'],
    ['territory_brief_orders', 'selection_snapshot'],
    ['territory_brief_orders', 'selection_sha256'],
    ['territory_brief_orders', 'package_manifest'],
    ['territory_brief_orders', 'package_version'],
    ['territory_brief_orders', 'source_edition_id'],
    ['territory_brief_consents', 'order_id'],
    ['territory_brief_consents', 'stripe_checkout_session_id'],
    ['territory_brief_consents', 'terms_version'],
    ['territory_brief_consents', 'terms_sha256'],
    ['territory_brief_consents', 'consent_text_sha256'],
    ['territory_brief_consents', 'immediate_supply_consented'],
    ['territory_brief_consents', 'cancellation_right_acknowledged'],
    ['territory_brief_consents', 'accepted_at'],
    ['territory_brief_consents', 'evidence_source'],
    ['territory_brief_download_tokens', 'token_hash'],
    ['territory_brief_download_tokens', 'order_id'],
    ['territory_brief_download_tokens', 'artifact_kind'],
    ['territory_brief_download_tokens', 'expires_at'],
    ['territory_brief_download_tokens', 'max_downloads'],
    ['territory_brief_download_tokens', 'download_count'],
    ['territory_brief_download_tokens', 'created_at'],
    ['territory_brief_download_tokens', 'last_downloaded_at']
  ];
  brief_tables CONSTANT TEXT[] := ARRAY[
    'territory_brief_scope_exclusions',
    'territory_brief_scope_versions',
    'territory_brief_consents',
    'territory_brief_download_tokens',
    'territory_brief_orders'
  ];
  missing TEXT[] := ARRAY[]::TEXT[];
  tbl TEXT;
  row_count BIGINT;
  i INTEGER;
BEGIN
  FOR i IN 1 .. array_length(required, 1) LOOP
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = current_schema()
        AND table_name = required[i][1]
        AND column_name = required[i][2]
    ) THEN
      missing := missing || (required[i][1] || '.' || required[i][2]);
    END IF;
  END LOOP;

  IF array_length(missing, 1) IS NULL THEN
    RAISE NOTICE 'Territory Brief tables already match the current design; nothing to rebuild.';
    RETURN;
  END IF;

  RAISE NOTICE 'Territory Brief tables predate migration 060 (missing: %); rebuilding.',
    array_to_string(missing, ', ');

  -- Prevent a writer from committing a new row between the emptiness check and
  -- DROP. Take every lock first, then count under READ COMMITTED snapshots.
  FOREACH tbl IN ARRAY brief_tables LOOP
    IF to_regclass(tbl) IS NOT NULL THEN
      EXECUTE format('LOCK TABLE %I IN ACCESS EXCLUSIVE MODE', tbl);
    END IF;
  END LOOP;

  FOREACH tbl IN ARRAY brief_tables LOOP
    IF to_regclass(tbl) IS NOT NULL THEN
      EXECUTE format('SELECT COUNT(*) FROM %I', tbl) INTO row_count;
      IF row_count > 0 THEN
        RAISE EXCEPTION 'Refusing to rebuild %: it holds % row(s). Migrate the data by hand.', tbl, row_count;
      END IF;
    END IF;
  END LOOP;

  -- No CASCADE: an unexpected dependant (a view, another foreign key) stops the
  -- migration and rolls it back instead of being dropped silently.
  FOREACH tbl IN ARRAY brief_tables LOOP
    EXECUTE format('DROP TABLE IF EXISTS %I', tbl);
  END LOOP;

  -- 060, with 072's package columns and token kinds folded in.
  CREATE TABLE territory_brief_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_checkout_session_id TEXT UNIQUE,
    stripe_payment_intent_id TEXT UNIQUE,
    customer_email TEXT NOT NULL,
    stripe_price_id TEXT NOT NULL,
    amount_total INTEGER,
    currency CHAR(3),
    scope_kind TEXT NOT NULL CHECK (scope_kind IN ('local_authority', 'region')),
    scope_name TEXT NOT NULL CHECK (scope_name = BTRIM(scope_name) AND scope_name <> ''),
    scope_window_days INTEGER NOT NULL DEFAULT 90 CHECK (scope_window_days BETWEEN 7 AND 365),
    scope_shortlist_target INTEGER NOT NULL DEFAULT 30 CHECK (scope_shortlist_target BETWEEN 10 AND 50),
    status TEXT NOT NULL DEFAULT 'pending'
      CHECK (status IN ('pending', 'paid', 'generating', 'fulfilled', 'failed', 'expired', 'refunded')),
    generation_attempts INTEGER NOT NULL DEFAULT 0 CHECK (generation_attempts >= 0),
    last_error TEXT,
    blob_pdf_pathname TEXT,
    blob_csv_pathname TEXT,
    artifact_sha256 CHAR(64) CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    fulfilled_at TIMESTAMPTZ,
    blob_zip_pathname TEXT,
    package_sha256 CHAR(64),
    selection_snapshot JSONB,
    selection_sha256 CHAR(64),
    package_manifest JSONB,
    package_version TEXT,
    source_edition_id BIGINT REFERENCES territory_brief_source_editions(id) ON DELETE RESTRICT,
    CHECK (customer_email = LOWER(BTRIM(customer_email))),
    CHECK (stripe_price_id LIKE 'price_%'),
    CHECK (amount_total IS NULL OR amount_total >= 0),
    CHECK (currency IS NULL OR currency ~ '^[a-z]{3}$'),
    CONSTRAINT territory_brief_orders_package_sha256_check
      CHECK (package_sha256 IS NULL OR package_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT territory_brief_orders_selection_sha256_check
      CHECK (selection_sha256 IS NULL OR selection_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT territory_brief_orders_package_version_check
      CHECK (package_version IS NULL OR (package_version = BTRIM(package_version) AND package_version <> ''))
  );

  CREATE INDEX territory_brief_orders_email_created
    ON territory_brief_orders (customer_email, created_at DESC);
  CREATE INDEX territory_brief_orders_status
    ON territory_brief_orders (status) WHERE status IN ('paid', 'generating', 'failed');

  CREATE TABLE territory_brief_consents (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL UNIQUE REFERENCES territory_brief_orders(id) ON DELETE RESTRICT,
    stripe_checkout_session_id TEXT NOT NULL UNIQUE,
    terms_version TEXT NOT NULL CHECK (terms_version = BTRIM(terms_version) AND terms_version <> ''),
    terms_sha256 CHAR(64) NOT NULL CHECK (terms_sha256 ~ '^[0-9a-f]{64}$'),
    consent_text_sha256 CHAR(64) NOT NULL CHECK (consent_text_sha256 ~ '^[0-9a-f]{64}$'),
    immediate_supply_consented BOOLEAN NOT NULL CHECK (immediate_supply_consented),
    cancellation_right_acknowledged BOOLEAN NOT NULL CHECK (cancellation_right_acknowledged),
    accepted_at TIMESTAMPTZ NOT NULL,
    evidence_source TEXT NOT NULL CHECK (evidence_source = 'stripe_checkout_terms_checkbox')
  );

  COMMENT ON TABLE territory_brief_consents IS
    'Append-only evidence of express immediate-supply consent for the Territory Opportunity Brief.';

  CREATE TRIGGER territory_brief_consents_immutable
  BEFORE UPDATE OR DELETE ON territory_brief_consents
  FOR EACH ROW EXECUTE FUNCTION prevent_territory_brief_consent_mutation();

  CREATE TABLE territory_brief_download_tokens (
    token_hash CHAR(64) PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    order_id UUID NOT NULL REFERENCES territory_brief_orders(id) ON DELETE RESTRICT,
    artifact_kind TEXT NOT NULL
      CONSTRAINT territory_brief_download_tokens_artifact_kind_check
        CHECK (artifact_kind IN ('pdf', 'csv', 'zip')),
    expires_at TIMESTAMPTZ NOT NULL,
    max_downloads INTEGER NOT NULL DEFAULT 5 CHECK (max_downloads BETWEEN 1 AND 20),
    download_count INTEGER NOT NULL DEFAULT 0 CHECK (download_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_downloaded_at TIMESTAMPTZ,
    CHECK (expires_at > created_at),
    UNIQUE (order_id, artifact_kind)
  );

  CREATE INDEX territory_brief_download_tokens_order
    ON territory_brief_download_tokens (order_id, expires_at DESC);

  -- 071, unchanged.
  CREATE TABLE territory_brief_scope_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES territory_brief_orders(id) ON DELETE RESTRICT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    supersedes_version INTEGER,
    rule_version INTEGER NOT NULL DEFAULT 1 CHECK (rule_version >= 1),
    buyer_objective TEXT CHECK (
      buyer_objective IS NULL
      OR (buyer_objective = BTRIM(buyer_objective) AND char_length(buyer_objective) BETWEEN 10 AND 300)
    ),
    provider_exclusion_count INTEGER NOT NULL DEFAULT 0 CHECK (provider_exclusion_count BETWEEN 0 AND 500),
    location_exclusion_count INTEGER NOT NULL DEFAULT 0 CHECK (location_exclusion_count BETWEEN 0 AND 500),
    scope_sha256 CHAR(64) NOT NULL CHECK (scope_sha256 ~ '^[0-9a-f]{64}$'),
    exclusions_purge_after TIMESTAMPTZ,
    exclusions_purged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (order_id, version),
    CHECK (supersedes_version IS NULL OR supersedes_version < version)
  );

  CREATE INDEX territory_brief_scope_versions_purge
    ON territory_brief_scope_versions (exclusions_purge_after)
    WHERE exclusions_purge_after IS NOT NULL AND exclusions_purged_at IS NULL;

  CREATE TABLE territory_brief_scope_exclusions (
    scope_version_id UUID NOT NULL REFERENCES territory_brief_scope_versions(id) ON DELETE CASCADE,
    id_kind TEXT NOT NULL CHECK (id_kind IN ('provider', 'location')),
    cqc_id TEXT NOT NULL CHECK (cqc_id ~ '^1-[0-9]{5,12}$'),
    PRIMARY KEY (scope_version_id, id_kind, cqc_id)
  );

  COMMENT ON TABLE territory_brief_scope_exclusions IS
    'Buyer exclusion identifiers for one scope version. Private to the order. Deleted after the correction period; never logged, never sent to Stripe, never shown in output.';

  CREATE TRIGGER territory_brief_scope_versions_frozen
  BEFORE UPDATE OR DELETE ON territory_brief_scope_versions
  FOR EACH ROW EXECUTE FUNCTION prevent_territory_brief_scope_mutation();
END $$;
