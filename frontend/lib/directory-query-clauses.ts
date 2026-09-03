import type { DirectoryOpportunity } from "./directory-constants.ts";

export const NO_PUBLISHED_RATING_CLAUSE =
  "lower(btrim(overall_rating)) = 'no published rating'";

export function isNoPublishedRating(value: string | null | undefined) {
  return (value ?? "").trim().toLowerCase() === "no published rating";
}

export function buildOpportunityClause(opportunity: DirectoryOpportunity | "") {
  switch (opportunity) {
    case "new_90":
      return "registration_date >= CURRENT_DATE - INTERVAL '90 days'";
    case "inadequate":
      return "overall_rating = 'Inadequate'";
    case "requires_improvement":
      return "lower(btrim(overall_rating)) = 'requires improvement'";
    case "not_yet_inspected":
      return "lower(btrim(coalesce(overall_rating, ''))) IN ('', 'not yet inspected', 'no published rating')";
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
  return `lower(btrim(overall_rating)) = lower(btrim($${paramIndex}))`;
}
