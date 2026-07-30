DROP INDEX IF EXISTS uniq_rating_changes_event_dedupe;
ALTER TABLE cqc_location_snapshots DROP COLUMN IF EXISTS ownership_type;
ALTER TABLE rating_changes DROP COLUMN IF EXISTS event_dedupe_key;
DROP INDEX IF EXISTS idx_tel_location_type_effective;
ALTER TABLE trusted_event_ledger DROP COLUMN IF EXISTS source_observed_at;
