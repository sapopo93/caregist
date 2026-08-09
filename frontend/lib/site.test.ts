import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";

import { getSiteUrl } from "./site.ts";

const ORIGINAL_ENV = { ...process.env };

afterEach(() => {
  process.env = { ...ORIGINAL_ENV };
});

describe("getSiteUrl", () => {
  it("canonicalises the CareGist apex domain to www", () => {
    process.env.NEXT_PUBLIC_APP_URL = "https://caregist.co.uk";
    assert.equal(getSiteUrl(), "https://www.caregist.co.uk");
  });

  it("preserves deployment-scoped preview hosts", () => {
    process.env.NEXT_PUBLIC_APP_URL = "https://caregist-preview.vercel.app/";
    assert.equal(getSiteUrl(), "https://caregist-preview.vercel.app");
  });
});
