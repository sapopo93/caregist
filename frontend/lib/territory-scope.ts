import {
  DEFAULT_REGION_OPTIONS,
  DIRECTORY_OPPORTUNITY_OPTIONS,
  isDirectoryOpportunity,
  type DirectoryOpportunity,
} from "./directory-constants.ts";

/**
 * Enquiry-only scope model for the Territory Opportunity Brief.
 *
 * A client picks a region and buyer type ("which organisations do you sell
 * to"), and the helper reports the matching-provider count and its coverage
 * band. A count is useful for scoping, but does not prove that the data is ready
 * for a brief, that every provider can be ranked, or that an order can proceed.
 */

export const TERRITORY_BRIEF_PRICE_GBP = 745;
// Founder-confirmed September two-product manifest: manual four-week pilot,
// one-off payment, no automatic renewal or automated fulfilment promise.
export const WEEKLY_DIGEST_PILOT_PRICE_GBP = 150;

/** Regions a client can choose from. Matches the directory's region facet. */
export const TERRITORY_REGION_OPTIONS = DEFAULT_REGION_OPTIONS;

export interface TerritoryBuyerType {
  /** Directory opportunity filter this buyer type resolves to. */
  value: DirectoryOpportunity;
  /** Short name shown in the picker. */
  label: string;
  /** Full description of the population. */
  description: string;
  /** Who this shortlist is built for. */
  persona: string;
}

export const TERRITORY_BUYER_TYPES: TerritoryBuyerType[] =
  DIRECTORY_OPPORTUNITY_OPTIONS.map((option) => ({
    value: option.value,
    label: option.shortLabel,
    description: option.label,
    persona: option.audience,
  }));

export function getTerritoryBuyerType(
  value: string,
): TerritoryBuyerType | null {
  return TERRITORY_BUYER_TYPES.find((entry) => entry.value === value) ?? null;
}

const MAX_FIELD_LENGTH = 160;

export interface TerritoryScopeInput {
  region?: string;
  buyerType?: string;
  serviceType?: string;
}

export interface TerritoryScope {
  region: string;
  buyerType: DirectoryOpportunity;
  /** Optional narrowing to one service type; empty means all. */
  serviceType: string;
}

export function normalizeTerritoryScope(
  input: TerritoryScopeInput,
): TerritoryScope {
  const region = String(input.region ?? "").trim();
  const buyerType = String(input.buyerType ?? "").trim();
  const serviceType = String(input.serviceType ?? "").trim();

  if (!region) {
    throw new Error("Choose a region.");
  }
  if (!TERRITORY_REGION_OPTIONS.includes(region)) {
    throw new Error("That region is not one of the available options.");
  }
  if (!buyerType) {
    throw new Error("Choose a buyer type.");
  }
  if (!isDirectoryOpportunity(buyerType)) {
    throw new Error("That buyer type is not one of the available options.");
  }
  if ([region, buyerType, serviceType].some((v) => v.length > MAX_FIELD_LENGTH)) {
    throw new Error("A selection is too long.");
  }

  return { region, buyerType, serviceType };
}

/* -------------------------------------------------------------------------- */
/* Coverage verdict                                                            */
/* -------------------------------------------------------------------------- */

/** At or above this many matching providers, the count is in the ready band. */
export const TERRITORY_MIN_READY = 25;
/** Between this and READY, the count is in the partial band. */
export const TERRITORY_MIN_PARTIAL = 12;
/** Newest observation older than this many years flags the territory as stale. */
export const TERRITORY_STALE_YEARS = 3;

export type TerritoryCoverageVerdict = "ready" | "partial" | "insufficient";

export interface TerritoryCoverageSignals {
  /** Count of active providers matching region + buyer type (+ service type). */
  providerCount: number;
  /** Most recent inspection or registration date in the matched set (ISO). */
  mostRecentObservation: string | null;
}

export interface TerritoryCoverageResult {
  verdict: TerritoryCoverageVerdict;
  providerCount: number;
  mostRecentObservation: string | null;
  stale: boolean;
  /** Always false: this helper supports enquiries and does not authorise checkout. */
  canCheckout: boolean;
  headline: string;
  detail: string;
}

function yearsBetween(fromIso: string, to: Date): number {
  const from = new Date(`${fromIso}T00:00:00Z`);
  if (Number.isNaN(from.getTime())) {
    return 0;
  }
  return (to.getTime() - from.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
}

export function evaluateTerritoryCoverage(
  scope: TerritoryScope,
  signals: TerritoryCoverageSignals,
  now: Date = new Date(),
): TerritoryCoverageResult {
  const providerCount = Math.max(0, Math.floor(signals.providerCount || 0));
  const buyerType = getTerritoryBuyerType(scope.buyerType);
  const label = buyerType ? buyerType.label.toLowerCase() : "matching organisations";

  let verdict: TerritoryCoverageVerdict = "insufficient";
  if (providerCount >= TERRITORY_MIN_READY) {
    verdict = "ready";
  } else if (providerCount >= TERRITORY_MIN_PARTIAL) {
    verdict = "partial";
  }

  const stale =
    signals.mostRecentObservation != null &&
    yearsBetween(signals.mostRecentObservation, now) > TERRITORY_STALE_YEARS;

  const canCheckout = false;

  const headline = `${providerCount} matching ${label} in ${scope.region}.`;
  let detail = `The published CQC record currently contains ${providerCount} active providers matching the selected scope.`;
  if (verdict === "ready") {
    detail += " Contact us to review the scope and available evidence before agreeing a brief.";
  } else if (verdict === "partial") {
    detail += " A broader region or different buyer type may return more matches. Contact us for a scope review.";
  } else {
    detail += " A broader region or different buyer type may return more matches. Contact us for a scope review.";
  }

  if (stale) {
    detail += " The most recent observation in this scope is more than three years old.";
  }

  return {
    verdict,
    providerCount,
    mostRecentObservation: signals.mostRecentObservation,
    stale,
    canCheckout,
    headline,
    detail,
  };
}
