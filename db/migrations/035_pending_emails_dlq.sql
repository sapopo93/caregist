-- F-44: bound pending_emails growth and support dead-letter scans.
--
-- * Cap html_body size so a runaway template can't bloat the table (NOT VALID
--   so the migration never fails on a pre-existing oversized row; new/updated
--   rows are checked immediately).
-- * Index status + created_at for the dead-letter query (failed rows older than
--   a cutoff).

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'pending_emails_html_body_size'
  ) THEN
    ALTER TABLE pending_emails
      ADD CONSTRAINT pending_emails_html_body_size
      CHECK (octet_length(html_body) <= 1000000)
      NOT VALID;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_pe_failed_created
  ON pending_emails (status, created_at)
  WHERE status = 'failed';
