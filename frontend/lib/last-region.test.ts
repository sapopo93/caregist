import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { isKnownRegion } from "./last-region.ts";

describe("last region", () => {
  it("accepts only the nine England regions", () => {
    assert.equal(isKnownRegion("London"), true);
    assert.equal(isKnownRegion("Yorkshire & Humberside"), true);
    assert.equal(isKnownRegion("Wales"), false);
    assert.equal(isKnownRegion("<script>"), false);
    assert.equal(isKnownRegion(undefined), false);
    assert.equal(isKnownRegion(""), false);
  });
});
