import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { getServicePage, getServicePageSlugs } from "./service-page-config.ts";

describe("service page configuration", () => {
  it("returns the canonical service mapping for known slugs", () => {
    assert.deepEqual(getServicePage("home-care"), {
      serviceType: "home-care",
      displayName: "Home Care Agencies",
    });
    assert.equal(getServicePageSlugs().length, 6);
  });

  it("rejects unknown and prototype-like slugs", () => {
    for (const slug of ["unknown", "constructor", "toString", "__proto__", "HOME-CARE"]) {
      assert.equal(getServicePage(slug), null);
    }
  });
});
