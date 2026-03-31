-- Search hardening migration
-- Rebuild FTS index to include local_authority and address_line1
-- Already applied manually — this file is for reference/re-run safety

DROP INDEX IF EXISTS idx_search;
CREATE INDEX idx_search ON care_providers
  USING GIN (to_tsvector('english',
    coalesce(name,'') || ' ' ||
    coalesce(town,'') || ' ' ||
    coalesce(county,'') || ' ' ||
    coalesce(postcode,'') || ' ' ||
    coalesce(local_authority,'') || ' ' ||
    coalesce(address_line1,'') || ' ' ||
    coalesce(service_types,'') || ' ' ||
    coalesce(specialisms,'')
  ));
