/**
 * Free Territory Brief preview: three dated example signals for a scope.
 *
 * Two switches must both be on: NEXT_PUBLIC_TERRITORY_PREVIEW_ENABLED here, and
 * TERRITORY_PREVIEW_ENABLED on the API (which returns 404 while off). The
 * preview opens no checkout, delivery or export path; see
 * docs/territory-preview.md for the review needed before enabling it.
 */

export type PreviewSignal = "new_registration" | "rating_changed";

export interface TerritoryPreviewExample {
  location_name: string;
  location_id: string;
  provider_id: string | null;
  town: string | null;
  signal: PreviewSignal;
  event_date: string;
  reason: string;
  source_url: string;
}

export interface TerritoryPreview {
  scope: { kind: "region" | "local_authority"; name: string; service: string | null; service_label: string | null };
  organisations: number;
  locations: number;
  window: { start: string; end: string; days: number };
  signals: { new_registrations: number; rating_changes: number; organisations_with_signals: number };
  examples: TerritoryPreviewExample[];
  brief: { fits: boolean; min_organisations: number; max_organisations: number; note: string };
  source: { as_of: string; basis: string };
  caveats: string[];
}

/** Directory service-type labels the preview API accepts, keyed to its enum. */
const SERVICE_KEYS: Record<string, string> = {
  "Homecare Agencies": "homecare",
  "Residential Homes": "residential",
  "Nursing Homes": "nursing",
  "Supported Living": "supported_living",
};

export function isTerritoryPreviewEnabled(flag: string | undefined): boolean {
  return (flag ?? "").trim().toLowerCase() === "true";
}

/** Returns null for a service the preview does not cover, so no request is made. */
export function previewServiceKey(serviceType: string): string | null | undefined {
  if (!serviceType) return null; // all services
  return SERVICE_KEYS[serviceType] ?? undefined;
}

export function buildPreviewPath(region: string, serviceType: string): string | null {
  const name = region.trim();
  if (name.length < 2) return null;
  const service = previewServiceKey(serviceType);
  if (service === undefined) return null;
  const params = new URLSearchParams({ kind: "region", name });
  if (service) params.set("service", service);
  return `/api/v1/territory-preview?${params.toString()}`;
}

const SIGNAL_LABELS: Record<PreviewSignal, string> = {
  new_registration: "New registration",
  rating_changed: "Rating change",
};

export function signalLabel(signal: PreviewSignal): string {
  return SIGNAL_LABELS[signal] ?? "Signal";
}

const nf = new Intl.NumberFormat("en-GB");

const SERVICE_NOUNS: Record<string, string> = {
  homecare: "homecare",
  residential: "residential care",
  nursing: "nursing care",
  supported_living: "supported living",
};

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** One headline sentence built only from the counts the API returned. */
export function previewHeadline(p: TerritoryPreview): string {
  const noun = p.scope.service ? SERVICE_NOUNS[p.scope.service] : undefined;
  const service = noun ? `${noun} ` : "";
  const orgs = `${nf.format(p.organisations)} ${service}organisation${p.organisations === 1 ? "" : "s"}`;
  const regs = p.signals.new_registrations;
  const ratings = p.signals.rating_changes;
  const parts = [
    regs ? `${nf.format(regs)} new registration${regs === 1 ? "" : "s"}` : "",
    ratings ? `${nf.format(ratings)} rating change${ratings === 1 ? "" : "s"}` : "",
  ].filter(Boolean);
  const movement = parts.length ? parts.join(" and ") : "no recorded registrations or rating changes";
  return `Across ${orgs} in ${p.scope.name}: ${movement} in the ${p.window.days} days to ${formatDate(p.window.end)}.`;
}

/** The preview covers the whole region and service, not the coverage check's provider group. */
export const PREVIEW_SCOPE_NOTE =
  "This preview covers every organisation in the region and service, not only the provider group checked above, and counts organisations rather than locations.";

export function previewWindowLabel(p: TerritoryPreview): string {
  return `${formatDate(p.window.start)} to ${formatDate(p.window.end)}`;
}
