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
