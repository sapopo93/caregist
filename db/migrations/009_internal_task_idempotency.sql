ALTER TABLE internal_tasks
ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_tasks_idempotency_key
    ON internal_tasks (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
