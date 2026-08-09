import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizePostVerificationPath, resolvePostVerificationPath } from "./post-verification.ts";

describe("post-verification destination", () => {
  it("preserves only the two saleable Radar continuations", () => {
    assert.equal(normalizePostVerificationPath("/login?upgrade=radar-regional"), "/login?upgrade=radar-regional");
    assert.equal(normalizePostVerificationPath("/login?upgrade=radar-national"), "/login?upgrade=radar-national");
    assert.equal(normalizePostVerificationPath("/login?upgrade=data-pro"), null);
    assert.equal(normalizePostVerificationPath("/login?provider_tier=enhanced"), null);
  });

  it("rejects external, protocol-relative, malformed, and unapproved destinations", () => {
    assert.equal(normalizePostVerificationPath("https://evil.example/login?upgrade=radar-national"), null);
    assert.equal(normalizePostVerificationPath("//evil.example/login?upgrade=radar-national"), null);
    assert.equal(normalizePostVerificationPath("/dashboard"), null);
    assert.equal(normalizePostVerificationPath("/login?upgrade=enterprise"), null);
    assert.equal(normalizePostVerificationPath("/login?upgrade=radar-national&next=/admin"), null);
  });

  it("uses the server-backed continuation without browser-local state", () => {
    assert.equal(
      resolvePostVerificationPath("/login?upgrade=radar-regional", null, null),
      "/login?upgrade=radar-regional",
    );
    assert.equal(
      resolvePostVerificationPath("https://evil.example/steal", null, null),
      "/login",
    );
  });
});
