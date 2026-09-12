import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  buildDirectoryTextSearchClause,
  buildOpportunityClause,
  buildRatingClause,
  isNoPublishedRating,
  NO_PUBLISHED_RATING_CLAUSE,
} from "./directory-query-clauses.ts";

describe("directory query clauses", () => {
  it("matches the stored Requires improvement casing without depending on case", () => {
    const clause = buildOpportunityClause("requires_improvement");

    assert.match(clause, /lower\(btrim\(overall_rating\)\)/);
    assert.match(clause, /'requires improvement'/);
  });

  it("treats every unpublished rating representation as not yet inspected", () => {
    const clause = buildOpportunityClause("not_yet_inspected");

    assert.match(clause, /coalesce\(overall_rating, ''\)/);
    assert.match(clause, /'not yet inspected'/);
    assert.match(clause, /'no published rating'/);
    assert.doesNotMatch(clause, /good|outstanding/i);
  });

  it("keeps the exact no-published-rating token separate from missing data", () => {
    assert.equal(isNoPublishedRating("No published rating"), true);
    assert.equal(isNoPublishedRating(" no PUBLISHED rating "), true);
    assert.equal(isNoPublishedRating("Not Yet Inspected"), false);
    assert.equal(isNoPublishedRating(""), false);
    assert.equal(isNoPublishedRating(null), false);
    assert.equal(
      NO_PUBLISHED_RATING_CLAUSE,
      "lower(btrim(overall_rating)) = 'no published rating'",
    );
  });

  it("includes postcode in the HTML directory text-search predicate", () => {
    const clause = buildDirectoryTextSearchClause(1, 2, "provider_search_vector");

    assert.match(clause, /postcode ILIKE \$1/);
    assert.match(clause, /provider_search_vector @@ websearch_to_tsquery\('english', \$2\)/);
  });

  it("matches explicit rating filters without relying on display casing", () => {
    assert.equal(
      buildRatingClause(4),
      "lower(btrim(overall_rating)) = lower(btrim($4))",
    );
  });
});
