import { isDirectoryOpportunity, type DirectoryOpportunity } from "./directory-constants.ts";

export interface DirectorySearchParams {
  query: string;
  region: string;
  serviceType: string;
  rating: string;
  opportunity: DirectoryOpportunity | "";
  page: number;
  perPage: number;
  offset: number;
}

type RawSearchParams = Record<string, string | string[] | undefined>;

function takeFirst(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return String(value[0] ?? "").trim();
  }

  return String(value ?? "").trim();
}

function parsePositiveInt(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function parseDirectorySearchParams(input: RawSearchParams): DirectorySearchParams {
  const page = parsePositiveInt(takeFirst(input.page), 1);
  const perPage = 24;
  const opportunity = takeFirst(input.opportunity);

  return {
    query: takeFirst(input.q),
    region: takeFirst(input.region),
    serviceType: takeFirst(input.service_type),
    rating: takeFirst(input.rating),
    opportunity: isDirectoryOpportunity(opportunity) ? opportunity : "",
    page,
    perPage,
    offset: (page - 1) * perPage,
  };
}
