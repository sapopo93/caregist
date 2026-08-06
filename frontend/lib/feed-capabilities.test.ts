import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { feedCapabilitiesForTier } from "./feed-capabilities.ts";

describe("registration-feed capabilities", () => {
  it("gives Free only the feed preview", () => {
    assert.deepEqual(feedCapabilitiesForTier("free"), {
      feed: true,
      savedFilters: false,
      digest: false,
      export: false,
    });
  });

  it("does not load registration-feed APIs for Alerts Pro", () => {
    assert.deepEqual(feedCapabilitiesForTier("alerts-pro"), {
      feed: false,
      savedFilters: false,
      digest: false,
      export: false,
    });
  });

  it("enables the recurring feed workflow from Starter upward", () => {
    for (const tier of ["starter", "pro", "business", "enterprise"]) {
      assert.deepEqual(feedCapabilitiesForTier(tier), {
        feed: true,
        savedFilters: true,
        digest: true,
        export: true,
      });
    }
  });

  it("fails closed for unknown tiers", () => {
    assert.deepEqual(feedCapabilitiesForTier("tampered"), feedCapabilitiesForTier("alerts-pro"));
  });
});
