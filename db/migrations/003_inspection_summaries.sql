-- Add inspection_summary column to care_providers
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS inspection_summary TEXT;

-- Generate summaries from existing data
UPDATE care_providers SET inspection_summary = NULL; -- Reset

-- Build summaries for providers with ratings
UPDATE care_providers
SET inspection_summary =
  name || ' is a ' ||
  LOWER(COALESCE(
    CASE
      WHEN service_types LIKE '%Residential Homes%' THEN 'residential care home'
      WHEN service_types LIKE '%Nursing Homes%' THEN 'nursing home'
      WHEN service_types LIKE '%Homecare%' THEN 'home care agency'
      WHEN service_types LIKE '%Doctors%' THEN 'GP surgery'
      WHEN service_types LIKE '%Dentist%' THEN 'dental practice'
      WHEN service_types LIKE '%Supported Living%' THEN 'supported living service'
      WHEN service_types LIKE '%Hospital%' THEN 'hospital'
      WHEN service_types LIKE '%Hospice%' THEN 'hospice'
      ELSE 'care provider'
    END, 'care provider'
  )) ||
  CASE WHEN number_of_beds > 0 THEN ' with ' || number_of_beds || ' beds' ELSE '' END ||
  ' in ' || COALESCE(town, 'England') ||
  CASE WHEN postcode IS NOT NULL THEN ' (' || postcode || ')' ELSE '' END ||
  '. ' ||
  CASE
    WHEN overall_rating = 'Outstanding' THEN 'CQC inspectors rated this service Outstanding overall'
    WHEN overall_rating = 'Good' THEN 'CQC inspectors rated this service Good overall'
    WHEN overall_rating = 'Requires Improvement' THEN 'CQC inspectors found this service Requires Improvement'
    WHEN overall_rating = 'Inadequate' THEN 'CQC inspectors rated this service Inadequate'
    ELSE 'This service has not yet been inspected by CQC'
  END ||
  CASE
    WHEN overall_rating IN ('Outstanding', 'Good', 'Requires Improvement', 'Inadequate') THEN
      '. Breakdown: Safe — ' || COALESCE(rating_safe, 'N/A') ||
      ', Effective — ' || COALESCE(rating_effective, 'N/A') ||
      ', Caring — ' || COALESCE(rating_caring, 'N/A') ||
      ', Responsive — ' || COALESCE(rating_responsive, 'N/A') ||
      ', Well-led — ' || COALESCE(rating_well_led, 'N/A')
    ELSE ''
  END ||
  '.' ||
  CASE
    WHEN last_inspection_date IS NOT NULL THEN
      ' Last inspected ' || TO_CHAR(last_inspection_date, 'DD Month YYYY') || '.'
    ELSE ''
  END ||
  CASE
    WHEN specialisms IS NOT NULL AND specialisms != '' THEN
      ' Specialises in: ' || REPLACE(LOWER(specialisms), '|', ', ') || '.'
    ELSE ''
  END ||
  CASE
    WHEN quality_score IS NOT NULL THEN
      ' CareGist quality score: ' || quality_score || '/100.'
    ELSE ''
  END
WHERE overall_rating IS NOT NULL AND overall_rating != '';

-- Also generate basic summaries for not-yet-inspected providers
UPDATE care_providers
SET inspection_summary =
  name || ' is a ' ||
  LOWER(COALESCE(
    CASE
      WHEN service_types LIKE '%Residential Homes%' THEN 'residential care home'
      WHEN service_types LIKE '%Nursing Homes%' THEN 'nursing home'
      WHEN service_types LIKE '%Homecare%' THEN 'home care agency'
      WHEN service_types LIKE '%Doctors%' THEN 'GP surgery'
      WHEN service_types LIKE '%Dentist%' THEN 'dental practice'
      WHEN service_types LIKE '%Supported Living%' THEN 'supported living service'
      ELSE 'care provider'
    END, 'care provider'
  )) ||
  CASE WHEN number_of_beds > 0 THEN ' with ' || number_of_beds || ' beds' ELSE '' END ||
  ' in ' || COALESCE(town, 'England') ||
  CASE WHEN postcode IS NOT NULL THEN ' (' || postcode || ')' ELSE '' END ||
  '. This service has not yet been inspected by CQC.' ||
  CASE
    WHEN specialisms IS NOT NULL AND specialisms != '' THEN
      ' Specialises in: ' || REPLACE(LOWER(specialisms), '|', ', ') || '.'
    ELSE ''
  END
WHERE overall_rating IS NULL OR overall_rating = '' OR overall_rating = 'Not Yet Inspected';
