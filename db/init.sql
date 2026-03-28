-- CareGist PostgreSQL Schema
-- Requires PostGIS extension

CREATE EXTENSION IF NOT EXISTS postgis;

-- Care providers table
CREATE TABLE IF NOT EXISTS care_providers (
  id VARCHAR(20) PRIMARY KEY,
  provider_id VARCHAR(20),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(300) UNIQUE,
  type VARCHAR(100),
  status VARCHAR(20),
  registration_date DATE,
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  town VARCHAR(100),
  county VARCHAR(100),
  postcode VARCHAR(10),
  region VARCHAR(100),
  local_authority VARCHAR(100),
  country VARCHAR(50) DEFAULT 'England',
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  geom GEOMETRY(Point, 4326),
  phone VARCHAR(20),
  website VARCHAR(500),
  email VARCHAR(255),
  overall_rating VARCHAR(50),
  rating_safe VARCHAR(50),
  rating_effective VARCHAR(50),
  rating_caring VARCHAR(50),
  rating_responsive VARCHAR(50),
  rating_well_led VARCHAR(50),
  last_inspection_date DATE,
  inspection_report_url VARCHAR(500),
  service_types TEXT,
  specialisms TEXT,
  regulated_activities TEXT,
  number_of_beds INT,
  ownership_type VARCHAR(50),
  quality_score INT,
  quality_tier VARCHAR(20),
  meta_title VARCHAR(300),
  meta_description TEXT,
  geocode_source VARCHAR(20),
  data_source VARCHAR(50),
  data_attribution VARCHAR(200),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_updated TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_postcode ON care_providers (postcode);
CREATE INDEX IF NOT EXISTS idx_region ON care_providers (region);
CREATE INDEX IF NOT EXISTS idx_local_authority ON care_providers (local_authority);
CREATE INDEX IF NOT EXISTS idx_overall_rating ON care_providers (overall_rating);
CREATE INDEX IF NOT EXISTS idx_quality_tier ON care_providers (quality_tier);
CREATE INDEX IF NOT EXISTS idx_status ON care_providers (status);
CREATE INDEX IF NOT EXISTS idx_slug ON care_providers (slug);
CREATE INDEX IF NOT EXISTS idx_type ON care_providers (type);
CREATE INDEX IF NOT EXISTS idx_geom ON care_providers USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_search ON care_providers
  USING GIN (to_tsvector('english',
    coalesce(name,'') || ' ' ||
    coalesce(town,'') || ' ' ||
    coalesce(county,'') || ' ' ||
    coalesce(postcode,'') || ' ' ||
    coalesce(service_types,'') || ' ' ||
    coalesce(specialisms,'')
  ));

-- API keys for authentication
CREATE TABLE IF NOT EXISTS api_keys (
  id SERIAL PRIMARY KEY,
  key VARCHAR(64) UNIQUE NOT NULL,
  name VARCHAR(255),
  email VARCHAR(255),
  tier VARCHAR(20) DEFAULT 'free',
  rate_limit INT DEFAULT 100,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  last_used_at TIMESTAMP
);

-- Pipeline run tracking
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id SERIAL PRIMARY KEY,
  run_type VARCHAR(20) NOT NULL,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  records_added INT DEFAULT 0,
  records_updated INT DEFAULT 0,
  records_deactivated INT DEFAULT 0,
  status VARCHAR(20) DEFAULT 'running',
  error_message TEXT
);

-- Set timezone to UTC
SET timezone = 'UTC';

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER care_providers_updated_at
  BEFORE UPDATE ON care_providers
  FOR EACH ROW
  EXECUTE FUNCTION update_timestamp();

-- Insert a default dev API key
INSERT INTO api_keys (key, name, email, tier, rate_limit)
VALUES ('dev_key_change_me_in_production', 'Development Key', 'dev@caregist.co.uk', 'free', 100)
ON CONFLICT (key) DO NOTHING;
