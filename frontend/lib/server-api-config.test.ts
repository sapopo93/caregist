import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { getPublicApiBase, getServerApiBase } from "./server-api-config.ts";

function withEnv(env: Record<string, string | undefined>, fn: () => void) {
  const keys = Object.keys(env);
  const previous = Object.fromEntries(keys.map((key) => [key, process.env[key]]));

  try {
    for (const [key, value] of Object.entries(env)) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
    fn();
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
}

describe("server API config", () => {
  it("derives the public API base from production APP_URL", () => {
    withEnv(
      {
        API_URL: undefined,
        NEXT_PUBLIC_API_URL: undefined,
        APP_URL: "https://caregist.co.uk",
        NEXT_PUBLIC_APP_URL: undefined,
        VERCEL_PROJECT_PRODUCTION_URL: undefined,
        VERCEL_URL: undefined,
      },
      () => {
        assert.equal(getPublicApiBase(), "https://api.caregist.co.uk");
      },
    );
  });

  it("derives the server API base from Vercel production URL without a protocol", () => {
    withEnv(
      {
        API_URL: undefined,
        NEXT_PUBLIC_API_URL: undefined,
        APP_URL: undefined,
        NEXT_PUBLIC_APP_URL: undefined,
        VERCEL_PROJECT_PRODUCTION_URL: "caregist.co.uk",
        VERCEL_URL: undefined,
      },
      () => {
        assert.equal(getServerApiBase(), "https://api.caregist.co.uk");
      },
    );
  });

  it("ignores localhost public API URL when APP_URL is production", () => {
    withEnv(
      {
        API_URL: undefined,
        NEXT_PUBLIC_API_URL: "http://127.0.0.1:8001",
        APP_URL: "https://caregist.co.uk",
        NEXT_PUBLIC_APP_URL: undefined,
        VERCEL_PROJECT_PRODUCTION_URL: undefined,
        VERCEL_URL: undefined,
      },
      () => {
        assert.equal(getPublicApiBase(), "https://api.caregist.co.uk");
      },
    );
  });
});
