import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { getClaimHref, getProviderHref, getProviderPathKey } from "./provider-path.ts";

describe("provider path helpers", () => {
  it("prefers canonical slug when present", () => {
    const provider = { id: "1-100", slug: "sunrise-care-home" };

    assert.equal(getProviderPathKey(provider), "sunrise-care-home");
    assert.equal(getProviderHref(provider), "/provider/sunrise-care-home");
    assert.equal(getClaimHref(provider), "/claim/sunrise-care-home");
  });

  it("falls back to CQC location id when slug is missing", () => {
    const provider = { id: "1-100", slug: null };

    assert.equal(getProviderPathKey(provider), "1-100");
    assert.equal(getProviderHref(provider), "/provider/1-100");
    assert.equal(getClaimHref(provider), "/claim/1-100");
  });

  it("does not generate undefined or null provider routes", () => {
    assert.equal(getProviderHref({}), "/search");
    assert.equal(getProviderHref({ slug: "  ", id: "  " }), "/search");
  });

  it("falls back to id when slug is null", () => {
    assert.equal(getProviderPathKey({ id: "1-100", slug: null }), "1-100");
    assert.equal(getProviderHref({ id: "1-100", slug: null }), "/provider/1-100");
  });

  it("falls back to id when slug is empty", () => {
    assert.equal(getProviderPathKey({ id: "1-100", slug: "" }), "1-100");
    assert.equal(getProviderHref({ id: "1-100", slug: "" }), "/provider/1-100");
  });

  it("falls back to id when slug is whitespace", () => {
    assert.equal(getProviderPathKey({ id: "1-100", slug: "  " }), "1-100");
    assert.equal(getProviderHref({ id: "1-100", slug: "  " }), "/provider/1-100");
  });

  it("falls back to id when slug is the string null", () => {
    assert.equal(getProviderPathKey({ id: "1-100", slug: "null" }), "1-100");
    assert.equal(getProviderHref({ id: "1-100", slug: "null" }), "/provider/1-100");
  });

  it("falls back to id when slug is the string undefined", () => {
    assert.equal(getProviderPathKey({ id: "1-100", slug: "undefined" }), "1-100");
    assert.equal(getProviderHref({ id: "1-100", slug: "undefined" }), "/provider/1-100");
  });

  it("uses real slug values", () => {
    assert.equal(getProviderPathKey({ id: "1-100", slug: "real-slug" }), "real-slug");
    assert.equal(getProviderHref({ id: "1-100", slug: "real-slug" }), "/provider/real-slug");
  });
});
