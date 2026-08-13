DROP POLICY IF EXISTS crm_activities_tps_worker_policy ON crm_activities;
DROP POLICY IF EXISTS crm_screening_events_tps_worker_policy ON crm_phone_screening_events;
DROP POLICY IF EXISTS crm_screening_cache_tps_worker_policy ON crm_phone_screening_cache;
DROP POLICY IF EXISTS crm_screening_imports_tps_worker_policy ON crm_phone_screening_imports;
DROP POLICY IF EXISTS crm_suppressions_tps_worker_policy ON crm_suppressions;
DROP POLICY IF EXISTS crm_companies_tps_worker_policy ON crm_companies;
DROP POLICY IF EXISTS crm_contacts_tps_worker_policy ON crm_contacts;

DROP POLICY IF EXISTS crm_tps_jobs_health_policy ON crm_tps_screening_jobs;
DROP POLICY IF EXISTS crm_tps_settings_health_policy ON crm_tps_automation_settings;

DROP TABLE IF EXISTS crm_tps_usage_attempts;
DROP TABLE IF EXISTS crm_tps_screening_jobs;
DROP TABLE IF EXISTS crm_tps_automation_settings;

ALTER TABLE crm_phone_screening_events DROP CONSTRAINT crm_phone_screening_events_status_check;
ALTER TABLE crm_phone_screening_events ADD CONSTRAINT crm_phone_screening_events_status_check CHECK (
  status IN ('clear', 'tps', 'ctps', 'consent_override')
);

ALTER TABLE crm_phone_screening_cache DROP CONSTRAINT crm_phone_screening_cache_status_check;
ALTER TABLE crm_phone_screening_cache ADD CONSTRAINT crm_phone_screening_cache_status_check CHECK (
  status IN ('clear', 'tps', 'ctps')
);

ALTER TABLE crm_contacts DROP CONSTRAINT crm_contacts_phone_screening_status_check;
ALTER TABLE crm_contacts ADD CONSTRAINT crm_contacts_phone_screening_status_check CHECK (
  phone_screening_status IN ('unknown', 'clear', 'tps', 'ctps', 'consent_override')
);
