-- Reverse migration for 036_event_intelligence_mlp.sql.
-- Run only during an approved rollback window.

DROP TABLE IF EXISTS location_signals;
DROP TABLE IF EXISTS market_events;
DROP TABLE IF EXISTS cqc_location_snapshots;
DROP TABLE IF EXISTS cqc_provider_snapshots;
DROP TABLE IF EXISTS cqc_snapshots;
