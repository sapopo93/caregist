import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizeExternalHttpUrl } from "./external-url.ts";

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
