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

export interface RatingChanges {
  status: "available" | "partial" | "unavailable";
  /** null when the source cannot date rating changes; never shown as zero. */
  count: number | null;
  undated: number;
  note?: string;
}

export interface TerritoryPreview {
  scope: { kind: "region" | "local_authority"; name: string; service: string | null; service_label: string | null };
  organisations: number;
  locations: number;
  window: { start: string; end: string; days: number };
  signals: { new_registrations: number; rating_changes: RatingChanges; organisations_with_signals: number };
  examples: TerritoryPreviewExample[];
  brief: { fits: boolean | null; provisional: boolean; min_organisations: number | null; max_organisations: number; note: string };
  source: {
    /** Plain-English qualification; null when source coverage is confirmed. */
    notice: string | null;
    window_anchor: string;
    window_anchor_basis: string;
    freshness_status: string;
    coverage_confirmed: boolean;
    source_published_at: string | null;
    reconciled_at: string | null;
    freshness_message: string | null;
    basis: string;
    licence: string;
    licence_url: string;
  };
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

/** CQC service-type wording, phrased to follow "providers of". */
const SERVICE_NOUNS: Record<string, string> = {
  homecare: "domiciliary care",
  residential: "care homes without nursing",
  nursing: "care homes with nursing",
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

/** One headline sentence built only from counts the API could measure. */
export function previewHeadline(p: TerritoryPreview): string {
  const noun = p.scope.service ? SERVICE_NOUNS[p.scope.service] : undefined;
  const providers = `${nf.format(p.organisations)} provider${p.organisations === 1 ? "" : "s"}${noun ? ` of ${noun}` : ""}`;
  const regs = p.signals.new_registrations;
  const ratings = p.signals.rating_changes;
  const regText = regs
    ? `${nf.format(regs)} newly registered location${regs === 1 ? "" : "s"}`
    : "no newly registered locations";
  const ratingCount = ratings.status === "unavailable" || ratings.count === null ? null : ratings.count;
  const ratingText =
    ratingCount === null ? "" : ` and ${ratings.status === "partial" ? "at least " : ""}${nf.format(ratingCount)} rating change${ratingCount === 1 ? "" : "s"}`;
  const movement = !regs && ratingCount === 0 ? "no newly registered locations or rating changes" : `${regText}${ratingText}`;
  return `Across ${providers} in ${p.scope.name}: ${movement} in the ${p.window.days} days to ${formatDate(p.window.end)}.`;
}

/** Shown whenever rating changes cannot be fully counted, so a missing count never reads as none. */
export function ratingNotice(p: TerritoryPreview): string | null {
  return p.signals.rating_changes.status === "available" ? null : (p.signals.rating_changes.note ?? null);
}

/** Shown whenever CQC source coverage is not confirmed. The API writes the wording. */
export function freshnessNotice(p: TerritoryPreview): string | null {
  if (p.source.coverage_confirmed) return null;
  return p.source.notice ?? "We can't currently confirm how up to date our copy of the CQC register is, so these figures are provisional and may be incomplete.";
}

/** The preview covers the whole region and service, not the coverage check's provider group. */
export const PREVIEW_SCOPE_NOTE =
  "This preview covers every provider in the region and service, not only the provider group checked above. It counts providers rather than locations, and leaves out locations whose CQC record is unconfirmed.";

export function previewWindowLabel(p: TerritoryPreview): string {
  return `${formatDate(p.window.start)} to ${formatDate(p.window.end)} (the most recent registration we hold)`;
}
