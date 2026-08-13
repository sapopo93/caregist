DROP TABLE IF EXISTS crm_email_events;
DROP TABLE IF EXISTS crm_phone_screening_events;
DROP TABLE IF EXISTS crm_phone_screening_cache;
DROP TABLE IF EXISTS crm_phone_screening_imports;
DROP TABLE IF EXISTS crm_call_intelligence;
DROP TABLE IF EXISTS crm_recordings;
DROP TABLE IF EXISTS crm_email_deliveries;
DROP TABLE IF EXISTS crm_email_campaigns;

DROP INDEX IF EXISTS uq_pending_emails_provider_message;
ALTER TABLE pending_emails DROP COLUMN IF EXISTS provider_message_id;

ALTER TABLE crm_activities DROP CONSTRAINT IF EXISTS crm_activities_activity_type_check;
ALTER TABLE crm_activities ADD CONSTRAINT crm_activities_activity_type_check CHECK (
  activity_type IN ('contact_created', 'note', 'task_created', 'task_completed', 'call', 'deal_created', 'deal_stage_changed', 'suppressed')
);
ALTER TABLE crm_suppressions DROP CONSTRAINT IF EXISTS crm_suppressions_reason_check;
ALTER TABLE crm_suppressions ADD CONSTRAINT crm_suppressions_reason_check CHECK (
  reason IN ('contact_objection', 'tps', 'ctps', 'invalid', 'legal', 'manual')
);

ALTER TABLE crm_call_sessions
  DROP COLUMN IF EXISTS recording_notice_version,
  DROP COLUMN IF EXISTS dispositioned_at;
ALTER TABLE crm_contacts
  DROP COLUMN IF EXISTS phone_screened_at,
  DROP COLUMN IF EXISTS phone_screening_evidence,
  DROP COLUMN IF EXISTS phone_screening_status,
  DROP COLUMN IF EXISTS email_marketing_recorded_at,
  DROP COLUMN IF EXISTS email_marketing_evidence,
  DROP COLUMN IF EXISTS email_marketing_basis,
  DROP COLUMN IF EXISTS subscriber_type,
  DROP COLUMN IF EXISTS market_code;
