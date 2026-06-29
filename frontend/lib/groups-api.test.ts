import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { getPublicGroup, getPublicGroups } from "./groups-api.ts";

type FetchCall = {
  url: string;
  init?: RequestInit;
};

function withEnv(env: Record<string, string | undefined>, fn: () => Promise<void>) {
  const keys = Object.keys(env);
  const previous = Object.fromEntries(keys.map((key) => [key, process.env[key]]));

  return Promise.resolve()
    .then(() => {
      for (const [key, value] of Object.entries(env)) {
        if (value === undefined) {
          delete process.env[key];
        } else {
          process.env[key] = value;
        }
      }
    })
    .then(fn)
    .finally(() => {
      for (const [key, value] of Object.entries(previous)) {
        if (value === undefined) {
          delete process.env[key];
        } else {
          process.env[key] = value;
        }
      }
    });
}

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("public groups API", () => {
  it("lists groups through the server API without consuming anonymous quota", async () => {
    const calls: FetchCall[] = [];
    const fetchImpl = async (input: string | URL | Request, init?: RequestInit) => {
      calls.push({ url: String(input), init });
      return response({
        data: [
          {
            provider_id: "1-102643122",
            group_name: "Voyage 1 Limited",
            slug: "voyage-1-limited",
            location_count: 279,
            regions: ["London"],
            provider_types: ["Social Care Org"],
          },
        ],
        meta: { total: 1, page: 1, per_page: 25, pages: 1 },
      });
    };

    await withEnv(
      {
        API_KEY: undefined,
        API_MASTER_KEY: "test-server-key",
        API_URL: undefined,
        NEXT_PUBLIC_API_URL: "https://api.caregist.co.uk",
      },
      async () => {
        const result = await getPublicGroups({ page: "1", q: "voyage" }, fetchImpl);

        assert.equal(result.meta.total, 1);
        assert.equal(calls.length, 1);
        assert.equal(calls[0].url, "https://api.caregist.co.uk/api/v1/groups?per_page=25&page=1&min_locations=3&q=voyage");
        assert.deepEqual(calls[0].init?.headers ?? {}, { "X-API-Key": "test-server-key" });
      },
    );
  });

  it("does not silently convert a non-OK groups list response into zero results", async () => {
    const fetchImpl = async () => response({ detail: "Missing API key" }, 401);

    await assert.rejects(
      () =>
        withEnv(
          {
            API_KEY: undefined,
            API_MASTER_KEY: "test-server-key",
            API_URL: undefined,
            NEXT_PUBLIC_API_URL: "https://api.caregist.co.uk",
          },
          async () => {
            await getPublicGroups({}, fetchImpl);
          },
        ),
      /Public groups API error: 401/,
    );
  });

  it("filters unnamed groups from public list responses before rendering", async () => {
    const fetchImpl = async () =>
      response({
        data: [
          {
            provider_id: "named",
            group_name: "Voyage 1 Limited",
            slug: "voyage-1-limited",
            location_count: 279,
            regions: [],
            provider_types: [],
          },
          {
            provider_id: "blank",
            group_name: "   ",
            slug: "blank",
            location_count: 12,
            regions: [],
            provider_types: [],
          },
          {
            provider_id: "missing",
            slug: "missing",
            location_count: 9,
            regions: [],
            provider_types: [],
          },
        ],
        meta: { total: 3, page: 1, per_page: 25, pages: 1 },
      });

    await withEnv(
      {
        API_KEY: undefined,
        API_MASTER_KEY: "test-server-key",
        API_URL: undefined,
        NEXT_PUBLIC_API_URL: "https://api.caregist.co.uk",
      },
      async () => {
        const result = await getPublicGroups({}, fetchImpl);

        assert.deepEqual(
          result.data.map((group) => group.provider_id),
          ["named"],
        );
      },
    );
  });

  it("loads group detail through the server API without consuming anonymous quota", async () => {
    const calls: FetchCall[] = [];
    const fetchImpl = async (input: string | URL | Request, init?: RequestInit) => {
      calls.push({ url: String(input), init });
      return response({
        data: {
          provider_id: "1-102643122",
          group_name: "Voyage 1 Limited",
          slug: "voyage-1-limited",
          location_count: 279,
          locations: [],
          benchmark: {},
        },
      });
    };

    await withEnv(
      {
        API_KEY: undefined,
        API_MASTER_KEY: "test-server-key",
        API_URL: undefined,
        NEXT_PUBLIC_API_URL: "https://api.caregist.co.uk",
      },
      async () => {
        const group = await getPublicGroup("voyage-1-limited", fetchImpl);

        assert.equal(group?.group_name, "Voyage 1 Limited");
        assert.equal(calls.length, 1);
        assert.equal(calls[0].url, "https://api.caregist.co.uk/api/v1/groups/voyage-1-limited");
        assert.deepEqual(calls[0].init?.headers ?? {}, { "X-API-Key": "test-server-key" });
      },
    );
  });
});
