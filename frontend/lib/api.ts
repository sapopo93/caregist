import { getPublicApiBase, getServerApiBase, getServerApiKey } from "@/lib/server-api-config";

async function apiFetch(path: string, params?: Record<string, string | undefined>) {
  // Resolve server config lazily so public-only imports do not fail at module load
  // when the authenticated server fetch path is not actually used.
  const apiBase = getServerApiBase();
  const apiKey = getServerApiKey();
  const url = new URL(path, apiBase);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") url.searchParams.set(k, v);
    });
  }

  // 10-second timeout keeps server-side fetches bounded when the backend is
  // starting cold or the upstream query path is degraded.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);

  try {
    const res = await fetch(url.toString(), {
      headers: { "X-API-Key": apiKey },
      next: { revalidate: 3600 },
      signal: controller.signal,
    });
    if (!res.ok) {
      const error = new Error(`API error: ${res.status}`);
      (error as any).status = res.status;
      throw error;
    }
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      const warmup = new Error("warming_up");
      (warmup as any).status = 503;
      throw warmup;
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function searchProviders(params: {
  q?: string;
  region?: string;
  rating?: string;
  type?: string;
  service_type?: string;
  page?: string;
  sort?: string;
  postcode?: string;
  [key: string]: string | undefined;
}) {
  return apiFetch("/api/v1/providers/search", params);
}

export async function getProvider(slug: string) {
  return apiFetch(`/api/v1/providers/${slug}`);
}

export async function getNearby(lat: number, lon: number, radiusKm = 10) {
  return apiFetch("/api/v1/providers/nearby/search", {
    lat: lat.toString(),
    lon: lon.toString(),
    radius_km: radiusKm.toString(),
  });
}

export async function getRegions() {
  return publicFetch("/api/v1/regions");
}

export async function getServiceTypes() {
  return publicFetch("/api/v1/service-types");
}

export async function getProviderReviews(slug: string, page = "1") {
  return apiFetch(`/api/v1/providers/${slug}/reviews`, { page });
}

export async function getCompareProviders(slugs: string[]) {
  return apiFetch("/api/v1/providers/compare", { slugs: slugs.join(",") });
}

export async function getRatingHistory(slug: string) {
  return apiFetch(`/api/v1/providers/${slug}/rating-history`);
}

export async function getComparisonByToken(token: string) {
  return apiFetch(`/api/v1/comparisons/${token}`);
}

// Region stats and city endpoints are public (no auth needed)
async function publicFetch(path: string, params?: Record<string, string | undefined>) {
  const publicApi = getPublicApiBase();
  const base = publicApi || (typeof window !== "undefined" ? window.location.origin : getServerApiBase());
  const url = new URL(path, base);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") url.searchParams.set(k, v);
    });
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);
  try {
    const res = await fetch(url.toString(), {
      next: { revalidate: 3600 },
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  } finally {
    clearTimeout(timer);
  }
}

export async function getRegionStats(laSlug: string) {
  return publicFetch(`/api/v1/regions/${laSlug}/stats`);
}

export async function getLocalAuthorities() {
  return publicFetch("/api/v1/regions/local-authorities");
}

export async function getCityProviders(citySlug: string, params?: Record<string, string | undefined>) {
  return publicFetch(`/api/v1/cities/${citySlug}/providers`, params);
}

export async function getTopCities() {
  return publicFetch("/api/v1/cities");
}
