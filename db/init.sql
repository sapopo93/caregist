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

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  password_hash VARCHAR(255) NOT NULL,
  stripe_customer_id VARCHAR(100),
  is_verified BOOLEAN DEFAULT false,
  verification_token VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_stripe ON users (stripe_customer_id);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  stripe_subscription_id VARCHAR(100) UNIQUE,
  stripe_price_id VARCHAR(100),
  tier VARCHAR(20) NOT NULL DEFAULT 'free',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  included_users INT NOT NULL DEFAULT 1,
  extra_seats INT NOT NULL DEFAULT 0,
  max_users INT NOT NULL DEFAULT 1,
  seat_price_gbp INT NOT NULL DEFAULT 0,
  current_period_end TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Link api_keys to users
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);

-- ============================================================
-- Phase 3: Growth tables (provider claims, reviews, enquiries)
-- ============================================================

-- New columns on care_providers for growth features
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS is_claimed BOOLEAN DEFAULT false;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS review_count INT DEFAULT 0;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS avg_review_rating DECIMAL(2,1);
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS enquiry_count INT DEFAULT 0;

-- Provider claims — growth flywheel: providers claim → invest → attract clients
CREATE TABLE IF NOT EXISTS provider_claims (
  id SERIAL PRIMARY KEY,
  provider_id VARCHAR(20) NOT NULL REFERENCES care_providers(id),
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  claimant_name VARCHAR(255) NOT NULL,
  claimant_email VARCHAR(255) NOT NULL,
  claimant_phone VARCHAR(20),
  claimant_role VARCHAR(100),
  organisation_name VARCHAR(255),
  proof_of_association TEXT,
  admin_notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  reviewed_at TIMESTAMP,
  reviewed_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_claims_provider ON provider_claims (provider_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON provider_claims (status);
CREATE INDEX IF NOT EXISTS idx_claims_email ON provider_claims (claimant_email);

-- Reviews — user-generated content layer
CREATE TABLE IF NOT EXISTS reviews (
  id SERIAL PRIMARY KEY,
  provider_id VARCHAR(20) NOT NULL REFERENCES care_providers(id),
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
  title VARCHAR(200) NOT NULL,
  body TEXT NOT NULL,
  reviewer_name VARCHAR(100) NOT NULL,
  reviewer_email VARCHAR(255) NOT NULL,
  relationship VARCHAR(50),
  visit_date DATE,
  admin_notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  moderated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviews_provider ON reviews (provider_id);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews (status);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews (rating);

-- Enquiries — lead-gen monetisation engine
CREATE TABLE IF NOT EXISTS enquiries (
  id SERIAL PRIMARY KEY,
  provider_id VARCHAR(20) NOT NULL REFERENCES care_providers(id),
  status VARCHAR(20) NOT NULL DEFAULT 'new',
  enquirer_name VARCHAR(255) NOT NULL,
  enquirer_email VARCHAR(255) NOT NULL,
  enquirer_phone VARCHAR(20),
  relationship VARCHAR(50),
  care_type VARCHAR(100),
  urgency VARCHAR(20) DEFAULT 'exploring',
  message TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  read_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_enquiries_provider ON enquiries (provider_id);
CREATE INDEX IF NOT EXISTS idx_enquiries_status ON enquiries (status);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions (user_id);

-- Outbound webhook subscriptions for Business and Enterprise plans
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  secret TEXT NOT NULL,
  events TEXT[] NOT NULL DEFAULT '{provider.rating_changed}',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_delivery_at TIMESTAMPTZ,
  delivery_failures INT NOT NULL DEFAULT 0,
  UNIQUE(user_id, url)
);

CREATE INDEX IF NOT EXISTS idx_ws_user ON webhook_subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_ws_active ON webhook_subscriptions (active) WHERE active = TRUE;

-- Password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id SERIAL PRIMARY KEY,
  token VARCHAR(10) NOT NULL,
  email VARCHAR(255) NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used BOOLEAN NOT NULL DEFAULT false,
  attempts INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reset_tokens_email ON password_reset_tokens (email, used);

-- Updated_at triggers for users and subscriptions
CREATE TRIGGER users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER subscriptions_updated_at
  BEFORE UPDATE ON subscriptions
  FOR EACH ROW
  EXECUTE FUNCTION update_timestamp();
