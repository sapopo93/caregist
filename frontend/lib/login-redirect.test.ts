import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizeLoginRedirect } from "./login-redirect.ts";

describe("post-login destination", () => {
  it("returns users to an approved protected workspace", () => {
    assert.equal(normalizeLoginRedirect("/crm"), "/crm");
    assert.equal(normalizeLoginRedirect("/provider-dashboard/example"), "/provider-dashboard/example");
    assert.equal(normalizeLoginRedirect("/dashboard?view=tasks"), "/dashboard?view=tasks");
  });

  it("rejects open redirects and unrelated paths", () => {
    assert.equal(normalizeLoginRedirect("https://evil.example/crm"), null);
    assert.equal(normalizeLoginRedirect("//evil.example/crm"), null);
    assert.equal(normalizeLoginRedirect("/\\evil.example/crm"), null);
    assert.equal(normalizeLoginRedirect("/pricing"), null);
    assert.equal(normalizeLoginRedirect("/crm-danger"), null);
    assert.equal(normalizeLoginRedirect(null), null);
  });
});
