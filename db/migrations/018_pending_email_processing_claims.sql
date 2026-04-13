-- Harden pending email delivery for concurrent workers and crash recovery.

ALTER TABLE pending_emails
  ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_pe_processing
  ON pending_emails (status, processing_started_at);
