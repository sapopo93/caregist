-- Remove only the named repair index. Databases that received the original
-- migration-049 table constraint retain that constraint.
DROP INDEX IF EXISTS uniq_source_snapshots_identity;
