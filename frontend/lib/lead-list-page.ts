import { isDirectoryOpportunity, type DirectoryOpportunity } from "./directory-constants.ts";

type RawSearchParams = Record<string, string | string[] | undefined>;
export interface LeadListDefaults {
  region: string;
  serviceType: string;
  rating: string;
  opportunity: DirectoryOpportunity | "";
}

function takeFirst(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return String(value[0] ?? "").trim();
  }

  return String(value ?? "").trim();
}

export function buildLeadListDefaults(input: RawSearchParams): LeadListDefaults {
  const opportunity = takeFirst(input.opportunity);

  return {
    region: takeFirst(input.region),
    serviceType: takeFirst(input.service_type),
    rating: takeFirst(input.rating),
    opportunity: isDirectoryOpportunity(opportunity) ? opportunity : "",
  };
}

export function buildLeadListExportHref(
  token: string,
  scope: Partial<LeadListDefaults>,
) {
  const params = new URLSearchParams({ token });
  if (scope.region) params.set("region", scope.region);
  if (scope.serviceType) params.set("service_type", scope.serviceType);
  if (scope.rating) params.set("rating", scope.rating);
  if (scope.opportunity) params.set("opportunity", scope.opportunity);
  return `/api/export?${params.toString()}`;
}
