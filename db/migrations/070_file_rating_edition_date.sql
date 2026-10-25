-- Additive: record which edition of CQC's published "Latest ratings" file each
-- file-sourced rating came from.
--
-- Why: the staleness check (tools/check_file_ratings_freshness.py) used the
-- newest rating publication date inside the file as a stand-in for the file's
-- edition, so a brand-new file whose latest rating was published weeks earlier
-- looked part-aged on arrival. The edition is not reliably in the filename
-- (files have been imported as both ratings.ods and 2026-08-04_Latest_ratings.ods),
-- so the importer now takes it explicitly (--edition-date) and records it here.
-- Nothing here changes overall_rating or any file_* rating value. Idempotent.

ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS file_rating_edition_date DATE;
