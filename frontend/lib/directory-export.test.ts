import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { providersToCsv, resolveExportScope } from "./directory-export.ts";

describe("resolveExportScope", () => {
  it("falls back to the stored scope when the request omits filters", () => {
    const scope = resolveExportScope(
      { region: "London", serviceType: "Homecare Agencies", rating: "Good", opportunity: "new_90" },
      { region: "", serviceType: "", rating: "" },
    );

    assert.deepEqual(scope, {
      region: "London",
      serviceType: "Homecare Agencies",
      rating: "Good",
      opportunity: "new_90",
    });
  });

  it("rejects requests that do not match the issued token scope", () => {
    assert.throws(
      () =>
        resolveExportScope(
          { region: "London", serviceType: "Homecare Agencies", rating: "Good" },
          { region: "South East", serviceType: "Homecare Agencies", rating: "Good" },
        ),
      /does not match/i,
    );
  });
});

describe("providersToCsv", () => {
  it("serializes rows with a stable header and escaped values", () => {
    const csv = providersToCsv([
      {
        name: 'Oak "House"',
        slug: "oak-house-london",
        region: "London",
        service_types: "Homecare Agencies|Supported Living",
        specialisms: "Dementia|Physical Disabilities",
        phone: "0207 123 4567",
        website: "https://example.com",
        overall_rating: "Good",
        registration_date: "2026-06-01",
        inspection_report_url: "https://www.cqc.org.uk/location/1-100",
      },
    ]);

    assert.match(csv, /^name,slug,region,service_types,specialisms,phone,website,overall_rating,registration_date,inspection_report_url,source_attribution$/m);
    assert.match(csv, /"Oak ""House"""/);
    assert.match(csv, /oak-house-london/);
    assert.match(csv, /2026-06-01/);
  });

  it("neutralizes spreadsheet formulas in exported provider fields", () => {
    const csv = providersToCsv([
      {
        name: "=HYPERLINK(\"https://attacker.invalid\",\"Open\")",
        slug: "safe-provider",
        region: "London",
        service_types: null,
        specialisms: null,
        phone: "+441234567890",
        website: "@malicious-formula",
        overall_rating: "Good",
        registration_date: null,
        inspection_report_url: null,
      },
    ]);

    assert.match(csv, /"'=HYPERLINK\(""https:\/\/attacker\.invalid""/);
    assert.match(csv, /'\+441234567890/);
    assert.match(csv, /'@malicious-formula/);
  });

  it("attributes every exported row to the CQC Open Government Licence source", () => {
    const csv = providersToCsv([
      {
        name: "Oak House",
        slug: "oak-house",
        region: "London",
        service_types: "Homecare Agencies",
        specialisms: null,
        phone: null,
        website: null,
        overall_rating: "Good",
        registration_date: "2026-06-01",
        inspection_report_url: "https://www.cqc.org.uk/location/1-100",
      },
    ]);

    assert.match(csv, /source_attribution/);
    assert.match(csv, /Care Quality Commission data, licensed under the Open Government Licence v3\.0/);
  });
});
