import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  canonicalServices,
  canonicalSlugsWithLiveRows,
  canonicalizeServiceCounts,
  resolveServiceAliases,
  serviceTypeLabel,
} from "./service-taxonomy.ts";

// Distinct service_types values across ACTIVE care_providers, read from production on 2026-10-29.
const LIVE_SERVICE_LABELS = [
  "Care home service without nursing",
  "Supported living service",
  "Care home service with nursing",
  "Community healthcare service",
  "Acute services without overnight beds / listed acute services with or without overnight beds",
  "Acute services with overnight beds",
  "Extra Care housing services",
  "Hospital services for people with mental health needs, learning disabilities and problems with substance misuse",
  "Community based services for people with mental health needs",
  "Remote clinical advice service",
  "Community based services for people who misuse substances",
  "Community based services for people with a learning disability",
  "Community health care services - Nurses Agency only",
  "Community health care services - Independent Midwives",
];

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

  it("maps the CQC Nurses Agency label to Community Nursing", () => {
    assert.ok(resolveServiceAliases("community-nursing").includes("Community health care services - Nurses Agency only"));
    assert.deepEqual(
      canonicalSlugsWithLiveRows(["Community health care services - Nurses Agency only"]),
      ["community-nursing"],
    );
  });

  it("offers only service types that have live rows", () => {
    const slugs = canonicalSlugsWithLiveRows(LIVE_SERVICE_LABELS);
    assert.ok(slugs.includes("community-nursing"));
    assert.ok(slugs.includes("acute-services"));
    assert.ok(slugs.includes("mental-health-hospitals"));
    assert.ok(!slugs.includes("clinics"), "Clinics has no live rows");
    assert.ok(!slugs.includes("hospitals"), "Hospitals is covered by acute and mental-health hospital services");
    assert.ok(!slugs.includes("supported-housing"), "Supported Housing has no live rows");
  });

  it("matches live labels case-insensitively and ignores surrounding whitespace", () => {
    assert.deepEqual(canonicalSlugsWithLiveRows(["  clinic  "]), ["clinics"]);
    assert.deepEqual(canonicalSlugsWithLiveRows([]), []);
  });
});
