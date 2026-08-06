import assert from "node:assert/strict";
import { test } from "node:test";

import { buildCareGistRobots, buildCareGistSitemap } from "./caregist-sitemap.ts";

const BASE_URL = "https://caregist.co.uk";

test("static sitemap preserves the public non-provider routes without fabricated freshness", () => {
  const entries = buildCareGistSitemap(BASE_URL);

  assert.deepEqual(
    entries.map((entry) => entry.url),
    [
      BASE_URL,
      `${BASE_URL}/search`,
      `${BASE_URL}/lead-list`,
      `${BASE_URL}/privacy`,
      `${BASE_URL}/terms`,
    ],
  );
  assert.ok(entries.every((entry) => entry.lastModified === undefined));
  assert.ok(entries.every((entry) => !entry.url.includes("/provider/")));
});

test("robots advertises the static sitemap and the single segmented provider sitemap source", () => {
  const robots = buildCareGistRobots(BASE_URL);

  assert.deepEqual(robots.sitemap, [
    `${BASE_URL}/sitemap.xml`,
    `${BASE_URL}/provider-sitemap-index.xml`,
  ]);
  assert.equal(new Set(robots.sitemap).size, 2);
});
