import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizeExternalHttpUrl, cqcEvidenceUrl } from "./external-url.ts";

describe("normalizeExternalHttpUrl", () => {
  it("makes bare provider hostnames absolute", () => {
    assert.equal(
      normalizeExternalHttpUrl("www.121careagency.co.uk"),
      "https://www.121careagency.co.uk/",
    );
  });

  it("preserves valid HTTP and HTTPS URLs", () => {
    assert.equal(normalizeExternalHttpUrl("https://example.org/path"), "https://example.org/path");
    assert.equal(normalizeExternalHttpUrl("http://example.org"), "http://example.org/");
  });

  it("rejects executable, credential-bearing, and malformed values", () => {
    assert.equal(normalizeExternalHttpUrl("javascript:alert(1)"), null);
    assert.equal(normalizeExternalHttpUrl("data:text/html,unsafe"), null);
    assert.equal(normalizeExternalHttpUrl("https://user:pass@example.org"), null);
    assert.equal(normalizeExternalHttpUrl("not a website"), null);
  });
});

describe("cqcEvidenceUrl", () => {
  it("repairs report paths and absent report URLs with the official location page", () => {
    for (const value of ["/reports/c1bff616?20230531120000", "reports/c1bff616", null, "https://reports/c1bff616"]) {
      assert.equal(cqcEvidenceUrl(value, "1-123456"), "https://www.cqc.org.uk/location/1-123456/reports");
    }
  });
  it("preserves official absolute reports and rejects lookalike or unsafe hosts", () => {
    assert.equal(cqcEvidenceUrl("https://api.cqc.org.uk/public/v1/reports/abc", "1-123456"), "https://api.cqc.org.uk/public/v1/reports/abc");
    for (const value of ["https://cqc.org.uk.example.com/report", "javascript:alert(1)", "https://user:pass@www.cqc.org.uk/report"]) {
      assert.equal(cqcEvidenceUrl(value, "1-123456"), "https://www.cqc.org.uk/location/1-123456/reports");
    }
    assert.equal(cqcEvidenceUrl(null, "not-a-location"), null);
  });
});
