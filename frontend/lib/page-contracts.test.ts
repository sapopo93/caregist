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

  it("provider pages expose working review, enquiry and provider-claim journeys", () => {
    const source = readAppFile("app/provider/[slug]/page.tsx");

    assert.match(source, /import EnquiryForm from/);
    assert.match(source, /import ReviewsSection from/);
    assert.match(source, /getProviderReviews/);
    assert.match(source, /<ReviewsSection/);
    assert.match(source, /<EnquiryForm\s+slug=\{providerSlug\}\s+providerName=\{provider\.name\}/);
    assert.match(source, /href=\{`\/claim\/\$\{encodeURIComponent\(providerSlug\)\}`\}/);
  });

  it("lead-list page renders the lead request form with query defaults", () => {
    const source = readAppFile("app/lead-list/page.tsx");

    assert.match(source, /LeadRequestForm/);
    assert.match(source, /buildLeadListDefaults/);
    assert.match(source, /buildLeadListExportHref/);
    assert.match(source, /searchParams/);
    assert.match(source, /defaults=\{defaults\}/);
    assert.match(source, /showExportDownload\s*=\s*submitted\s*\|\|\s*Boolean\(exportHref\)/);
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

  it("commercial directory routes fail closed until Human Gate approval", () => {
    const exportSource = readAppFile("app/api/export/route.ts");
    const leadSource = readAppFile("app/api/leads/request/route.ts");

    assert.match(exportSource, /DIRECTORY_EXPORT_DELIVERY_ENABLED/);
    assert.match(exportSource, /status:\s*503/);
    assert.match(leadSource, /DIRECTORY_LEAD_INTAKE_ENABLED/);
    assert.match(leadSource, /hold[\s\S]*human-gate/);
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

  it("opportunity lead requests use signed stateless export tokens", () => {
    const source = readAppFile("app/api/leads/request/route.ts");
    const opportunityBranch = source.indexOf("if (normalized.opportunity)");
    const databaseTokenCall = source.indexOf("await createLeadAndToken");

    assert.ok(opportunityBranch >= 0);
    assert.ok(databaseTokenCall > opportunityBranch);
    assert.match(source, /return\s+redirectWithStatelessToken\([\s\S]*normalized[\s\S]*Opportunity-specific scopes/);
  });

  it("privacy policy covers lead requests and export access tokens", () => {
    const source = readAppFile("app/privacy/page.tsx");

    assert.match(source, /Lead-list requests/);
    assert.match(source, /Export access tokens/);
    assert.match(source, /90 days after expiry/);
  });
});
