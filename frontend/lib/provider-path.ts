export interface ProviderPathSource {
  id?: string | null;
  slug?: string | null;
}

export function getProviderPathKey(provider: ProviderPathSource): string {
  return provider.slug?.trim() || provider.id?.trim() || "";
}

export function getProviderHref(provider: ProviderPathSource): string {
  const key = getProviderPathKey(provider);
  return key ? `/provider/${encodeURIComponent(key)}` : "/search";
}

export function getClaimHref(provider: ProviderPathSource): string {
  const key = getProviderPathKey(provider);
  return key ? `/claim/${encodeURIComponent(key)}` : "/pricing";
}
