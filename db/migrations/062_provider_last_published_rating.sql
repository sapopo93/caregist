-- Additive: keep the last rating CQC published as its own labelled evidence.
--
-- Reviewer finding (FIX 1): the pipeline carried a previous published rating
-- forward into care_providers.overall_rating when the current payload published
-- no current rating, so the row kept asserting a rating the source had stopped
-- publishing. The current payload is the only authority for what is published
-- *now*: when it positively reports that no rating is published, overall_rating
-- is cleared (never filled from history), and the value that was there is kept
-- here, separately and named for what it is -- evidence about the past.
--
-- last_published_rating_date is the date the source published that rating and
-- is NULL when no date was observed. Nothing is invented here: no row gains a
-- rating value that was never observed, and the backfill below only copies a
-- value the application already classifies as a real published rating
-- (rating_state = 'rated', which 061 sets only from a published-vocabulary
-- value). Idempotent: guarded on last_published_rating IS NULL.

ALTER TABLE care_providers
  ADD COLUMN IF NOT EXISTS last_published_rating TEXT;

ALTER TABLE care_providers
  ADD COLUMN IF NOT EXISTS last_published_rating_date DATE;

UPDATE care_providers
   SET last_published_rating = btrim(overall_rating)
 WHERE rating_state = 'rated'
   AND last_published_rating IS NULL
   AND overall_rating IS NOT NULL
   AND btrim(overall_rating) <> '';
