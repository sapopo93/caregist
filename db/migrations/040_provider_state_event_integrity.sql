-- Make the trusted ledger authoritative for CQC location state transitions.
-- rating_changes remains a compatibility projection for existing monitors.

ALTER TABLE trusted_event_ledger
  ADD COLUMN IF NOT EXISTS source_observed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_tel_location_type_effective
  ON trusted_event_ledger (location_id, event_type, effective_date DESC);

ALTER TABLE rating_changes
  ADD COLUMN IF NOT EXISTS event_dedupe_key TEXT;

ALTER TABLE cqc_location_snapshots
  ADD COLUMN IF NOT EXISTS ownership_type TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_rating_changes_event_dedupe
  ON rating_changes (event_dedupe_key)
  WHERE event_dedupe_key IS NOT NULL;

COMMENT ON COLUMN trusted_event_ledger.source_observed_at IS
  'Timestamp supplied by the CQC source record; observed_at is CareGist ingestion time.';

COMMENT ON COLUMN rating_changes.event_dedupe_key IS
  'Trusted-event-ledger key for the compatibility projection; prevents replay duplicates.';
