import test from "node:test";
import assert from "node:assert/strict";

import {
  canIssueDirectoryAccessTokens,
  createDirectoryAccessToken,
  readDirectoryAccessToken,
} from "./directory-access-token.ts";

const originalSecret = process.env.DIRECTORY_TOKEN_SECRET;

test("directory access tokens round-trip the requested scope", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "test-secret-with-at-least-32-characters";

  assert.equal(canIssueDirectoryAccessTokens(), true);

  const token = createDirectoryAccessToken({
    region: "London",
    serviceType: "Homecare Agencies",
    rating: "Good",
    opportunity: "new_90",
  });

  assert.deepEqual(readDirectoryAccessToken(token), {
    region: "London",
    serviceType: "Homecare Agencies",
    rating: "Good",
    opportunity: "new_90",
  });
});

test("directory access tokens reject tampered payloads", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "test-secret-with-at-least-32-characters";

  const token = createDirectoryAccessToken({
    region: "London",
    serviceType: "Homecare Agencies",
    rating: "Good",
  });

  const [payload, signature] = token.split(".");
  const tamperedPayload = Buffer.from(
    JSON.stringify({
      v: 1,
      iat: 1,
      exp: Math.floor(Date.now() / 1000) + 60,
      region: "London",
      serviceType: "Homecare Agencies",
      rating: "Inadequate",
    }),
    "utf8",
  ).toString("base64url");

  assert.equal(readDirectoryAccessToken(`${tamperedPayload}.${signature}`), null);
  assert.notEqual(payload, tamperedPayload);
});

test("directory access tokens reject expired payloads", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "test-secret-with-at-least-32-characters";

  const token = createDirectoryAccessToken(
    {
      region: "London",
      serviceType: "Homecare Agencies",
      rating: "Good",
    },
    { ttlSeconds: -1 },
  );

  assert.equal(readDirectoryAccessToken(token), null);
});

test("directory access tokens reject weak secrets", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "too-short";

  assert.equal(canIssueDirectoryAccessTokens(), false);
  assert.throws(
    () => createDirectoryAccessToken({ region: "London", serviceType: "", rating: "" }),
    /at least 32 characters/i,
  );
});

test("directory access tokens reject extra token segments", () => {
  process.env.DIRECTORY_TOKEN_SECRET = "test-secret-with-at-least-32-characters";
  const token = createDirectoryAccessToken({ region: "London", serviceType: "", rating: "" });

  assert.equal(readDirectoryAccessToken(`${token}.unexpected`), null);
});

test.after(() => {
  if (originalSecret === undefined) {
    delete process.env.DIRECTORY_TOKEN_SECRET;
    return;
  }

  process.env.DIRECTORY_TOKEN_SECRET = originalSecret;
});
