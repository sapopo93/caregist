import { getServerApiBase, getServerApiKey } from "./server-api-config.ts";

type NextFetchInit = RequestInit & {
  next?: {
    revalidate?: number;
  };
};

type FetchLike = (input: string | URL | Request, init?: NextFetchInit) => Promise<Response>;

export type PublicGroup = {
  provider_id: string;
  group_name?: string | null;
  slug: string;
  location_count: number;
  outstanding_count: number;
  good_count: number;
  ri_count: number;
  inadequate_count: number;
  not_inspected_count: number;
  avg_quality_score?: number | null;
  pct_good_or_outstanding?: number | null;
  total_beds?: number | null;
  regions?: string[];
  provider_types?: string[];
  locations?: unknown[];
  benchmark?: {
    national_avg_quality?: number | null;
    national_pct_good?: number | null;
  };
  latest_inspection?: string | null;
};

export type PublicGroupsResult = {
  data: PublicGroup[];
  meta: {
    total: number;
    page: number;
    per_page: number;
    pages: number;
  };
};

function serverApiUrl(path: string): URL {
  const base = getServerApiBase();
  if (base) return new URL(path, base);
  return new URL(path, "http://localhost:8000");
}

function isNamedGroup(group: PublicGroup): boolean {
  return typeof group.group_name === "string" && group.group_name.trim().length > 0;
}

async function fetchJson(url: URL, fetchImpl: FetchLike, errorPrefix: string) {
  const res = await fetchImpl(url.toString(), {
    headers: { "X-API-Key": getServerApiKey() },
    next: { revalidate: 3600 },
  });
  if (!res.ok) {
    throw new Error(`${errorPrefix}: ${res.status}`);
  }
  return res.json();
}

export async function getPublicGroups(
  params: { q?: string; page?: string } = {},
  fetchImpl: FetchLike = fetch,
): Promise<PublicGroupsResult> {
  const url = serverApiUrl("/api/v1/groups");
  url.searchParams.set("per_page", "25");
  url.searchParams.set("page", params.page || "1");
  url.searchParams.set("min_locations", "3");
  if (params.q) url.searchParams.set("q", params.q);

  const result = (await fetchJson(url, fetchImpl, "Public groups API error")) as PublicGroupsResult;
  const rawData = Array.isArray(result.data) ? result.data : [];
  const data = rawData.filter(isNamedGroup);

  return {
    data,
    meta: {
      total: data.length === rawData.length ? result.meta.total : data.length,
      page: result.meta.page,
      per_page: result.meta.per_page,
      pages: data.length === rawData.length ? result.meta.pages : Math.max(1, Math.ceil(data.length / result.meta.per_page)),
    },
  };
}

export async function getPublicGroup(slug: string, fetchImpl: FetchLike = fetch): Promise<PublicGroup | null> {
  const url = serverApiUrl(`/api/v1/groups/${encodeURIComponent(slug)}`);
  const res = await fetchImpl(url.toString(), {
    headers: { "X-API-Key": getServerApiKey() },
    next: { revalidate: 3600 },
  });

  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Public group API error: ${res.status}`);
  }

  const result = (await res.json()) as { data?: PublicGroup };
  if (!result.data || !isNamedGroup(result.data)) return null;
  return result.data;
}
