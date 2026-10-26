import type { DirectoryOpportunity } from "./directory-constants.ts";

/**
 * Served overall rating under the CareGist rating rule (mirrors
 * api/queries/providers.py SERVED_RATING; tools/prepare_order.py must match this
 * text exactly):
 *   1. CQC's monthly ratings file is the main source (migrations 068, 070).
 *   2. A CQC page check made on or after the file edition wins where it differs
 *      (migration 069); a page showing no rating withholds it (NULL).
 *   3. Otherwise whatever the API stored (a published rating, or its sentinel
 *      text such as "Not yet inspected") -- the API fills only the file's gaps.
 */
export const RECONCILED_RATING_SQL = `(CASE
    WHEN site_check_rating IS NOT NULL AND site_check_rating IS DISTINCT FROM file_overall_rating AND (file_rating_edition_date IS NULL OR site_check_at::date >= file_rating_edition_date) THEN NULLIF(site_check_rating, 'none')
    WHEN file_overall_rating IS NOT NULL THEN file_overall_rating
    ELSE overall_rating
  END)`;

/**
 * Which source served the rating: 'cqc_website', 'cqc_website_unrated' (withheld
 * because CQC's page shows none), 'cqc_file' or 'cqc_api'; null when none did.
 */
export const RATING_SOURCE_SQL = `(CASE
    WHEN site_check_rating IS NOT NULL AND site_check_rating IS DISTINCT FROM file_overall_rating AND (file_rating_edition_date IS NULL OR site_check_at::date >= file_rating_edition_date) AND site_check_rating <> 'none' THEN 'cqc_website'
    WHEN site_check_rating IS NOT NULL AND site_check_rating IS DISTINCT FROM file_overall_rating AND (file_rating_edition_date IS NULL OR site_check_at::date >= file_rating_edition_date) THEN 'cqc_website_unrated'
    WHEN file_overall_rating IS NOT NULL THEN 'cqc_file'
    WHEN lower(btrim(overall_rating)) IN ('outstanding', 'good', 'requires improvement', 'inadequate') THEN 'cqc_api'
  END)`;

/** That source's date (YYYY-MM-DD): the page check, the file rating's publication, or the API's. */
export const RATING_SOURCE_DATE_SQL = `(CASE
    WHEN site_check_rating IS NOT NULL AND site_check_rating IS DISTINCT FROM file_overall_rating AND (file_rating_edition_date IS NULL OR site_check_at::date >= file_rating_edition_date) THEN site_check_at::date::text
    WHEN file_overall_rating IS NOT NULL THEN file_overall_rating_date::text
    WHEN lower(btrim(overall_rating)) IN ('outstanding', 'good', 'requires improvement', 'inadequate') THEN last_published_rating_date::text
  END)`;

export const NO_PUBLISHED_RATING_CLAUSE =
  `lower(btrim(${RECONCILED_RATING_SQL})) = 'no published rating'`;

export function isNoPublishedRating(value: string | null | undefined) {
  return (value ?? "").trim().toLowerCase() === "no published rating";
}

export function buildOpportunityClause(opportunity: DirectoryOpportunity | "") {
  switch (opportunity) {
    case "new_90":
      return "registration_date >= CURRENT_DATE - INTERVAL '90 days'";
    case "inadequate":
      return `${RECONCILED_RATING_SQL} = 'Inadequate'`;
    case "requires_improvement":
      return `lower(btrim(${RECONCILED_RATING_SQL})) = 'requires improvement'`;
    case "not_yet_inspected":
      return `lower(btrim(coalesce(${RECONCILED_RATING_SQL}, ''))) IN ('', 'not yet inspected', 'no published rating')`;
    case "stale_inspection":
      return "(last_inspection_date IS NULL OR last_inspection_date < CURRENT_DATE - INTERVAL '3 years')";
    default:
      return "";
  }
}

export function buildDirectoryTextSearchClause(
  ilikeIndex: number,
  tsQueryIndex: number,
  searchVector: string,
) {
  return `(
        name ILIKE $${ilikeIndex}
        OR town ILIKE $${ilikeIndex}
        OR county ILIKE $${ilikeIndex}
        OR postcode ILIKE $${ilikeIndex}
        OR region ILIKE $${ilikeIndex}
        OR service_types ILIKE $${ilikeIndex}
        OR specialisms ILIKE $${ilikeIndex}
        OR ${searchVector} @@ websearch_to_tsquery('english', $${tsQueryIndex})
      )`;
}

export function buildRatingClause(paramIndex: number) {
  return `lower(btrim(${RECONCILED_RATING_SQL})) = lower(btrim($${paramIndex}))`;
}

/**
 * Excludes CQC locations held in reconciliation_quarantined_locations
 * (migration 067) while unresolved. Quarantined rows stay ACTIVE but must not
 * enter public claims. There is deliberately no to_regclass guard: if the table
 * is missing the query errors, so callers that surface the error fail closed.
 */
export function buildNotQuarantinedClause(table = "care_providers") {
  return `NOT EXISTS (
        SELECT 1
        FROM reconciliation_quarantined_locations q
        WHERE q.location_id = ${table}.id
          AND q.resolved_at IS NULL
      )`;
}
