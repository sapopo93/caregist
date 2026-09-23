import assert from "node:assert/strict";
import test from "node:test";

import {
  createTerritoryScopeRequestSecurityIdentity,
  normalizeTerritoryScopeRequestContact,
} from "./territory-scope-request.ts";

const originalSecret = process.env.DIRECTORY_TOKEN_SECRET;
const originalVercel = process.env.VERCEL;

test("normalizes a scope-request contact", () => {
  assert.deepEqual(
    normalizeTerritoryScopeRequestContact({
      email: " Buyer@Example.com ",
      name: " Buyer ",
      company: " Acme ",
    }),
    { email: "buyer@example.com", name: "Buyer", company: "Acme" },
  );
});

test("rejects invalid and oversized contact data", () => {
  assert.throws(() => normalizeTerritoryScopeRequestContact({ email: "not-an-email" }), /email/i);
  assert.throws(
    () => normalizeTerritoryScopeRequestContact({ email: "a@example.com", company: "x".repeat(161) }),
    /too long/i,
  );
});

test("creates stable, opaque abuse and duplicate keys", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "test-secret-with-at-least-32-characters";
  process.env.VERCEL = "1";
  const request = new Request("https://example.test/api/territory/requests", {
    headers: { "x-vercel-forwarded-for": "203.0.113.7, 10.0.0.1" },
  });
  const input = {
    email: "buyer@example.com",
    name: "Buyer",
    company: "Acme",
    region: "London",
    buyerType: "requires_improvement",
    serviceType: "",
  };
  const first = createTerritoryScopeRequestSecurityIdentity(request, input, 1_800_000);
  const duplicate = createTerritoryScopeRequestSecurityIdentity(request, input, 1_800_001);
  const nextWindow = createTerritoryScopeRequestSecurityIdentity(request, input, 2_700_000);

  assert.deepEqual(first, duplicate);
  assert.notEqual(first.submissionKey, nextWindow.submissionKey);
  assert.equal(first.requesterFingerprint.length, 64);
  assert.equal(first.submissionKey.includes("buyer@example.com"), false);
});

test("fails closed without a sufficiently strong intake secret", () => {
  delete process.env.DIRECTORY_TOKEN_SECRET;
  assert.throws(
    () => createTerritoryScopeRequestSecurityIdentity(
      new Request("https://example.test"),
      { email: "buyer@example.com", name: "", company: "", region: "London", buyerType: "x", serviceType: "" },
    ),
    /DIRECTORY_TOKEN_SECRET/,
  );
});

test.after(() => {
  if (originalSecret === undefined) delete process.env.DIRECTORY_TOKEN_SECRET;
  else process.env.DIRECTORY_TOKEN_SECRET = originalSecret;
  if (originalVercel === undefined) delete process.env.VERCEL;
  else process.env.VERCEL = originalVercel;
});
