import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./directory-db.ts", import.meta.url), "utf8");

test("territory coverage counts locations and distinct provider organisations separately", () => {
  assert.match(source, /COUNT\(\*\)::int AS location_count/);
  assert.match(
    source,
    /COUNT\(DISTINCT NULLIF\(BTRIM\(provider_id\), ''\)\)::int AS provider_organisation_count/,
  );
});
