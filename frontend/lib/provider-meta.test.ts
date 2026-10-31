import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

import { domainRatingLabel, providerMetaDescription, publishedRating } from "./provider-meta.ts";

const base = { name: "Be Caring Leeds", type: "Social Care Org", town: "Leeds" };

describe("provider meta", () => {
  it("replaces a stale stored rating with the served rating", () => {
    const description = providerMetaDescription({
      ...base,
      overall_rating: "Outstanding",
      meta_description:
        "Be Caring Leeds provides domiciliary care services in Leeds. CQC rating: Not Yet Inspected. Covers: Dementia.",
    });
    assert.equal(
      description,
      "Be Caring Leeds provides domiciliary care services in Leeds. CQC rating: Outstanding. Covers: Dementia.",
    );
  });

  it("handles the 'Latest CQC rating' wording", () => {
    const description = providerMetaDescription({
      ...base,
      overall_rating: "Requires improvement",
      meta_description: "Care home in Leeds. Latest CQC rating: Good. Specialisms include dementia.",
    });
    assert.match(description, /Latest CQC rating: Requires improvement\./);
  });

  it("says no rating is published when the served rating is withheld or a sentinel", () => {
    for (const overall_rating of [null, "", "Not yet inspected", "No published rating"]) {
      const description = providerMetaDescription({
        ...base,
        overall_rating,
        meta_description: "Clinic in Leeds. CQC rating: Good. Covers: everyone.",
      });
      assert.equal(description, "Clinic in Leeds. No published CQC rating. Covers: everyone.");
    }
  });

  it("builds a description when none is stored", () => {
    assert.equal(
      providerMetaDescription({ ...base, overall_rating: "Good", meta_description: null }),
      "Be Caring Leeds is a CQC-registered social care org in Leeds. CQC rating: Good.",
    );
  });

  it("labels blank and sentinel domain ratings as not published", () => {
    assert.equal(domainRatingLabel(""), "Not published");
    assert.equal(domainRatingLabel(null), "Not published");
    assert.equal(domainRatingLabel("Not yet inspected"), "Not published");
    assert.equal(domainRatingLabel("good"), "Good");
    assert.equal(publishedRating(" Inadequate "), "Inadequate");
  });

  it("is wired into the provider page", () => {
    const source = readFileSync(new URL("../app/provider/[slug]/page.tsx", import.meta.url), "utf8");
    assert.match(source, /providerMetaDescription\(provider\)/);
    assert.match(source, /domainRatingLabel\(provider\[dimension\.key\]\)/);
    assert.doesNotMatch(source, /provider\[dimension\.key\] \?\? "Not published"/);
  });
});
