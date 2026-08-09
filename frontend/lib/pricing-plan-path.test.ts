import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizePricingPlanSlug, pricingPlanCardId } from "./pricing-plan-path.ts";

describe("retained pricing-plan path", () => {
  it("gives every public plan a stable pricing-card anchor", () => {
    assert.equal(pricingPlanCardId("Free Directory"), "plan-free-directory");
    assert.equal(pricingPlanCardId("Radar Regional"), "plan-radar-regional");
    assert.equal(pricingPlanCardId("Radar National"), "plan-radar-national");
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
