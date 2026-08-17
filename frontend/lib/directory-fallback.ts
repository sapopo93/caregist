import { DEFAULT_RATING_OPTIONS, DEFAULT_REGION_OPTIONS, DEFAULT_SERVICE_TYPE_OPTIONS } from "./directory-constants.ts";
import type { DirectoryOpportunity } from "./directory-constants.ts";
import {
  MAX_DIRECTORY_EXPORT_ROWS,
  type DirectoryExportRow,
  type DirectoryExportScope,
} from "./directory-export.ts";
import type { DirectorySearchParams } from "./directory-filters.ts";
import { type DirectoryFileProvider, loadDirectoryFileProviders } from "./directory-file-store.ts";

type FallbackProvider = DirectoryFileProvider;

interface FallbackSearchRow extends DirectoryFileProvider {
  searchScore: number;
}

let activeProvidersPromise: Promise<FallbackProvider[]> | null = null;
let filterOptionsPromise: Promise<{
  regions: string[];
  serviceTypes: string[];
  ratings: string[];
}> | null = null;
let statsPromise: Promise<{
  totalProviders: number;
  totalRegions: number;
}> | null = null;
let opportunityStatsPromise: Promise<{
  totalProviders: number;
  newLast90Days: number;
  inadequate: number;
  requiresImprovement: number;
  notYetInspected: number;
  staleInspection: number;
}> | null = null;

async function loadProviders() {
  return loadDirectoryFileProviders();
}

async function loadActiveProviders() {
  if (!activeProvidersPromise) {
    activeProvidersPromise = loadProviders().then((providers) =>
      providers.filter((provider) => provider.status === "ACTIVE"),
    );
  }

  return activeProvidersPromise;
}

function splitPipeValue(value: string | null) {
  return (value ?? "")
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);
}

function matchesServiceType(provider: FallbackProvider, serviceType: string) {
  if (!serviceType) {
    return true;
  }

  return splitPipeValue(provider.service_types).includes(serviceType);
}

function parseDate(value: string | null) {
  if (!value) {
    return null;
  }

  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? new Date(timestamp) : null;
}

function daysSince(value: string | null) {
  const date = parseDate(value);
  if (!date) {
    return null;
  }

  return Math.floor((Date.now() - date.getTime()) / 86_400_000);
}

function normalizedRating(value: string | null) {
  return (value ?? "").trim().toLowerCase();
}

function matchesOpportunity(provider: FallbackProvider, opportunity: DirectoryOpportunity | "") {
  switch (opportunity) {
    case "new_90": {
      const ageDays = daysSince(provider.registration_date);
      return ageDays !== null && ageDays >= 0 && ageDays <= 90;
    }
    case "inadequate":
      return provider.overall_rating === "Inadequate";
    case "requires_improvement":
      return normalizedRating(provider.overall_rating) === "requires improvement";
    case "not_yet_inspected":
      return ["", "not yet inspected", "no published rating"].includes(
        normalizedRating(provider.overall_rating),
      );
    case "stale_inspection": {
      const ageDays = daysSince(provider.last_inspection_date);
      return ageDays === null || ageDays > 365 * 3;
    }
    default:
      return true;
  }
}

function buildSearchScore(provider: FallbackProvider, query: string) {
  if (!query) {
    return 0;
  }

  const needle = query.toLowerCase();
  let score = 0;
  const weightedFields: Array<[string | null, number]> = [
    [provider.name, 5],
    [provider.town, 4],
    [provider.county, 3],
    [provider.postcode, 4],
    [provider.region, 3],
    [provider.service_types, 2],
    [provider.specialisms, 1],
  ];

  for (const [field, weight] of weightedFields) {
    const value = String(field ?? "").toLowerCase();
    if (!value) {
      continue;
    }

    if (value.startsWith(needle)) {
      score += weight + 2;
      continue;
    }

    if (value.includes(needle)) {
      score += weight;
    }
  }

  return score;
}

function sortRows(rows: FallbackSearchRow[], hasQuery: boolean) {
  return rows.sort((left, right) => {
    if (hasQuery && right.searchScore !== left.searchScore) {
      return right.searchScore - left.searchScore;
    }

    return left.name.localeCompare(right.name);
  });
}

