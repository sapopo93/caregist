import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { parseDirectorySearchParams } from "./directory-filters.ts";

describe("parseDirectorySearchParams", () => {
  it("defaults pagination to 24 results per page on page 1", () => {
    const filters = parseDirectorySearchParams({});

    assert.equal(filters.query, "");
    assert.equal(filters.region, "");
    assert.equal(filters.serviceType, "");
    assert.equal(filters.rating, "");
    assert.equal(filters.opportunity, "");
    assert.equal(filters.page, 1);
    assert.equal(filters.perPage, 24);
    assert.equal(filters.offset, 0);
  });

  it("trims incoming filters and clamps invalid pages", () => {
    const filters = parseDirectorySearchParams({
      q: "  London  ",
      region: "  London ",
      service_type: " Homecare Agencies ",
      rating: " Good ",
      opportunity: " requires_improvement ",
      page: "0",
    });

    assert.equal(filters.query, "London");
    assert.equal(filters.region, "London");
    assert.equal(filters.serviceType, "Homecare Agencies");
    assert.equal(filters.rating, "Good");
    assert.equal(filters.opportunity, "requires_improvement");
    assert.equal(filters.page, 1);
    assert.equal(filters.offset, 0);
  });

  it("ignores unknown opportunity segments", () => {
    const filters = parseDirectorySearchParams({ opportunity: "latest_magic_list" });

    assert.equal(filters.opportunity, "");
  });

  it("calculates offsets for later pages", () => {
    const filters = parseDirectorySearchParams({ page: "3" });

    assert.equal(filters.page, 3);
    assert.equal(filters.offset, 48);
  });
});
