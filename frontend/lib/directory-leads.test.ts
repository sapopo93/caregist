import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizeLeadRequest } from "./directory-leads.ts";

describe("normalizeLeadRequest", () => {
  it("normalizes email and trims optional filters", () => {
    const lead = normalizeLeadRequest({
      email: "  BUYER@Example.com ",
      region: " London ",
      serviceType: " Homecare Agencies ",
      rating: " Good ",
      opportunity: " new_90 ",
    });

    assert.deepEqual(lead, {
      email: "buyer@example.com",
      region: "London",
      serviceType: "Homecare Agencies",
      rating: "Good",
      opportunity: "new_90",
    });
  });

  it("rejects empty emails", () => {
    assert.throws(() => normalizeLeadRequest({ email: "   " }), /email is required/i);
  });

  it("rejects invalid emails", () => {
    assert.throws(
      () => normalizeLeadRequest({ email: "not-an-email", opportunity: "new_90" }),
      /valid email/i,
    );
  });

  it("rejects oversized lead fields before database or email use", () => {
    assert.throws(
      () => normalizeLeadRequest({ email: `${"a".repeat(250)}@example.com`, region: "London" }),
      /email is too long/i,
    );
    assert.throws(
      () => normalizeLeadRequest({ email: "buyer@example.com", region: "x".repeat(161) }),
      /filter is too long/i,
    );
  });

  it("rejects unscoped export requests", () => {
    assert.throws(
      () => normalizeLeadRequest({ email: "buyer@example.com" }),
      /choose at least one/i,
    );
  });

  it("ignores unknown opportunity values", () => {
    const lead = normalizeLeadRequest({
      email: "buyer@example.com",
      region: "London",
      opportunity: "wrong",
    });

    assert.equal(lead.opportunity, "");
    assert.equal(lead.region, "London");
  });
});
