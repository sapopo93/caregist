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

test("normalizeTerritoryScope rejects an unknown service type", () => {
  assert.throws(
    () => normalizeTerritoryScope({
      region: "London",
      buyerType: "requires_improvement",
      serviceType: "Invented service",
    }),
    /service type is not one of the available options/i,
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
    locationCount: 40,
    providerOrganisationCount: TERRITORY_MIN_READY,
    mostRecentObservation: "2025-06-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "ready");
  assert.equal(result.coverageSufficient, true);
  assert.equal(result.checkoutEligible, false);
  assert.equal(result.stale, false);
});

test("evaluateTerritoryCoverage returns partial between the thresholds", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    locationCount: 22,
    providerOrganisationCount: TERRITORY_MIN_PARTIAL,
    mostRecentObservation: "2025-06-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "partial");
  assert.equal(result.coverageSufficient, true);
  assert.equal(result.checkoutEligible, false);
});

test("evaluateTerritoryCoverage marks coverage insufficient below the threshold", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    locationCount: 30,
    providerOrganisationCount: TERRITORY_MIN_PARTIAL - 1,
    mostRecentObservation: "2025-06-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "insufficient");
  assert.equal(result.coverageSufficient, false);
  assert.equal(result.checkoutEligible, false);
});

test("evaluateTerritoryCoverage flags a stale territory without opening checkout", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    locationCount: 55,
    providerOrganisationCount: 40,
    mostRecentObservation: "2020-01-01",
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.verdict, "ready");
  assert.equal(result.stale, true);
  assert.equal(result.coverageSufficient, true);
  assert.equal(result.checkoutEligible, false);
  assert.match(result.detail, /three years/i);
});

test("evaluateTerritoryCoverage tolerates a missing observation date", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    locationCount: 45,
    providerOrganisationCount: 30,
    mostRecentObservation: null,
  }, new Date("2025-09-01T00:00:00Z"));
  assert.equal(result.stale, false);
  assert.equal(result.verdict, "ready");
});

test("distinct organisations, not locations, decide coverage sufficiency", () => {
  const result = evaluateTerritoryCoverage(READY_SCOPE, {
    locationCount: 80,
    providerOrganisationCount: TERRITORY_MIN_PARTIAL - 1,
    mostRecentObservation: "2025-06-01",
  });

  assert.equal(result.locationCount, 80);
  assert.equal(result.providerOrganisationCount, TERRITORY_MIN_PARTIAL - 1);
  assert.equal(result.coverageSufficient, false);
  assert.equal(result.checkoutEligible, false);
});
