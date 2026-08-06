import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizePostVerificationPath, resolvePostVerificationPath } from "./post-verification.ts";

describe("post-verification destination", () => {
  it("preserves the paid plan and provider continuations generated at signup", () => {
    assert.equal(normalizePostVerificationPath("/login?upgrade=alerts-pro"), "/login?upgrade=alerts-pro");
    assert.equal(normalizePostVerificationPath("/login?upgrade=data-pro"), "/login?upgrade=data-pro");
    assert.equal(
      normalizePostVerificationPath("/login?provider_tier=enhanced"),
      "/login?provider_tier=enhanced",
    );
  });

  it("rejects external, protocol-relative, malformed, and unapproved destinations", () => {
    assert.equal(normalizePostVerificationPath("https://evil.example/login?upgrade=data-pro"), null);
    assert.equal(normalizePostVerificationPath("//evil.example/login?upgrade=data-pro"), null);
    assert.equal(normalizePostVerificationPath("/dashboard"), null);
    assert.equal(normalizePostVerificationPath("/login?upgrade=enterprise"), null);
    assert.equal(normalizePostVerificationPath("/login?upgrade=data-pro&next=/admin"), null);
  });

  it("uses the server-backed continuation without browser-local state", () => {
    assert.equal(
      resolvePostVerificationPath("/login?upgrade=data-business", null, null),
      "/login?upgrade=data-business",
    );
    assert.equal(
      resolvePostVerificationPath("https://evil.example/steal", null, null),
      "/login",
    );
  });
});