export async function getFallbackFilterOptions() {
  if (!filterOptionsPromise) {
    filterOptionsPromise = (async () => {
      const providers = await loadActiveProviders();
      const regions = new Set<string>();
      const serviceTypes = new Set<string>();
      const ratings = new Set<string>();

      for (const provider of providers) {
        if (provider.region) {
          regions.add(provider.region);
        }

        for (const serviceType of splitPipeValue(provider.service_types)) {
          serviceTypes.add(serviceType);
        }

        if (provider.overall_rating) {
          ratings.add(provider.overall_rating);
        }
      }

      return {
        regions: regions.size > 0 ? [...regions].sort((a, b) => a.localeCompare(b)) : DEFAULT_REGION_OPTIONS,
        serviceTypes:
          serviceTypes.size > 0 ? [...serviceTypes].sort((a, b) => a.localeCompare(b)) : DEFAULT_SERVICE_TYPE_OPTIONS,
        ratings:
          ratings.size > 0
            ? DEFAULT_RATING_OPTIONS.filter((rating) => ratings.has(rating)).concat(
                [...ratings]
                  .filter((rating) => !DEFAULT_RATING_OPTIONS.includes(rating))
                  .sort((a, b) => a.localeCompare(b)),
              )
            : DEFAULT_RATING_OPTIONS,
      };
    })();
  }

  return filterOptionsPromise;
}

export async function getFallbackServiceTypeCounts() {
  const providers = await loadActiveProviders();
  const counts = new Map<string, number>();

  for (const provider of providers) {
    for (const serviceType of splitPipeValue(provider.service_types)) {
      counts.set(serviceType, (counts.get(serviceType) ?? 0) + 1);
    }
  }

  return [...counts.entries()]
    .map(([service_type, provider_count]) => ({ service_type, provider_count }))
    .sort((left, right) => left.service_type.localeCompare(right.service_type));
}

export async function getFallbackStats() {
  if (!statsPromise) {
    statsPromise = (async () => {
      const providers = await loadActiveProviders();
      const regions = new Set<string>();

      for (const provider of providers) {
        if (provider.region) {
          regions.add(provider.region);
        }
      }

      return {
        totalProviders: providers.length,
        totalRegions: regions.size,
      };
    })();
  }

  return statsPromise;
}

export async function getFallbackOpportunityStats() {
  if (!opportunityStatsPromise) {
    opportunityStatsPromise = (async () => {
      const providers = await loadActiveProviders();

      return {
        totalProviders: providers.length,
        newLast90Days: providers.filter((provider) => matchesOpportunity(provider, "new_90")).length,
        inadequate: providers.filter((provider) => matchesOpportunity(provider, "inadequate")).length,
        requiresImprovement: providers.filter((provider) => matchesOpportunity(provider, "requires_improvement")).length,
        notYetInspected: providers.filter((provider) => matchesOpportunity(provider, "not_yet_inspected")).length,
        staleInspection: providers.filter((provider) => matchesOpportunity(provider, "stale_inspection")).length,
      };
    })();
  }

  return opportunityStatsPromise;
}

export async function searchFallbackProviders(filters: DirectorySearchParams) {
  const providers = await loadActiveProviders();
  const query = filters.query.trim();
  const hasQuery = query.length > 0;

  const rows = providers
    .filter((provider) => {
      if (filters.region && provider.region !== filters.region) {
        return false;
      }

      if (filters.rating && normalizedRating(provider.overall_rating) !== normalizedRating(filters.rating)) {
        return false;
      }

      return matchesServiceType(provider, filters.serviceType) && matchesOpportunity(provider, filters.opportunity);
    })
    .map((provider) => ({
      ...provider,
      searchScore: buildSearchScore(provider, query),
    }))
    .filter((provider) => {
      if (hasQuery && provider.searchScore === 0) {
        return false;
      }
      return true;
    });

  const sortedRows = sortRows(rows, hasQuery);
  const total = sortedRows.length;
  const providersPage = sortedRows
    .slice(filters.offset, filters.offset + filters.perPage)
    .map(({ searchScore: _searchScore, ...provider }) => provider);

  return {
    providers: providersPage,
    total,
    totalPages: total === 0 ? 0 : Math.ceil(total / filters.perPage),
  };
}

export async function getFallbackProvider(slugOrId: string) {
  const providers = await loadActiveProviders();
  return providers.find((provider) => provider.slug === slugOrId || provider.id === slugOrId) ?? null;
}

export async function listFallbackProvidersForExport(scope: DirectoryExportScope): Promise<DirectoryExportRow[]> {
  const providers = await loadActiveProviders();

  return providers
    .filter((provider) => {
      if (scope.region && provider.region !== scope.region) {
        return false;
      }

      if (scope.rating && normalizedRating(provider.overall_rating) !== normalizedRating(scope.rating)) {
        return false;
      }

      return matchesServiceType(provider, scope.serviceType) && matchesOpportunity(provider, scope.opportunity ?? "");
    })
    .sort((left, right) => left.name.localeCompare(right.name))
    .slice(0, MAX_DIRECTORY_EXPORT_ROWS + 1)
    .map((provider) => ({
      cqc_location_id: provider.id,
      cqc_provider_id: provider.provider_id,
      name: provider.name,
      slug: provider.slug,
      region: provider.region,
      service_types: provider.service_types,
      specialisms: provider.specialisms,
      phone: provider.phone,
      website: provider.website,
      overall_rating: provider.overall_rating,
      registration_date: provider.registration_date,
      inspection_report_url: provider.inspection_report_url,
    }));
}
