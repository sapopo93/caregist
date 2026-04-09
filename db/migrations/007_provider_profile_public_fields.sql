-- Provider public profile metadata fields used by the dashboard and public page

ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS logo_url TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS funding_types TEXT[];
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS fee_guidance TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS min_visit_duration TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS contract_types TEXT[];
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS age_ranges TEXT[];

COMMENT ON COLUMN care_providers.profile_tier IS
  'NULL=free/unclaimed, claimed=free claimed listing, enhanced=paid enhanced, premium=paid premium, sponsored=paid sponsored';
