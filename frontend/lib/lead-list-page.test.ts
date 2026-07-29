import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { buildLeadListDefaults, buildLeadListExportHref } from "./lead-list-page.ts";

describe("buildLeadListDefaults", () => {
  it("preserves filtered search params for the lead request form", () => {
    assert.deepEqual(
      buildLeadListDefaults({
        region: " London ",
        service_type: " Homecare Agencies ",
        rating: "Good",
        opportunity: "new_90",
      }),
      {
        region: "London",
        serviceType: "Homecare Agencies",
        rating: "Good",
        opportunity: "new_90",
      },
    );
  });

  it("uses the first value for repeated query params", () => {
    assert.deepEqual(
      buildLeadListDefaults({
        region: ["North West", "London"],
        service_type: ["Residential homes"],
        rating: ["Outstanding", "Good"],
        opportunity: ["inadequate", "new_90"],
      }),
      {
        region: "North West",
        serviceType: "Residential homes",
        rating: "Outstanding",
        opportunity: "inadequate",
      },
    );
  });

  it("ignores unknown opportunity params", () => {
    assert.equal(buildLeadListDefaults({ opportunity: "old_news" }).opportunity, "");
  });
});

describe("buildLeadListExportHref", () => {
  it("includes token and selected segment", () => {
    assert.equal(
      buildLeadListExportHref("tok_123", {
        region: "London",
        serviceType: "Homecare Agencies",
        rating: "Good",
        opportunity: "new_90",
      }),
      "/api/export?token=tok_123&region=London&service_type=Homecare+Agencies&rating=Good&opportunity=new_90",
    );
  });
});
