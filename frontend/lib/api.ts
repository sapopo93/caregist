// Server-side only — no NEXT_PUBLIC_ prefix, key stays on server
const API_BASE = process.env.API_URL || "http://localhost:8000";
const API_KEY = process.env.API_KEY || "dev_key_change_me";

async function apiFetch(path: string, params?: Record<string, string>) {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString(), {
    headers: { "X-API-Key": API_KEY },
    next: { revalidate: 3600 },
  });
  if (!res.ok) {
    const error = new Error(`API error: ${res.status}`);
    (error as any).status = res.status;
    throw error;
  }
  return res.json();
}

export async function searchProviders(params: {
  q?: string;
  region?: string;
  rating?: string;
  type?: string;
  service_type?: string;
  page?: string;
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
