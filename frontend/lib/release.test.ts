import assert from "node:assert/strict";
import test from "node:test";

import { releaseGitSha } from "./release.ts";

test("Vercel build SHA takes precedence over a stale explicit SHA", () => {
  assert.equal(
    releaseGitSha({
      CAREGIST_RELEASE_SHA: "ABCDEF1234567",
      VERCEL_GIT_COMMIT_SHA: "1111111111111",
    }),
    "1111111111111",
  );
});

test("Vercel release SHA is used when no explicit SHA is injected", () => {
  assert.equal(releaseGitSha({ VERCEL_GIT_COMMIT_SHA: "a".repeat(40) }), "a".repeat(40));
});

test("invalid public release values fail closed", () => {
  assert.equal(releaseGitSha({ CAREGIST_RELEASE_SHA: "branch/main<script>" }), "unknown");
});

test("explicit release SHA remains available outside Vercel", () => {
  assert.equal(releaseGitSha({ CAREGIST_RELEASE_SHA: "ABCDEF1234567" }), "abcdef1234567");
});

test("invalid Vercel SHA cannot fall back to a stale explicit SHA", () => {
  assert.equal(releaseGitSha({ VERCEL_GIT_COMMIT_SHA: "invalid", CAREGIST_RELEASE_SHA: "a".repeat(40) }), "unknown");
});
