import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

import {
  RECONCILED_RATING_SQL,
  buildDirectoryTextSearchClause,
  buildOpportunityClause,
  buildRatingClause,
  isNoPublishedRating,
  NO_PUBLISHED_RATING_CLAUSE,
} from "./directory-query-clauses.ts";

describe("directory query clauses", () => {
  it("matches the stored Requires improvement casing without depending on case", () => {
    const clause = buildOpportunityClause("requires_improvement");

    assert.match(clause, /lower\(btrim\(\(CASE/);
    assert.match(clause, /'requires improvement'/);
  });

  it("treats every unpublished rating representation as not yet inspected", () => {
    const clause = buildOpportunityClause("not_yet_inspected");

    assert.match(clause, /coalesce\(\(CASE/);
    assert.match(clause, /'not yet inspected'/);
    assert.match(clause, /'no published rating'/);
    assert.doesNotMatch(clause.replace(RECONCILED_RATING_SQL, ""), /good|outstanding/i);
  });

  it("keeps the exact no-published-rating token separate from missing data", () => {
    assert.equal(isNoPublishedRating("No published rating"), true);
    assert.equal(isNoPublishedRating(" no PUBLISHED rating "), true);
    assert.equal(isNoPublishedRating("Not Yet Inspected"), false);
    assert.equal(isNoPublishedRating(""), false);
    assert.equal(isNoPublishedRating(null), false);
    assert.equal(
      NO_PUBLISHED_RATING_CLAUSE,
      `lower(btrim(${RECONCILED_RATING_SQL})) = 'no published rating'`,
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
      `lower(btrim(${RECONCILED_RATING_SQL})) = lower(btrim($4))`,
    );
  });
});

it("directory-db never selects the raw API rating column for display", () => {
  const source = readFileSync(new URL("./directory-db.ts", import.meta.url), "utf8");
  assert.doesNotMatch(source, /^\s+overall_rating,\s*$/m);
});
