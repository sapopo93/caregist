-- Irreversible privacy migration. Raw evidence and unsafe activation state are
-- deliberately not restored. Schema rollback is a no-op; claims require fresh
-- identity/authority verification before activation.
DO $$
BEGIN
  RAISE NOTICE 'Migration 042 is intentionally irreversible; no personal evidence was restored.';
END $$;
