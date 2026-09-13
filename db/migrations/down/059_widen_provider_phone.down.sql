-- Narrowing back to VARCHAR(20) will fail if any stored value is longer, which
-- is the point: the pipeline halt this migration fixed would return.
ALTER TABLE care_providers ALTER COLUMN phone TYPE VARCHAR(20);
