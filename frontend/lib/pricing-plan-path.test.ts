import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizePricingPlanSlug, pricingPlanCardId } from "./pricing-plan-path.ts";

describe("retained pricing-plan path", () => {
  it("gives every public plan a stable pricing-card anchor", () => {
    assert.equal(pricingPlanCardId("Free"), "plan-free");
    assert.equal(pricingPlanCardId("Alerts Pro"), "plan-alerts-pro");
    assert.equal(pricingPlanCardId("Data Starter"), "plan-data-starter");
    assert.equal(pricingPlanCardId("Data Pro"), "plan-data-pro");
    assert.equal(pricingPlanCardId("Data Business"), "plan-data-business");
    assert.equal(pricingPlanCardId("Enterprise"), "plan-enterprise");
  });

  it("accepts retained login slugs and rejects unknown values", () => {
    assert.equal(normalizePricingPlanSlug("data-pro"), "data-pro");
    assert.equal(normalizePricingPlanSlug(" DATA BUSINESS "), "data-business");
    assert.equal(normalizePricingPlanSlug("enterprise-plus"), null);
    assert.equal(normalizePricingPlanSlug("../admin"), null);
    assert.equal(normalizePricingPlanSlug(null), null);
  });
});

