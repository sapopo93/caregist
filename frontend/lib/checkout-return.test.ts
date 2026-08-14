import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { pollCheckoutReturn } from "./checkout-return.ts";

describe("checkout return polling", () => {
  it("waits for the webhook-backed entitlement instead of trusting payment alone", async () => {
    const responses = [
      { checkout_status: "complete", payment_status: "paid", entitlement_ready: false },
      { checkout_status: "complete", payment_status: "paid", entitlement_ready: true, tier: "radar-regional" },
    ];
    let calls = 0;

    const result = await pollCheckoutReturn(
      async () => responses[Math.min(calls++, responses.length - 1)],
      { attempts: 3, delayMs: 0, sleep: async () => undefined },
    );

    assert.equal(calls, 2);
    assert.equal(result.entitlement_ready, true);
    assert.equal(result.tier, "radar-regional");
  });

  it("stops after a bounded number of attempts when fulfillment is delayed", async () => {
    let calls = 0;
    const result = await pollCheckoutReturn(
      async () => {
        calls += 1;
        return { checkout_status: "complete", payment_status: "paid", entitlement_ready: false };
      },
      { attempts: 3, delayMs: 0, sleep: async () => undefined },
    );

    assert.equal(calls, 3);
    assert.equal(result.entitlement_ready, false);
  });
});
