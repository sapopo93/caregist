import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { serialiseJsonLd } from "./json-ld.ts";

describe("JSON-LD serialisation", () => {
  it("cannot close the script element or open a new one", () => {
    const out = serialiseJsonLd({ name: "</script><script>alert(1)</script>" });
    assert.ok(!out.includes("<"));
    assert.deepEqual(JSON.parse(out), { name: "</script><script>alert(1)</script>" });
  });

  it("escapes JavaScript line separators and still round-trips", () => {
    const value = { note: "a\u2028b\u2029c" };
    const out = serialiseJsonLd(value);
    assert.ok(!out.includes(String.fromCharCode(0x2028)) && !out.includes(String.fromCharCode(0x2029)));
    assert.deepEqual(JSON.parse(out), value);
  });

  it("leaves ordinary data unchanged", () => {
    assert.equal(serialiseJsonLd({ a: 1, b: "x" }), '{"a":1,"b":"x"}');
  });
});
