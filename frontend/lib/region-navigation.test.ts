import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { DEFAULT_REGION_OPTIONS } from "./directory-constants.ts";
import {
  isSupportedRegion,
  regionLinks,
  regionServiceLinks,
  regionSlug,
  truncateForDisplay,
  unsupportedRegionMessage,
} from "./region-navigation.ts";
import { canonicalServices, resolveServiceAliases } from "./service-taxonomy.ts";

describe("region validation", () => {
  it("accepts exactly the nine England regions", () => {
    assert.equal(DEFAULT_REGION_OPTIONS.length, 9);
    for (const region of DEFAULT_REGION_OPTIONS) assert.equal(isSupportedRegion(region), true);
  });

  it("rejects unknown, empty and differently cased values", () => {
    for (const value of ["Atlantis", "", "london", "Yorkshire", "Scotland"]) {
      assert.equal(isSupportedRegion(value), false);
    }
  });

  it("builds the slugs the region page expects", () => {
    assert.equal(regionSlug("Yorkshire & Humberside"), "yorkshire-humberside");
    assert.equal(regionSlug("South East"), "south-east");
    assert.deepEqual(
      regionLinks().map((link) => link.href),
      [
        "/region/east",
        "/region/east-midlands",
        "/region/london",
        "/region/north-east",
        "/region/north-west",
        "/region/south-east",
        "/region/south-west",
        "/region/west-midlands",
        "/region/yorkshire-humberside",
      ],
    );
  });
});

describe("unsupportedRegionMessage", () => {
  it("is null for a valid or missing region", () => {
    assert.equal(unsupportedRegionMessage(""), null);
    assert.equal(unsupportedRegionMessage("West Midlands"), null);
  });

  it("names the value and the nine regions", () => {
    assert.equal(
      unsupportedRegionMessage("Atlantis"),
      "CareGist covers the nine England regions that CQC reports on. “Atlantis” is not one of them.",
    );
  });

  it("caps a long value at 40 characters", () => {
    const message = unsupportedRegionMessage("A".repeat(200)) ?? "";
    assert.ok(message.includes(`“${"A".repeat(40)}…”`));
    assert.ok(!message.includes("A".repeat(41)));
  });

  it("keeps markup as plain text for React to escape", () => {
    const message = unsupportedRegionMessage("<script>x</script>") ?? "";
    assert.ok(message.includes("<script>x</script>"));
  });
});

describe("truncateForDisplay", () => {
  it("leaves short text alone and shortens long text", () => {
    assert.equal(truncateForDisplay("Atlantis"), "Atlantis");
    assert.equal(truncateForDisplay("x".repeat(40)), "x".repeat(40));
    assert.equal(truncateForDisplay("x".repeat(41)), `${"x".repeat(40)}…`);
  });

  it("does not split a character made of two code units", () => {
    const value = "\u{1F600}".repeat(45);
    assert.equal(Array.from(truncateForDisplay(value)).length, 41);
  });
});

describe("regionServiceLinks", () => {
  const links = regionServiceLinks("Yorkshire & Humberside");

  it("covers care homes, nursing homes, home care, supported living and GP surgeries", () => {
    const types = links.map((link) => link.serviceType);
    for (const expected of ["residential-care-homes", "nursing-care-homes", "home-care", "supported-living", "primary-medical-care"]) {
      assert.ok(types.includes(expected), expected);
    }
  });

  it("uses only canonical service slugs that the search filter resolves", () => {
    const slugs = new Set(canonicalServices().map((entry) => entry.slug));
    for (const link of links) {
      assert.ok(slugs.has(link.serviceType), link.serviceType);
      assert.ok(resolveServiceAliases(link.serviceType).length > 0);
    }
  });

  it("encodes the region and service type in the search URL", () => {
    const home = links.find((link) => link.serviceType === "home-care");
    assert.equal(home?.href, "/search?region=Yorkshire+%26+Humberside&service_type=home-care");
  });

  it("carries no pricing or checkout paths", () => {
    for (const link of links) assert.doesNotMatch(link.href, /pricing|checkout|billing/);
  });
});
