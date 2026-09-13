import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizePricingPlanSlug, pricingPlanCardId } from "./pricing-plan-path.ts";

describe("retained pricing-plan path", () => {
  it("gives each of the two saleable products a stable pricing-card anchor", () => {
    assert.equal(pricingPlanCardId("Weekly Digest"), "plan-weekly-digest");
    assert.equal(pricingPlanCardId("Territory Opportunity Brief"), "plan-territory-opportunity-brief");
    assert.equal(pricingPlanCardId("Free Directory"), "plan-free-directory");
  });

  it("keeps an anchor for withdrawn plans so an old link degrades instead of breaking", () => {
    assert.equal(pricingPlanCardId("Market Movement Report"), "plan-market-movement-report");
    assert.equal(pricingPlanCardId("Radar Regional"), "plan-radar-regional");
    assert.equal(pricingPlanCardId("Radar National"), "plan-radar-national");
    assert.equal(pricingPlanCardId("Strategic Territory Intelligence Assignment"), "plan-strategic-territory-intelligence-assignment");
    assert.equal(pricingPlanCardId("Founding Intelligence Membership"), "plan-founding-intelligence-membership");
    assert.equal(pricingPlanCardId("Intelligence Feed Pilot"), "plan-intelligence-feed-pilot");
    assert.equal(pricingPlanCardId("Embedded Enterprise"), "plan-embedded-enterprise");
  });

  it("accepts retained login slugs and rejects unknown values", () => {
    assert.equal(normalizePricingPlanSlug("radar-regional"), "radar-regional");
    assert.equal(normalizePricingPlanSlug(" RADAR NATIONAL "), "radar-national");
    assert.equal(normalizePricingPlanSlug("data-pro"), null);
    assert.equal(normalizePricingPlanSlug("enterprise-plus"), null);
    assert.equal(normalizePricingPlanSlug("../admin"), null);
    assert.equal(normalizePricingPlanSlug(null), null);
  });
});
