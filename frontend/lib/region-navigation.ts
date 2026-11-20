import { DEFAULT_REGION_OPTIONS } from "./directory-constants.ts";
import { SERVICE_PAGES } from "./service-page-config.ts";

/** Longest piece of user-typed text shown back on a page. */
export const MAX_DISPLAYED_REGION_LENGTH = 40;

/** Region name to its /region/ slug, e.g. "Yorkshire & Humberside" to "yorkshire-humberside". */
export function regionSlug(region: string): string {
  return region.toLowerCase().replace(/&/g, "").trim().replace(/\s+/g, "-");
}

/** True only for the nine England regions CQC reports on, matched exactly as the search filter does. */
export function isSupportedRegion(value: string): boolean {
  return DEFAULT_REGION_OPTIONS.includes(value);
}

/** Caps text typed by a visitor before it is shown back to them. */
export function truncateForDisplay(value: string, max = MAX_DISPLAYED_REGION_LENGTH): string {
  const characters = Array.from(value);
  if (characters.length <= max) return value;
  return `${characters.slice(0, max).join("").trimEnd()}…`;
}

export function regionLinks(): { name: string; href: string }[] {
  return DEFAULT_REGION_OPTIONS.map((name) => ({ name, href: `/region/${regionSlug(name)}` }));
}

/**
 * Message for a `region` value that is not one of the nine regions, or null when
 * the value is empty or valid. Plain text; React escapes it when rendered.
 */
export function unsupportedRegionMessage(value: string): string | null {
  if (!value || isSupportedRegion(value)) return null;
  return `CareGist covers the nine England regions that CQC reports on. “${truncateForDisplay(value)}” is not one of them.`;
}

/** Search links for the main service types in one region. Values come from the service pages, which use canonical service slugs. */
export function regionServiceLinks(region: string): { label: string; serviceType: string; href: string }[] {
  return Object.values(SERVICE_PAGES).map(({ serviceType, displayName }) => ({
    label: displayName,
    serviceType,
    href: `/search?${new URLSearchParams({ region, service_type: serviceType }).toString()}`,
  }));
}
