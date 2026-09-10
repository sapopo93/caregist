import {
  DEFAULT_REGION_OPTIONS,
  DIRECTORY_OPPORTUNITY_OPTIONS,
  isDirectoryOpportunity,
  type DirectoryOpportunity,
} from "./directory-constants.ts";

/**
 * Self-serve scope model for the Territory Opportunity Brief.
 *
 * A client picks a region and a buyer type ("which organisations do you sell
 * to"), and the system decides — from the live CQC record — whether that scope
 * can be filled without a human scoping call. This replaces the first two manual
 * delivery steps ("Agree the brief" / "Confirm the source check") with a
 * coverage gate the request runs itself.
 */

export const TERRITORY_BRIEF_PRICE_GBP = 795;

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

/** At or above this many matching providers, the brief can be filled in full. */
export const TERRITORY_MIN_READY = 25;
/** Between this and READY, the brief is deliverable but smaller than advertised. */
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
  /** Whether checkout is allowed for this scope. */
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

  const canCheckout = verdict !== "insufficient";

  let headline: string;
  let detail: string;
  if (verdict === "ready") {
    headline = `${scope.region} is ready for a ${label} brief.`;
    detail = `The published CQC record currently supports ${providerCount} ${label} in ${scope.region}. That is enough for the full ranked shortlist of 25–50 organisations.`;
  } else if (verdict === "partial") {
    headline = `${scope.region} can be covered, with a smaller shortlist.`;
    detail = `The published CQC record currently supports ${providerCount} ${label} in ${scope.region}. The brief will rank every one of them, but the shortlist will be shorter than the usual 25–50.`;
  } else {
    headline = `${scope.region} does not have enough ${label} to build a brief.`;
    detail = `The published CQC record currently supports only ${providerCount} ${label} in ${scope.region}. Pick a wider region or a different buyer type, or contact us about a custom scope.`;
  }

  if (stale && verdict !== "insufficient") {
    detail += " Note: the most recent observation in this scope is more than three years old, so movement signals will be limited.";
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
