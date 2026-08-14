import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { readFileSync } from "node:fs";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const appRoot = resolve(import.meta.dirname, "..");

function readAppFile(path: string) {
  return readFileSync(resolve(appRoot, path), "utf8");
}

describe("page contracts", () => {
  it("service-types API returns counted service type rows", () => {
    const source = readAppFile("app/api/v1/service-types/route.ts");

    assert.match(source, /getDirectoryServiceTypeCounts/);
    assert.doesNotMatch(source, /provider_count:\s*0/);
  });

  it("missing provider pages return a real 404", () => {
    const source = readAppFile("app/provider/[slug]/page.tsx");

    assert.match(source, /getProviderHref/);
    assert.match(source, /import\s+\{\s*notFound\s*\}\s+from\s+"next\/navigation"/);
    assert.match(source, /export async function generateMetadata[\s\S]*if\s*\(!provider\)\s*\{[\s\S]*notFound\(\);?[\s\S]*\}/);
    assert.match(source, /if\s*\(!provider\)\s*\{[\s\S]*notFound\(\);?[\s\S]*\}/);
    assert.equal(existsSync(resolve(appRoot, "app/provider/[slug]/loading.tsx")), false);
  });

  it("provider pages remove unavailable claim, enquiry, and review journeys", () => {
    const source = readAppFile("app/provider/[slug]/page.tsx");
    const structuredData = readAppFile("components/ProviderJsonLd.tsx");

    assert.doesNotMatch(source, /EnquiryForm|ReviewsSection|getProviderReviews/);
    assert.doesNotMatch(source, /lead-list|Want this segment as a CSV|Get a lead list/);
    assert.doesNotMatch(source, /\/claim\//);
    assert.match(source, /normalizeExternalHttpUrl/);
    assert.doesNotMatch(structuredData, /AggregateRating|reviewCount/);
  });

  it("removes unrelated and unavailable public routes", () => {
    assert.equal(existsSync(resolve(appRoot, "app/story-video/page.tsx")), false);
    assert.equal(existsSync(resolve(appRoot, "app/claim/[slug]/page.tsx")), false);
    assert.equal(existsSync(resolve(appRoot, "components/CityRatingPage.tsx")), false);
    assert.doesNotMatch(readAppFile("app/dashboard/page.tsx"), /Find a provider to claim|\/claim\//);
  });

  it("permanently retires the commodity lead-list page", () => {
    const source = readAppFile("app/lead-list/page.tsx");

    assert.match(source, /permanentRedirect\("\/pricing"\)/);
    assert.doesNotMatch(source, /LeadRequestForm|buildLeadListExportHref/);
  });

  it("does not advertise commodity provider exports on public directory pages", () => {
    const sources = [
      readAppFile("app/region/[slug]/page.tsx"),
      readAppFile("app/services/[slug]/page.tsx"),
    ].join("\n");

    assert.doesNotMatch(sources, /ExportCSVButton|providers\/export\.csv/);
  });

  it("retires the public review-policy surface with a permanent redirect", () => {
    const source = readAppFile("app/review-policy/page.tsx");

    assert.match(source, /permanentRedirect\("\/terms"\)/);
    assert.doesNotMatch(source, /star rating|submit a review|moderation/i);
  });

  it("export API maps token lookup failures to unauthorized responses", () => {
    const source = readAppFile("app/api/export/route.ts");
    const tryBlockStart = source.indexOf("try {");
    const tokenLookup = source.indexOf("await getExportScopeForToken");
    const catchBlockStart = source.indexOf("} catch");

    assert.ok(tryBlockStart >= 0);
    assert.ok(tokenLookup > tryBlockStart);
    assert.ok(tokenLookup < catchBlockStart);
  });

  it("removed lead intake is gone while historical directory export stays gated", () => {
    const exportSource = readAppFile("app/api/export/route.ts");
    const leadSource = readAppFile("app/api/leads/request/route.ts");

    assert.match(exportSource, /DIRECTORY_EXPORT_DELIVERY_ENABLED/);
    assert.match(exportSource, /status:\s*503/);
    assert.match(leadSource, /status:\s*410/);
    assert.doesNotMatch(leadSource, /DIRECTORY_LEAD_INTAKE_ENABLED|createLeadAndToken/);
  });

  it("keeps generated feed exports alive through the native save dialog", () => {
    const feedSource = readAppFile("components/NewRegistrationFeedPanel.tsx");

    assert.match(feedSource, /document\.body\.appendChild\(anchor\)/);
    assert.match(feedSource, /window\.addEventListener\("beforeunload"/);
    assert.doesNotMatch(feedSource, /anchor\.click\(\);\s*window\.URL\.revokeObjectURL\(url\)/);
  });

  it("paid checkout renders an explicit unavailable state until every gate is configured", () => {
    const pricingCtaSource = readAppFile("components/PricingCTA.tsx");
    const layoutSource = readAppFile("app/layout.tsx");

    assert.match(pricingCtaSource, /Paid checkout unavailable/);
    assert.match(pricingCtaSource, /business_use_confirmed/);
    assert.match(pricingCtaSource, /terms_version/);
    assert.doesNotMatch(layoutSource, /STRIPE_PAYMENT_LINK_URL/);
  });

  it("keeps provider-result navigation on reliable document requests", () => {
    const feedSource = readAppFile("components/NewRegistrationFeedPanel.tsx");
    const cardSource = readAppFile("components/ProviderCard.tsx");
    const directoryCardSource = readAppFile("components/directory/DirectoryProviderCard.tsx");

    assert.match(feedSource, /<a href=\{getProviderHref\(providerRef\)\}/);
    assert.match(cardSource, /<a href=\{providerHref\}/);
    assert.match(directoryCardSource, /<a href=\{href\}/);
  });

  it("reserves page space for the cookie banner instead of covering actions", () => {
    const consentSource = readAppFile("components/CookieConsent.tsx");
    const globalStyles = readAppFile("app/globals.css");

    assert.match(consentSource, /ResizeObserver/);
    assert.match(consentSource, /--cookie-consent-offset/);
    assert.match(globalStyles, /padding-bottom:\s*var\(--cookie-consent-offset,\s*0px\)/);
  });

  it("does not claim to charge VAT while the operator is not VAT registered", () => {
    const pricingSource = readAppFile("app/pricing/page.tsx");
    const apiSource = readAppFile("app/api/page.tsx");
    const configSource = readAppFile("lib/caregist-config.ts");
    const dashboardSource = readAppFile("app/dashboard/page.tsx");
    const termsSource = readAppFile("app/terms/page.tsx");
    const commercialSources = [pricingSource, apiSource, configSource, dashboardSource];

    for (const source of commercialSources) {
      assert.doesNotMatch(source, /\+\s*VAT|exclude(?:s|d)?\s+VAT/i);
    }
    assert.match(pricingSource, /VAT is not currently charged/);
    assert.match(termsSource, /not currently VAT registered/);
  });

  it("does not issue opportunity lead-list tokens", () => {
    const source = readAppFile("app/api/leads/request/route.ts");
    assert.match(source, /status:\s*410/);
    assert.doesNotMatch(source, /opportunity|createLeadAndToken|redirectWithStatelessToken/);
  });

  it("privacy policy covers Radar report processing and outcome tracking", () => {
    const source = readAppFile("app/privacy/page.tsx");

    assert.match(source, /Account and organisation data/);
    assert.match(source, /CQC source and report data/);
    assert.match(source, /optional outcomes/);
    assert.match(source, /Open Government Licence v3\.0/);
    assert.match(source, /H-Kay Limited/);
    assert.doesNotMatch(source, /Draft v2\.0|Henry Mlalazi trading as CareGist/);
  });

  it("keeps the legal operator consistent and removes retired API tiers", () => {
    const sources = [
      readAppFile("app/privacy/page.tsx"),
      readAppFile("app/terms/page.tsx"),
      readAppFile("app/acceptable-use/page.tsx"),
    ];
    const combined = sources.join("\n");

    for (const source of sources) assert.match(source, /H-Kay Limited/);
    assert.doesNotMatch(combined, /Henry Mlalazi trading as CareGist/);
    assert.doesNotMatch(combined, /Alerts Pro|Data Starter|Data Pro|Data Business|Extra Seat/);
  });

  it("does not claim that browser storage contains an API key", () => {
    const source = readAppFile("app/cookies/page.tsx");

    assert.doesNotMatch(source, /Store your API key/i);
    assert.match(source, /No password, API key, or signing secret is intentionally stored/);
  });
});
