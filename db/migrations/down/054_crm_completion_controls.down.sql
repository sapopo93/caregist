ALTER TABLE crm_activities DROP CONSTRAINT IF EXISTS crm_activities_activity_type_check;
ALTER TABLE crm_activities ADD CONSTRAINT crm_activities_activity_type_check CHECK (
  activity_type IN (
    'contact_created', 'note', 'task_created', 'task_completed', 'call',
    'deal_created', 'deal_stage_changed', 'suppressed',
    'email_campaign_queued', 'email_unsubscribed', 'recording_available',
    'email_bounced', 'email_complained', 'phone_screened',
    'ai_evaluation_completed'
  )
);

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'crm_contacts', 'crm_deals', 'crm_tasks', 'crm_suppressions',
    'crm_call_sessions', 'crm_call_events', 'crm_activities',
    'crm_phone_screening_imports', 'crm_phone_screening_cache',
    'crm_phone_screening_events', 'crm_email_campaigns', 'crm_email_deliveries',
    'crm_email_events', 'crm_recordings', 'crm_call_intelligence'
  ] LOOP
    EXECUTE format('ALTER TABLE %I NO FORCE ROW LEVEL SECURITY', table_name);
  END LOOP;
END
$$;

DROP TABLE IF EXISTS crm_worker_heartbeats;
DROP TABLE IF EXISTS crm_ai_usage_attempts;
DROP POLICY IF EXISTS crm_recordings_health_policy ON crm_recordings;
DROP POLICY IF EXISTS crm_contacts_ai_policy ON crm_contacts;
DROP INDEX IF EXISTS idx_crm_call_intelligence_monthly_cost;
ALTER TABLE crm_call_intelligence
  DROP CONSTRAINT IF EXISTS crm_call_intelligence_external_user_check,
  DROP COLUMN IF EXISTS evaluation_latency_ms,
  DROP COLUMN IF EXISTS actual_cost_usd,
  DROP COLUMN IF EXISTS reserved_cost_usd,
  DROP COLUMN IF EXISTS cache_hit_input_tokens,
  DROP COLUMN IF EXISTS output_tokens,
  DROP COLUMN IF EXISTS input_tokens,
  DROP COLUMN IF EXISTS external_request_id,
  DROP COLUMN IF EXISTS external_user_id,
  DROP COLUMN IF EXISTS redaction_summary;

ALTER TABLE crm_call_sessions
  DROP CONSTRAINT IF EXISTS crm_call_sessions_callback_due_check,
  DROP CONSTRAINT IF EXISTS crm_call_sessions_disposition_group_check,
  DROP COLUMN IF EXISTS callback_due_at,
  DROP COLUMN IF EXISTS disposition_group;

DROP INDEX IF EXISTS idx_crm_contacts_company;
ALTER TABLE crm_call_intelligence
  DROP CONSTRAINT IF EXISTS fk_crm_intelligence_recording_tenant,
  DROP CONSTRAINT IF EXISTS fk_crm_intelligence_call_tenant;
ALTER TABLE crm_recordings DROP CONSTRAINT IF EXISTS fk_crm_recordings_call_tenant;
ALTER TABLE crm_email_events DROP CONSTRAINT IF EXISTS fk_crm_email_events_delivery_tenant;
ALTER TABLE crm_email_deliveries
  DROP CONSTRAINT IF EXISTS fk_crm_deliveries_contact_tenant,
  DROP CONSTRAINT IF EXISTS fk_crm_deliveries_campaign_tenant;
ALTER TABLE crm_phone_screening_events DROP CONSTRAINT IF EXISTS fk_crm_screening_events_contact_tenant;
ALTER TABLE crm_phone_screening_cache DROP CONSTRAINT IF EXISTS fk_crm_screening_cache_import_tenant;
ALTER TABLE crm_activities DROP CONSTRAINT IF EXISTS fk_crm_activities_contact_tenant;
ALTER TABLE crm_call_sessions DROP CONSTRAINT IF EXISTS fk_crm_calls_contact_tenant;
ALTER TABLE crm_tasks DROP CONSTRAINT IF EXISTS fk_crm_tasks_contact_tenant;
ALTER TABLE crm_deals DROP CONSTRAINT IF EXISTS fk_crm_deals_contact_tenant;
ALTER TABLE crm_contacts DROP CONSTRAINT IF EXISTS fk_crm_contacts_company_tenant;
ALTER TABLE crm_call_sessions DROP CONSTRAINT IF EXISTS uq_crm_call_sessions_org_id;
ALTER TABLE crm_recordings DROP CONSTRAINT IF EXISTS uq_crm_recordings_org_id;
ALTER TABLE crm_email_deliveries DROP CONSTRAINT IF EXISTS uq_crm_email_deliveries_org_id;
ALTER TABLE crm_email_campaigns DROP CONSTRAINT IF EXISTS uq_crm_email_campaigns_org_id;
ALTER TABLE crm_phone_screening_imports DROP CONSTRAINT IF EXISTS uq_crm_screening_imports_org_id;
ALTER TABLE crm_companies DROP CONSTRAINT IF EXISTS uq_crm_companies_org_id;
ALTER TABLE crm_contacts DROP CONSTRAINT IF EXISTS uq_crm_contacts_org_id;
ALTER TABLE crm_contacts DROP COLUMN IF EXISTS company_id;
DROP TABLE IF EXISTS crm_companies;
