/**
 * Provider-page text that must follow the served rating (the CareGist rating rule),
 * not the rating the ETL wrote into `meta_description` when the row was built.
 */

const PUBLISHED_RATINGS = new Map(
  ["Outstanding", "Good", "Requires improvement", "Inadequate"].map((r) => [r.toLowerCase(), r]),
);

/** The served overall rating as display text, or null when none is published. */
export function publishedRating(value: string | null | undefined): string | null {
  return PUBLISHED_RATINGS.get((value ?? "").trim().toLowerCase()) ?? null;
}

/** A domain rating cell: blank and sentinel values read "Not published". */
export function domainRatingLabel(value: string | null | undefined): string {
  return publishedRating(value) ?? "Not published";
}

// prepare_directory.py writes "CQC rating: X." or "Latest CQC rating: X.".
const STORED_RATING_CLAUSE = /((?:Latest )?CQC rating: )[^.]*\./;

/**
 * The page's meta description with its rating clause replaced by the served
 * rating, so search snippets cannot contradict the page ("Not Yet Inspected"
 * beside an Outstanding badge).
 */
export function providerMetaDescription(provider: {
  name: string;
  type: string | null;
  town: string | null;
  overall_rating: string | null;
  meta_description: string | null;
}): string {
  const rating = publishedRating(provider.overall_rating);
  const stored = provider.meta_description?.trim();
  if (stored) {
    return STORED_RATING_CLAUSE.test(stored)
      ? stored.replace(STORED_RATING_CLAUSE, rating ? `$1${rating}.` : "No published CQC rating.")
      : stored;
  }
  const base = `${provider.name} is a CQC-registered ${provider.type?.toLowerCase() ?? "care provider"} in ${
    provider.town ?? "England"
  }.`;
  return rating ? `${base} CQC rating: ${rating}.` : base;
}
