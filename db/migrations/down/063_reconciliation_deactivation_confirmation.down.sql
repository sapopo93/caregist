-- Reverses 063_reconciliation_deactivation_confirmation.sql exactly: both
-- columns are additive and hold records of a completed batch, not canonical
-- truth, so dropping them restores the previous schema.
ALTER TABLE reconciliation_batches DROP COLUMN IF EXISTS deactivation_confirmation;
ALTER TABLE reconciliation_batches DROP COLUMN IF EXISTS deactivation_unconfirmed_count;
