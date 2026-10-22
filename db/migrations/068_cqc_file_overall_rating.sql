-- Additive: keep the overall rating from CQC's published "Latest ratings"
-- file as its own labelled evidence, separate from the API-derived column.
--
-- Why: for ~141 locations CQC's public API returns no currentRatings block
-- while CQC's own published ratings file (care directory with ratings) lists an
-- overall rating. Reporting "no rating published" for those would be a false gap
-- about the source. overall_rating is NOT touched here: it still mirrors the API.
-- These columns record what the file said, when CQC published that rating, and
-- which file (by sha256) it came from, so every value is citable.
--
-- Nothing is inferred: rows only gain a value that appears verbatim in the file
-- (importer: tools/import_cqc_latest_ratings.py). Idempotent.

ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS file_overall_rating TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS file_overall_rating_date DATE;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS file_rating_source TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS file_rating_source_sha256 TEXT;
