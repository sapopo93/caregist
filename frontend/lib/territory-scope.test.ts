import assert from "node:assert/strict";
import { test } from "node:test";

import {
  evaluateTerritoryCoverage,
  normalizeTerritoryScope,
  TERRITORY_BUYER_TYPES,
  TERRITORY_MIN_PARTIAL,
  TERRITORY_MIN_READY,
  type TerritoryScope,
} from "./territory-scope.ts";

const READY_SCOPE: TerritoryScope = {
  region: "London",
  buyerType: "requires_improvement",
  serviceType: "",
};

test("normalizeTerritoryScope accepts a known region and buyer type", () => {
  const scope = normalizeTerritoryScope({
    region: "London",
    buyerType: "inadequate",
    serviceType: " Nursing Homes ",
  });
  assert.deepEqual(scope, {
    region: "London",
    buyerType: "inadequate",
    serviceType: "Nursing Homes",
  });
});

test("normalizeTerritoryScope rejects an unknown region", () => {
  assert.throws(
    () => normalizeTerritoryScope({ region: "Narnia", buyerType: "inadequate" }),
    /region/i,
  );
});

test("normalizeTerritoryScope rejects an unknown buyer type", () => {
  assert.throws(
    () => normalizeTerritoryScope({ region: "London", buyerType: "everyone" }),
    /buyer type/i,
  );
});

test("normalizeTerritoryScope requires both fields", () => {
  assert.throws(() => normalizeTerritoryScope({ region: "London" }), /buyer type/i);
  assert.throws(() => normalizeTerritoryScope({ buyerType: "inadequate" }), /region/i);
});

test("every buyer type maps to a directory opportunity value", () => {
  for (const buyer of TERRITORY_BUYER_TYPES) {
    const scope = normalizeTerritoryScope({ region: "London", buyerType: buyer.value });
    assert.equal(scope.buyerType, buyer.value);
  }
});

test("evaluateTerritoryCoverage returns ready at or above the ready threshold", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    providerCount: TERRITORY_MIN_READY,
    mostRecentObservation: "2025-06-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "ready");
  assert.equal(result.canCheckout, true);
  assert.equal(result.stale, false);
});

test("evaluateTerritoryCoverage returns partial between the thresholds", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    providerCount: TERRITORY_MIN_PARTIAL,
    mostRecentObservation: "2025-06-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "partial");
  assert.equal(result.canCheckout, true);
});

test("evaluateTerritoryCoverage blocks checkout below the partial threshold", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    providerCount: TERRITORY_MIN_PARTIAL - 1,
    mostRecentObservation: "2025-06-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "insufficient");
  assert.equal(result.canCheckout, false);
});

test("evaluateTerritoryCoverage flags a stale territory but still allows checkout", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    providerCount: 40,
    mostRecentObservation: "2020-01-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "ready");
  assert.equal(result.stale, true);
  assert.equal(result.canCheckout, true);
  assert.match(result.detail, /three years/i);
});

test("evaluateTerritoryCoverage tolerates a missing observation date", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    providerCount: 30,
    mostRecentObservation: null,
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.stale, false);
  assert.equal(result.verdict, "ready");
});
