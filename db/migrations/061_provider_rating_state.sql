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
-- Existing rows default to 'unknown' so no row asserts anything about the
-- source that has not been observed. Idempotent and additive: no column type
-- change, no DROP, no row deletion, and overall_rating is never rewritten here.

ALTER TABLE care_providers
  ADD COLUMN IF NOT EXISTS rating_state TEXT NOT NULL DEFAULT 'unknown';

-- Classify existing rows from the value that is already stored, so a sentinel
-- stops being treated as a rating by readers that filter on rating_state.
-- Nothing is invented: a value that is not a published rating maps to the state
-- its own text names, everything else stays 'unknown', and only the new column
-- is written.
UPDATE care_providers
   SET rating_state = CASE
         WHEN overall_rating IS NULL OR btrim(overall_rating) = '' THEN 'unknown'
         WHEN lower(btrim(overall_rating)) = 'not yet inspected' THEN 'not_yet_inspected'
         WHEN lower(btrim(overall_rating)) = 'no published rating' THEN 'not_published'
         WHEN lower(btrim(overall_rating)) = 'inspected but not rated' THEN 'unrated'
         WHEN lower(btrim(overall_rating)) = 'not applicable' THEN 'not_applicable'
         ELSE 'rated'
       END
 WHERE rating_state = 'unknown';
