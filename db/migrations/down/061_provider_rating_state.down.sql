-- Reverses 061_provider_rating_state.sql exactly: the column is additive, so
-- dropping it restores the previous schema. No data is restored because no
-- pre-existing data was modified (overall_rating is untouched by the forward
-- migration).
ALTER TABLE care_providers DROP COLUMN IF EXISTS rating_state;
