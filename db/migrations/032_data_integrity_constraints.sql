-- Data-integrity constraints and query-shape indexes.
--
-- Closes audit findings F-12, F-13, F-14, F-34. Every statement is written to
-- be safe to apply against a live database with pre-existing data:
--   * Foreign keys are added NOT VALID so they enforce on new/updated rows
--     immediately and never fail the migration on historical orphans. A
--     follow-up VALIDATE CONSTRAINT can be run during a low-traffic window.
--   * The unique active-subscription index is preceded by an idempotent dedup
--     that cancels all-but-the-newest active subscription per user.
--   * All indexes use IF NOT EXISTS.

-- ---------------------------------------------------------------------------
-- F-12: rating_changes.provider_id stores care_providers.id (the location PK,
-- see incremental_update.py). Add the missing FK so provider deletes cascade
-- to their rating-change history instead of leaving orphans.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_rating_changes_provider'
  ) THEN
    ALTER TABLE rating_changes
      ADD CONSTRAINT fk_rating_changes_provider
      FOREIGN KEY (provider_id) REFERENCES care_providers (id) ON DELETE CASCADE
      NOT VALID;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- F-13: trusted_event_ledger is the audit-of-record for the feed product.
-- Its provider_id column holds the CQC *provider* id (non-unique), so the
-- correct integrity link is on location_id, which is populated with
-- care_providers.id (see migration 015 backfill). SET NULL preserves ledger
-- rows if the underlying provider is ever removed.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'trusted_event_ledger' AND column_name = 'location_id'
  ) AND NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_trusted_event_ledger_location'
  ) THEN
    ALTER TABLE trusted_event_ledger
      ADD CONSTRAINT fk_trusted_event_ledger_location
      FOREIGN KEY (location_id) REFERENCES care_providers (id) ON DELETE SET NULL
      NOT VALID;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- F-14: prevent multiple status='active' subscriptions per user. First cancel
-- any existing duplicates (keep the most recently created active row), then
-- enforce the invariant with a partial unique index.
-- ---------------------------------------------------------------------------
UPDATE subscriptions s
SET status = 'superseded',
    updated_at = NOW()
WHERE status = 'active'
  AND id NOT IN (
    SELECT DISTINCT ON (user_id) id
    FROM subscriptions
    WHERE status = 'active'
    ORDER BY user_id, created_at DESC, id DESC
  );

CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_sub_per_user
  ON subscriptions (user_id)
  WHERE status = 'active';

-- ---------------------------------------------------------------------------
-- F-34: composite / partial indexes for known hot query shapes.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_rc_provider_detected
  ON rating_changes (provider_id, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_cp_region_rating_active
  ON care_providers (region, overall_rating)
  WHERE upper(status) = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_ae_user_created
  ON analytics_events (user_id, created_at DESC);
