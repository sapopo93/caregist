DROP TABLE IF EXISTS dataset_download_tokens;
DROP TRIGGER IF EXISTS digital_content_consents_immutable ON digital_content_consents;
DROP FUNCTION IF EXISTS prevent_digital_content_consent_mutation();
DROP TABLE IF EXISTS digital_content_consents;
DROP TABLE IF EXISTS full_dataset_orders;
DROP TABLE IF EXISTS full_dataset_artifacts;
