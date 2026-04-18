export interface ProviderPathSource {
  id?: string | null;
  slug?: string | null;
}

function getValidSlug(slug?: string | null): string {
  const trimmed = slug?.trim() ?? "";
  const normalized = trimmed.toLowerCase();
  return trimmed && normalized !== "null" && normalized !== "undefined" ? trimmed : "";
}

export function getProviderPathKey(provider: ProviderPathSource): string {
  return getValidSlug(provider.slug) || provider.id?.trim() || "";
}

export function getProviderHref(provider: ProviderPathSource): string {
  const key = getProviderPathKey(provider);
  return key ? `/provider/${encodeURIComponent(key)}` : "/search";
}

export function getClaimHref(provider: ProviderPathSource): string {
  const key = getProviderPathKey(provider);
  return key ? `/claim/${encodeURIComponent(key)}` : "/pricing";
}
