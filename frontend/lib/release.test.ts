import assert from "node:assert/strict";
import test from "node:test";

import { releaseGitSha } from "./release.ts";

test("deployment release SHA takes precedence over a stale explicit value", () => {
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

test("invalid public release values fail closed when no valid fallback exists", () => {
  assert.equal(releaseGitSha({ CAREGIST_RELEASE_SHA: "branch/main<script>" }), "unknown");
});

test("a valid fallback is used when a higher-priority value is invalid", () => {
  assert.equal(
    releaseGitSha({
      VERCEL_GIT_COMMIT_SHA: "not-a-sha",
      CAREGIST_RELEASE_SHA: "ABCDEF1234567",
    }),
    "abcdef1234567",
  );
});
