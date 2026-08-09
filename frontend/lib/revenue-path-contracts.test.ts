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
      "Free Directory": "£0",
      "Radar Regional": "£299/mo",
      "Radar National": "£799/mo",
      "Intelligence Feed Pilot": "From £6,000/yr",
      "Embedded Enterprise": "Annual quote",
    });

    const providerPrices = Object.fromEntries(PROVIDER_TIERS.map(({ tier, price }) => [tier, price]));
    assert.deepEqual(providerPrices, {
      claimed: "£0",
      enhanced: "Existing subscription",
      sponsored: "Existing subscription",
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
    const dashboard = source("app/dashboard/page.tsx");

    assert.match(feed, /if \(!capabilities\.feed\)/);
    assert.match(feed, /if \(capabilities\.savedFilters\) void loadSavedFilters\(\)/);
    assert.match(feed, /if \(capabilities\.digest\) void loadDigest\(\)/);
    assert.match(dashboard, /subscriptionReady \? \(/);
  });

  it("removes paid provider-listing checkout while preserving free claims", () => {
    const providerDashboard = source("app/provider-dashboard/[slug]/page.tsx");

    assert.match(providerDashboard, /Provider claims and corrections are free/);
    assert.doesNotMatch(providerDashboard, /profile-checkout/);
  });

  it("offers a plan/seat change action on the current account plan, not a second charge", () => {
    // Existing subscriptions are no longer fail-closed to "contact support" —
    // POST /api/v1/billing/checkout now resolves an existing subscription's
    // change through the concurrency-safe billing_operations ledger instead
    // of opening a second Stripe subscription. The dashboard's "Current
    // Plan" state reuses the same handleUpgrade action for that change.
    const pricingCta = source("components/PricingCTA.tsx");
    const currentPlanBranch = pricingCta.match(
      /if \(user && isCurrentTier\) \{([\s\S]*?)if \(user && currentRank < targetRank/,
    );

    assert.ok(currentPlanBranch);
    assert.match(currentPlanBranch[1], /Current Plan/);
    assert.match(currentPlanBranch[1], /handleUpgrade/);
  });

  it("does not render removed provider sales cards", () => {
    const dashboard = source("app/provider-dashboard/[slug]/page.tsx");

    assert.doesNotMatch(dashboard, /Provider Pro|Sponsored Listing|profile-checkout/);
  });

  it("backs the cancel-anytime promise with authenticated billing management", () => {
    const dashboard = source("app/dashboard/page.tsx");

    assert.match(dashboard, /fetch\("\/api\/v1\/billing\/portal"/);
    assert.match(dashboard, /Manage billing or cancel/);
  });
});
