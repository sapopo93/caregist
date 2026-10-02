import assert from "node:assert/strict";
import { test } from "node:test";
import { directoryReturnHref } from "./provider-path.ts";

test("provider return links retain filters and pagination but reject external destinations", () => {
  assert.equal(directoryReturnHref("/search?q=East+London&service_type=home-care&page=2"), "/search?q=East+London&service_type=home-care&page=2");
  for (const value of [undefined, ["/search"], "https://evil.example/search", "//evil.example/search", "/search/../login", "/searching", "javascript:alert(1)"]) {
    assert.equal(directoryReturnHref(value), "/search");
  }
});
