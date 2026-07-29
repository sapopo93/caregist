import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

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
        assert.equal(getPublicApiBase(), "https://caregist.co.uk");
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
        assert.equal(getServerApiBase(), "https://caregist.co.uk");
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
        assert.equal(getPublicApiBase(), "https://caregist.co.uk");
      },
    );
  });

  it("uses the current Vercel deployment instead of a retired configured API host", () => {
    withEnv(
      {
        CAREGIST_BACKEND_URL: undefined,
        API_URL: "https://api.caregist.co.uk",
        NEXT_PUBLIC_API_URL: "https://api.caregist.co.uk",
        VERCEL_URL: "caregist-candidate.vercel.app",
      },
      () => {
        assert.equal(getServerApiBase(), "https://caregist-candidate.vercel.app");
      },
    );
  });

  it("uses the private Vercel service binding for server-side API calls", () => {
    withEnv(
      {
        CAREGIST_BACKEND_URL: "https://backend.internal.vercel",
        API_URL: "https://api.caregist.co.uk",
        VERCEL_URL: "caregist-candidate.vercel.app",
      },
      () => {
        assert.equal(getServerApiBase(), "https://backend.internal.vercel");
      },
    );
  });

  it("does not include a NEXT_PUBLIC_API_KEY server fallback", () => {
    const source = fs.readFileSync(new URL("./server-api-config.ts", import.meta.url), "utf-8");

    assert.doesNotMatch(source, /NEXT_PUBLIC_API_KEY/);
  });

  it("does not proxy unmatched API routes to the retired backend", () => {
    const source = fs.readFileSync(new URL("../next.config.ts", import.meta.url), "utf-8");

    assert.doesNotMatch(source, /api\.caregist\.co\.uk/);
    assert.doesNotMatch(source, /destination:\s*`\$\{apiDestination\}/);
  });
});
