-- Reverses 075. Non-production verification only: a production recovery uses a
-- forward fix or a Neon recovery point (db/migrations/README.md). Running this
-- deletes every Operator History order and delivered file.
DROP TRIGGER IF EXISTS operator_history_artefacts_immutable ON operator_history_artefacts;
DROP TRIGGER IF EXISTS operator_history_orders_guard_trg ON operator_history_orders;
DROP TABLE IF EXISTS operator_history_artefacts;
DROP TABLE IF EXISTS operator_history_orders;
DROP FUNCTION IF EXISTS operator_history_artefacts_append_only();
DROP FUNCTION IF EXISTS operator_history_orders_guard();
