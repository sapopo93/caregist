-- Non-production rollback for migration 049. Production uses forward fixes.

DROP TABLE IF EXISTS delivery_attempts;
DROP TABLE IF EXISTS delivery_cursors;
DROP TABLE IF EXISTS delivery_outbox;
DROP TABLE IF EXISTS delivery_subscriptions;
DROP TABLE IF EXISTS event_outcomes;
DROP TABLE IF EXISTS event_actions;
DROP TABLE IF EXISTS provider_list_items;
DROP TABLE IF EXISTS provider_lists;
DROP TABLE IF EXISTS saved_signal_views;
DROP TABLE IF EXISTS organization_subscriptions;
DROP TABLE IF EXISTS organization_members;
DROP TABLE IF EXISTS organizations;
DROP TABLE IF EXISTS event_explanations;
DROP TABLE IF EXISTS report_evidence_spans;
DROP TABLE IF EXISTS report_documents;

DROP FUNCTION IF EXISTS caregist_is_organization_member(UUID);
DROP FUNCTION IF EXISTS caregist_current_user_id();

ALTER TABLE care_providers
  DROP COLUMN IF EXISTS registered_manager_absent_date,
  DROP COLUMN IF EXISTS signal_checked_at;

DROP TABLE IF EXISTS cqc_location_index_entries;

ALTER TABLE trusted_event_ledger
  DROP CONSTRAINT IF EXISTS trusted_event_ledger_entity_level_valid,
  DROP CONSTRAINT IF EXISTS trusted_event_ledger_explanation_status_valid,
  DROP CONSTRAINT IF EXISTS trusted_event_ledger_snapshot_sha_valid,
  DROP COLUMN IF EXISTS public_event_id,
  DROP COLUMN IF EXISTS schema_version,
  DROP COLUMN IF EXISTS entity_level,
  DROP COLUMN IF EXISTS source_snapshot_id,
  DROP COLUMN IF EXISTS source_published_at,
  DROP COLUMN IF EXISTS source_checked_at,
  DROP COLUMN IF EXISTS source_url,
  DROP COLUMN IF EXISTS source_snapshot_sha256,
  DROP COLUMN IF EXISTS explanation_status;

DROP TABLE IF EXISTS source_snapshots;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_signup_purchase_intent_valid;
ALTER TABLE users
  ADD CONSTRAINT users_signup_purchase_intent_valid CHECK (
    (signup_intent_type IS NULL AND signup_intent_value IS NULL)
    OR (signup_intent_type = 'plan' AND signup_intent_value IN ('alerts-pro', 'data-starter', 'data-pro', 'data-business'))
    OR (signup_intent_type = 'provider_tier' AND signup_intent_value IN ('enhanced', 'sponsored'))
  );
