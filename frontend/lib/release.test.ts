import assert from "node:assert/strict";
import test from "node:test";

import { releaseGitSha } from "./release.ts";

test("explicit release SHA takes precedence and is normalized", () => {
  assert.equal(
    releaseGitSha({
      CAREGIST_RELEASE_SHA: "ABCDEF1234567",
      VERCEL_GIT_COMMIT_SHA: "1111111111111",
    }),
    "abcdef1234567",
  );
});

test("Vercel release SHA is used when no explicit SHA is injected", () => {
  assert.equal(releaseGitSha({ VERCEL_GIT_COMMIT_SHA: "a".repeat(40) }), "a".repeat(40));
});

test("invalid public release values fail closed", () => {
  assert.equal(releaseGitSha({ CAREGIST_RELEASE_SHA: "branch/main<script>" }), "unknown");
});
