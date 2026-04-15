import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, "../app/pricing/page.tsx"), "utf-8");

describe("pricing page — provider listing CTA regression", () => {
  it("does not contain hello@ mailto stub", () => {
    assert.ok(
      !src.includes("hello@caregist.co.uk"),
      "Legacy hello@ mailto found on pricing page"
    );
  });

  it("does not use static /search?intent=claim href", () => {
    assert.ok(
      !src.includes('href="/search?intent=claim"'),
      "Static search-intent href found — should use ProviderListingCTA"
    );
  });

  it("uses ProviderListingCTA component", () => {
    assert.ok(
      src.includes("ProviderListingCTA"),
      "ProviderListingCTA not used in pricing page"
    );
  });

  it("preserves enterprise mailto", () => {
    assert.ok(
      src.includes("enterprise@caregist.co.uk"),
      "Enterprise mailto was removed — must be preserved"
    );
  });
});
