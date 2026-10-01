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

/** Keep provider navigation within the customer's filtered directory search. */
export function directoryReturnHref(value: unknown): string {
  if (typeof value !== "string" || value.length > 2048 || !/^\/search(?:\?|$)/.test(value)) return "/search";
  const url = new URL(value, "https://caregist.co.uk");
  return url.origin === "https://caregist.co.uk" && url.pathname === "/search"
    ? `${url.pathname}${url.search}`
    : "/search";
}
