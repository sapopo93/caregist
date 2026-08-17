import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { loadCommercialCheckoutReadiness } from "./commercial-readiness.ts";

function healthResponse(body: unknown, ok = true) {
  return async () => ({ ok, json: async () => body }) as Response;
}

describe("commercial checkout readiness", () => {
  it("enables checkout only for an explicit true readiness value", async () => {
    const ready = await loadCommercialCheckoutReadiness(
      "https://api.example",
      healthResponse({ commercialReadiness: { checkoutReady: true } }),
    );

    assert.equal(ready, true);
  });

  it("fails closed for false, missing, and non-boolean readiness", async () => {
    for (const body of [
      { commercialReadiness: { checkoutReady: false } },
      { commercialReadiness: {} },
      { commercialReadiness: { checkoutReady: "true" } },
      {},
    ]) {
      assert.equal(
        await loadCommercialCheckoutReadiness("https://api.example", healthResponse(body)),
        false,
      );
    }
  });

  it("fails closed when health is unavailable", async () => {
    assert.equal(
      await loadCommercialCheckoutReadiness(
        "https://api.example",
        healthResponse({ commercialReadiness: { checkoutReady: true } }, false),
      ),
      false,
    );
    assert.equal(
      await loadCommercialCheckoutReadiness("https://api.example", async () => {
        throw new Error("network unavailable");
      }),
      false,
    );
  });
});
