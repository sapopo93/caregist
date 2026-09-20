-- Additive: canonical CQC rating state for a provider location.
--
-- CQC returns three different shapes through currentRatings.overall.rating:
--   * a real published rating ("Outstanding"/"Good"/"Requires improvement"/
--     "Inadequate"),
--   * a sentinel string that is NOT a rating ("Not Yet Inspected",
--     "No Published Rating", "Inspected but not rated", casing variants),
--   * nothing at all (no currentRatings block, or no overall block in it).
--
-- Until now the pipeline wrote "" or the sentinel itself into
-- care_providers.overall_rating, so 24,486 rating_changed ledger events over
-- 2026-08-10..2026-09-19 carry no destination value (~20,966 of them from
-- "Not Yet Inspected" alone): representation churn was being recorded as rating
-- movement. overall_rating now holds a published rating only, and this column
-- records what the source actually said.
--
-- CLASSIFICATION AUTHORITY (must not disagree with the application):
-- this file classifies a value *stored in overall_rating* with exactly the
-- rules the application uses, which are declared once in
-- api/services/rating_states.py (PUBLISHED_RATING_VALUES and _SENTINEL_STATES)
-- and implemented in SQL below. tests/integration/test_migration_061_rating_state.py
-- runs this migration against real Postgres over the shared corpus
-- (tests/rating_corpus.py) and fails if any stored value classifies differently
-- here than it does through the payload classifier or classify_stored_rating.
-- There is deliberately NO `ELSE 'rated'` catch-all: an unrecognised value
-- resolves to 'unknown'. Classifying an unrecognised value as 'rated' would
-- assert a rating that was never published (reviewer finding, FIX 4), and
-- would also rewrite a row that ingestion had correctly left 'unknown'.
--
-- RE-RUN SAFETY: the backfill is one-time per row. It only touches rows whose
-- rating_state_source is still 'unclassified' (the column default) and stamps
-- every row it touches 'migration_061'; the pipeline stamps the rows it cleans
-- 'pipeline'. A second run therefore matches no row, and a row that ingestion
-- has classified is never rewritten from a stale overall_rating. Additive: no
-- column type change, no DROP, no row deletion, and overall_rating is never
-- rewritten here.

ALTER TABLE care_providers
  ADD COLUMN IF NOT EXISTS rating_state TEXT NOT NULL DEFAULT 'unknown';

-- Provenance of rating_state: 'unclassified' (never classified by anything),
-- 'migration_061' (classified once by the backfill below) or 'pipeline'
-- (written by ingestion from a payload). This is what makes the backfill
-- one-time and re-run safe.
ALTER TABLE care_providers
  ADD COLUMN IF NOT EXISTS rating_state_source TEXT NOT NULL DEFAULT 'unclassified';

UPDATE care_providers
   SET rating_state = CASE
         WHEN src.normalized IS NULL THEN 'unknown'
         WHEN src.normalized IN (
           'outstanding', 'good', 'requires improvement', 'inadequate'
         ) THEN 'rated'
         WHEN src.normalized IN (
           'not yet inspected', 'not inspected', 'awaiting inspection'
         ) THEN 'not_yet_inspected'
         WHEN src.normalized IN (
           'no published rating', 'not published', 'no rating',
           'rating not published'
         ) THEN 'not_published'
         WHEN src.normalized IN (
           'inspected but not rated', 'not rated', 'unrated'
         ) THEN 'unrated'
         WHEN src.normalized IN ('not applicable', 'n/a') THEN 'not_applicable'
         ELSE 'unknown'
       END,
       rating_state_source = 'migration_061'
  FROM (
    SELECT id,
           NULLIF(
             regexp_replace(lower(btrim(coalesce(overall_rating, ''))), '\s+', ' ', 'g'),
             ''
           ) AS normalized
      FROM care_providers
  ) AS src
 WHERE care_providers.id = src.id
   AND care_providers.rating_state_source = 'unclassified';
