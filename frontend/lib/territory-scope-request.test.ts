import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
    headers: {
      "x-vercel-forwarded-for": "203.0.113.7, 10.0.0.1",
      "idempotency-key": "550e8400-e29b-41d4-a716-446655440000",
    },
  });
  const input = {
    email: "buyer@example.com",
    name: "Buyer",
    company: "Acme",
    region: "London",
    buyerType: "requires_improvement",
    serviceType: "",
  };
  const first = createTerritoryScopeRequestSecurityIdentity(request, input);
  const duplicate = createTerritoryScopeRequestSecurityIdentity(request, input);
  const nextKey = createTerritoryScopeRequestSecurityIdentity(
    new Request(request.url, { headers: {
      "x-vercel-forwarded-for": "203.0.113.7",
      "idempotency-key": "550e8400-e29b-41d4-a716-446655440001",
    } }),
    input,
  );
  const differentSource = createTerritoryScopeRequestSecurityIdentity(
    new Request(request.url, { headers: {
      "x-vercel-forwarded-for": "198.51.100.9",
      "idempotency-key": "550e8400-e29b-41d4-a716-446655440000",
    } }),
    input,
  );

  assert.deepEqual(first, duplicate);
  assert.notEqual(first.submissionKey, nextKey.submissionKey);
  assert.notEqual(first.submissionKey, differentSource.submissionKey);
  assert.equal(first.requesterFingerprint.length, 64);
  assert.equal(first.contactFingerprint.length, 64);
  assert.equal(first.submissionKey.includes("buyer@example.com"), false);
});

test("does not collapse missing proxy headers into one global rate-limit bucket", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "test-secret-with-at-least-32-characters";
  delete process.env.VERCEL;
  const request = new Request("https://example.test/api/territory/requests", {
    headers: { "idempotency-key": "550e8400-e29b-41d4-a716-446655440000" },
  });
  const common = {
    name: "Buyer",
    company: "Acme",
    region: "London",
    buyerType: "requires_improvement",
    serviceType: "",
  };

  const first = createTerritoryScopeRequestSecurityIdentity(request, {
    ...common,
    email: "first@example.com",
  });
  const sameContact = createTerritoryScopeRequestSecurityIdentity(request, {
    ...common,
    email: "first@example.com",
  });
  const otherContact = createTerritoryScopeRequestSecurityIdentity(request, {
    ...common,
    email: "other@example.com",
  });

  assert.equal(first.requesterFingerprint, sameContact.requesterFingerprint);
  assert.notEqual(first.requesterFingerprint, otherContact.requesterFingerprint);
  assert.equal(first.requesterFingerprint.includes("first@example.com"), false);
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

test("rejects a missing or weak idempotency key", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "test-secret-with-at-least-32-characters";
  assert.throws(
    () => createTerritoryScopeRequestSecurityIdentity(
      new Request("https://example.test"),
      { email: "buyer@example.com", name: "", company: "", region: "London", buyerType: "x", serviceType: "" },
    ),
    /Idempotency-Key/,
  );
});

test("the public route records quota attempts before running the coverage aggregate", () => {
  const route = readFileSync(new URL("../app/api/territory/requests/route.ts", import.meta.url), "utf8");
  assert.ok(route.indexOf("recordTerritoryScopeRequestAttempt(securityIdentity)") > 0);
  assert.ok(
    route.indexOf("recordTerritoryScopeRequestAttempt(securityIdentity)") <
      route.indexOf("getTerritoryScopeCoverage({"),
  );
});

test.after(() => {
  if (originalSecret === undefined) delete process.env.DIRECTORY_TOKEN_SECRET;
  else process.env.DIRECTORY_TOKEN_SECRET = originalSecret;
  if (originalVercel === undefined) delete process.env.VERCEL;
  else process.env.VERCEL = originalVercel;
});
