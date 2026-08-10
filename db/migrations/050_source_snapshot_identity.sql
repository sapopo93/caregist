-- Repair source snapshot identity on databases where migration 049 found a
-- pre-existing source_snapshots table and CREATE TABLE IF NOT EXISTS therefore
-- did not add UNIQUE (source_type, checksum_sha256).

LOCK TABLE source_snapshots IN SHARE ROW EXCLUSIVE MODE;

CREATE TEMP TABLE source_snapshot_duplicates ON COMMIT DROP AS
SELECT id,
       MIN(id) OVER (PARTITION BY source_type, checksum_sha256) AS canonical_id
FROM source_snapshots;

UPDATE trusted_event_ledger AS event
SET source_snapshot_id = duplicate.canonical_id
FROM source_snapshot_duplicates AS duplicate
WHERE event.source_snapshot_id = duplicate.id
  AND duplicate.id <> duplicate.canonical_id;

UPDATE cqc_location_index_entries AS entry
SET last_snapshot_id = duplicate.canonical_id
FROM source_snapshot_duplicates AS duplicate
WHERE entry.last_snapshot_id = duplicate.id
  AND duplicate.id <> duplicate.canonical_id;

UPDATE report_documents AS document
SET source_snapshot_id = duplicate.canonical_id
FROM source_snapshot_duplicates AS duplicate
WHERE document.source_snapshot_id = duplicate.id
  AND duplicate.id <> duplicate.canonical_id;

DELETE FROM source_snapshots AS snapshot
USING source_snapshot_duplicates AS duplicate
WHERE snapshot.id = duplicate.id
  AND duplicate.id <> duplicate.canonical_id;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_index AS index_record
    JOIN pg_class AS table_record ON table_record.oid = index_record.indrelid
    JOIN pg_namespace AS namespace_record ON namespace_record.oid = table_record.relnamespace
    WHERE namespace_record.nspname = 'public'
      AND table_record.relname = 'source_snapshots'
      AND index_record.indisunique
      AND index_record.indpred IS NULL
      AND index_record.indexprs IS NULL
      AND (
        SELECT ARRAY_AGG(attribute_record.attname ORDER BY key_record.ordinality)
        FROM UNNEST(index_record.indkey::SMALLINT[]) WITH ORDINALITY
          AS key_record(attnum, ordinality)
        JOIN pg_attribute AS attribute_record
          ON attribute_record.attrelid = table_record.oid
         AND attribute_record.attnum = key_record.attnum
      ) = ARRAY['source_type', 'checksum_sha256']::NAME[]
  ) THEN
    CREATE UNIQUE INDEX uniq_source_snapshots_identity
      ON source_snapshots (source_type, checksum_sha256);
  END IF;
END $$;
