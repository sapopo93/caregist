import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { PRICING_LADDER, PROVIDER_TIERS } from "./caregist-config.ts";

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

  it("keeps every checkout-backed public price aligned with the approved monthly ladder", () => {
    const dataPrices = Object.fromEntries(PRICING_LADDER.map(({ tier, price }) => [tier, price]));
    assert.deepEqual(dataPrices, {
      Free: "£0",
      "Alerts Pro": "£49/mo",
      "Data Starter": "£99/mo",
      "Data Pro": "£199/mo",
      "Data Business": "£499/mo",
      Enterprise: "Contact us",
    });

    const providerPrices = Object.fromEntries(PROVIDER_TIERS.map(({ tier, price }) => [tier, price]));
    assert.deepEqual(providerPrices, {
      claimed: "£0",
      enhanced: "£99/location/mo",
      sponsored: "£149/location/mo",
      enterprise: "Contact",
    });
  });

  it("carries retained login plan intent to a stable, focused pricing card", () => {
    const login = source("app/login/page.tsx");
    const pricing = source("app/pricing/page.tsx");
    const retainedFocus = source("components/RetainedPlanFocus.tsx");

    assert.match(login, /\/pricing\?highlight=\$\{upgrade\}/);
    assert.match(pricing, /id=\{pricingPlanCardId\(tier\.tier\)/);
    assert.match(pricing, /<RetainedPlanFocus \/>/);
    assert.match(retainedFocus, /searchParams\.get\("highlight"\)/);
    assert.match(retainedFocus, /scrollIntoView/);
    assert.match(retainedFocus, /card\.focus/);
  });

  it("does not spend a Free user's product allowance on unavailable feed controls", () => {
    const feed = source("components/NewRegistrationFeedPanel.tsx");

    assert.match(
      feed,
      /if \(tier === "free"\) \{[\s\S]*?return;[\s\S]*?\}[\s\S]*?void loadSavedFilters\(\);[\s\S]*?void loadDigest\(\);/,
    );
  });
});
