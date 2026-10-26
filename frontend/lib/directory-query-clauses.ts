import type { DirectoryOpportunity } from "./directory-constants.ts";

/**
 * Reconciled overall rating: the CQC API rating when it is a real published
 * rating, otherwise the rating in CQC's published ratings file (migration 068,
 * tools/import_cqc_latest_ratings.py), otherwise whatever the API stored.
 * The API wins when both exist: it is the live feed.
 */
export const RECONCILED_RATING_SQL = `(CASE
    WHEN lower(btrim(overall_rating)) IN ('outstanding', 'good', 'requires improvement', 'inadequate') THEN overall_rating
    WHEN file_overall_rating IS NOT NULL AND (site_check_rating IS NULL OR site_check_rating = file_overall_rating) THEN file_overall_rating
    ELSE overall_rating
  END)`;

/**
 * 'cqc_file' when the displayed rating came from the ratings file; 'cqc_file_disputed'
 * when the file has a rating that CQC's own page no longer showed when checked
 * (migration 069), so none is displayed; else null.
 */
export const RATING_SOURCE_SQL = `(CASE
    WHEN lower(btrim(overall_rating)) IN ('outstanding', 'good', 'requires improvement', 'inadequate') THEN NULL
    WHEN file_overall_rating IS NOT NULL AND (site_check_rating IS NULL OR site_check_rating = file_overall_rating) THEN 'cqc_file'
    WHEN file_overall_rating IS NOT NULL THEN 'cqc_file_disputed'
  END)`;

/** The date CQC published a rating served from the ratings file, else null. */
export const RATING_SOURCE_DATE_SQL = `(CASE
    WHEN lower(btrim(overall_rating)) IN ('outstanding', 'good', 'requires improvement', 'inadequate') THEN NULL
    WHEN file_overall_rating IS NOT NULL AND (site_check_rating IS NULL OR site_check_rating = file_overall_rating) THEN file_overall_rating_date::text
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
