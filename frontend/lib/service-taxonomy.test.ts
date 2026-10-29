import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { canonicalServices, canonicalizeServiceCounts, resolveServiceAliases, serviceTypeLabel } from "./service-taxonomy.ts";

describe("canonical service taxonomy", () => {
  it("covers every observed CQC source label exactly once", () => {
    const aliases = canonicalServices().flatMap((entry) => entry.aliases.map((alias) => alias.toLocaleLowerCase("en-GB")));
    assert.equal(aliases.length, 58);
    assert.equal(new Set(aliases).size, 58);
  });

  it("resolves canonical slugs and legacy labels to the same source aliases", () => {
    assert.deepEqual(resolveServiceAliases("home-care"), resolveServiceAliases("Homecare Agencies"));
  });

  it("aggregates legacy labels under a stable canonical slug", () => {
    const rows = canonicalizeServiceCounts([
      { service_type: "Homecare Agencies", provider_count: 100 },
      { service_type: "Domiciliary care service", provider_count: 5 },
    ]);
    assert.equal(rows.find((row) => row.service_type === "home-care")?.provider_count, 105);
  });
});

describe("service type labels", () => {
  it("uses display names instead of title-casing the slug", () => {
    assert.equal(serviceTypeLabel("blood-transplant"), "Blood and Transplant Services");
    assert.equal(serviceTypeLabel("primary-medical-care"), "GP and Primary Medical Services");
    assert.equal(serviceTypeLabel("Homecare Agencies"), "Homecare Agencies");
  });
});

describe("API short names share a slug with the CQC long-form names", () => {
  // The live directory rows hold CQC's long-form names; the fallback dataset holds
  // the API's short names. A slug with only a short name returned no live results.
  it("maps each short name to the long-form entry the live rows hold", () => {
    assert.deepEqual(resolveServiceAliases("Clinic"), resolveServiceAliases("acute-services"));
    assert.deepEqual(resolveServiceAliases("Hospital"), resolveServiceAliases("acute-services"));
    assert.deepEqual(resolveServiceAliases("Supported Housing"), resolveServiceAliases("extra-care-housing"));
    assert.ok(resolveServiceAliases("community-nursing").includes("Community health care services - Nurses Agency only"));
  });

  it("offers no slug that only short names can match", () => {
    const slugs = canonicalServices().map((entry) => entry.slug);
    for (const removed of ["clinics", "hospitals", "supported-housing"]) {
      assert.ok(!slugs.includes(removed), removed);
    }
  });
});
