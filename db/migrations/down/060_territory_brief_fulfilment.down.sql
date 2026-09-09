-- Reverse 060_territory_brief_fulfilment.sql

DROP TRIGGER IF EXISTS territory_brief_consents_immutable ON territory_brief_consents;
DROP FUNCTION IF EXISTS prevent_territory_brief_consent_mutation();
DROP TABLE IF EXISTS territory_brief_download_tokens;
DROP TABLE IF EXISTS territory_brief_consents;
DROP TABLE IF EXISTS territory_brief_orders;
