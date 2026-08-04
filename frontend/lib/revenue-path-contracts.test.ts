import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

function source(path: string): string {
  return readFileSync(join(frontendRoot, path), "utf8");
}

describe("revenue path contracts", () => {
  it("uses document navigation for revenue-critical provider links", () => {
    const providerCard = source("components/ProviderCard.tsx");
    const feed = source("components/NewRegistrationFeedPanel.tsx");

    assert.match(providerCard, /<a href=\{providerHref\}/);
    assert.doesNotMatch(providerCard, /<Link href=\{providerHref\}/);
    assert.match(feed, /<a href=\{getProviderHref\(providerRef\)\}/);
    assert.doesNotMatch(feed, /<Link href=\{getProviderHref\(providerRef\)\}/);
  });

  it("reserves layout space for the visible cookie banner", () => {
    const banner = source("components/CookieConsent.tsx");
    const styles = source("app/globals.css");

    assert.match(banner, /new ResizeObserver\(reserveBannerSpace\)/);
    assert.match(banner, /--cookie-consent-offset/);
    assert.match(styles, /padding-bottom: var\(--cookie-consent-offset, 0px\)/);
  });

  it("does not advertise VAT charges while H-Kay is unregistered", () => {
    const publicPricingFiles = [
      "app/api/page.tsx",
      "app/dashboard/page.tsx",
      "app/pricing/page.tsx",
      "app/terms/page.tsx",
      "lib/caregist-config.ts",
    ];
    const combined = publicPricingFiles.map(source).join("\n");

    assert.doesNotMatch(combined, /\+\s*VAT|exclude(?:s|d)?\s+VAT|ex\s+VAT/i);
    assert.match(combined, /not currently VAT registered/);
    assert.match(combined, /VAT is not currently charged/);
  });
});
