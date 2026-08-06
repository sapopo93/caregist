import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { canonicalServices, canonicalizeServiceCounts, resolveServiceAliases } from "./service-taxonomy.ts";

describe("canonical service taxonomy", () => {
  it("covers every observed CQC source label exactly once", () => {
    const aliases = canonicalServices().flatMap((entry) => entry.aliases.map((alias) => alias.toLocaleLowerCase("en-GB")));
    assert.equal(aliases.length, 57);
    assert.equal(new Set(aliases).size, 57);
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
