import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, "../app/pricing/page.tsx"), "utf-8");

const ctaSrc = readFileSync(join(__dirname, "../components/PricingCTA.tsx"), "utf-8");

describe("pricing page — final catalogue regression", () => {
  it("does not contain hello@ mailto stub", () => {
    assert.ok(
      !src.includes("hello@caregist.co.uk"),
      "Legacy hello@ mailto found on pricing page"
    );
  });

  it("does not sell a provider-listing path", () => {
    assert.ok(
      !src.includes('href="/search?intent=claim"'),
      "Removed paid listing path found"
    );
    assert.ok(!src.includes("ProviderListingCTA"));
  });

  it("uses the catalogue-aware PricingCTA component", () => {
    assert.ok(
      src.includes("PricingCTA"),
      "PricingCTA not used in pricing page"
    );
  });

  it("keeps Feed and Embedded sales-assisted", () => {
    assert.ok(
      ctaSrc.includes("enterprise@caregist.co.uk"),
      "Sales-assisted mailto was removed"
    );
    assert.match(ctaSrc, /if \(!targetTier\)/);
  });
});
