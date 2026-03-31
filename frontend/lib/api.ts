// Server-side only — no NEXT_PUBLIC_ prefix, key stays on server
const API_BASE = process.env.API_URL || "http://localhost:8000";
const API_KEY = process.env.API_KEY || "dev_key_change_me";

// Warn loudly if env vars are missing (visible in Vercel function logs)
if (!process.env.API_URL) {
  console.warn("[caregist] API_URL env var is not set — falling back to localhost:8000");
}
if (!process.env.API_KEY) {
  console.warn("[caregist] API_KEY env var is not set — using default dev key");
}

async function apiFetch(path: string, params?: Record<string, string | undefined>) {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") url.searchParams.set(k, v);
    });
  }

  // 10-second timeout — keeps us well inside Vercel's 30s function limit
  // even when Render free tier is cold-starting
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);

  try {
    const res = await fetch(url.toString(), {
      headers: { "X-API-Key": API_KEY },
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
  return apiFetch("/api/v1/regions");
}

export async function getServiceTypes() {
  return apiFetch("/api/v1/service-types");
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
const PUBLIC_API = process.env.NEXT_PUBLIC_API_URL || API_BASE;

async function publicFetch(path: string, params?: Record<string, string | undefined>) {
  const url = new URL(`${PUBLIC_API}${path}`);
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
