-- Additive: record what CQC's own location page showed when a file-sourced rating
-- was checked against it.
--
-- Why: the published ratings file is periodic, so a rating copied from it can be
-- out of date by the time a customer looks (a read-only check of the 141 file-sourced
-- Inadequate locations on 23 Oct 2026 found 17 whose cqc.org.uk page no longer showed
-- Inadequate). A file rating is served only while it is unchecked or the page agreed;
-- a disagreeing one is withheld and labelled, never guessed at. Nothing here changes
-- overall_rating or file_overall_rating. 'none' means the page showed no rating.
-- Importer: tools/verify_file_ratings_against_site.py. Idempotent.

ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS site_check_rating TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS site_check_at TIMESTAMPTZ;
