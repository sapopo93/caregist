import type { Metadata } from "next";
import { getServerApiBase } from "@/lib/server-api-config";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "CQC Data Status | CareGist",
  description: "Current CareGist CQC source watermark, location count, and freshness status.",
  robots: { index: false, follow: true },
};

type SourceStatus = {
  status?: string;
  source_fresh?: boolean;
  feed_fresh?: boolean;
  generated_at?: string | null;
  source?: {
    source?: string | null;
    sourceUri?: string | null;
    sourcePublishedAt?: string | null;
    sourceRetrievedAt?: string | null;
    checksumSha256?: string | null;
    sourceLocationCount?: number | null;
    activeLocationCount?: number | null;
    ageHours?: number | null;
    slaHours?: number | null;
  } | null;
  units?: {
    locationRows?: number | null;
    activeLocationRows?: number | null;
    activeProviderOrganisations?: number | null;
    groupedProviderOrganisations?: number | null;
    namedGroupLabels?: number | null;
    sourceActiveLocationRows?: number | null;
    countsReconciled?: boolean;
  } | null;
};

async function loadStatus(): Promise<SourceStatus | null> {
  try {
    const response = await fetch(`${getServerApiBase()}/api/v1/health/freshness`, {
      cache: "no-store",
    });
    if (response.status !== 200 && response.status !== 503) return null;
    return await response.json();
  } catch {
    return null;
  }
}

function formatDate(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", { dateStyle: "long", timeStyle: "short", timeZone: "UTC" });
}

export default async function DataStatusPage() {
  const status = await loadStatus();
  const source = status?.source;
  const units = status?.units;
  const current = status?.status === "healthy";

  return (
    <div className="mx-auto max-w-3xl px-6 py-14">
      <div className="mb-8">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-clay">Data operations</p>
        <h1 className="text-4xl font-bold text-bark">CQC data status</h1>
        <p className="mt-3 text-dusk">
          This page reports the source watermark CareGist has actually reconciled. It does not describe live CQC data.
        </p>
      </div>

      <div className="mt-6 rounded-xl border border-stone bg-white p-6">
        <h2 className="mb-5 text-xl font-bold text-bark">Unit reconciliation</h2>
        <dl className="grid gap-5 sm:grid-cols-2">
          <div><dt className="text-xs uppercase tracking-wide text-dusk">All database location rows</dt><dd className="mt-1 font-mono font-bold text-charcoal">{units?.locationRows?.toLocaleString("en-GB") || "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Active database locations</dt><dd className="mt-1 font-mono font-bold text-charcoal">{units?.activeLocationRows?.toLocaleString("en-GB") || "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Active provider organisations</dt><dd className="mt-1 font-mono font-bold text-charcoal">{units?.activeProviderOrganisations?.toLocaleString("en-GB") || "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Grouped provider organisations</dt><dd className="mt-1 font-mono font-bold text-charcoal">{units?.groupedProviderOrganisations?.toLocaleString("en-GB") || "Not available"}</dd></div>
        </dl>
        <p className="mt-5 text-xs text-dusk">
          A location is a regulated place or service. A provider organisation may operate multiple locations. A group label is a CareGist grouping aid and is not itself a CQC registration unit.
        </p>
      </div>

      <div className="rounded-xl border border-stone bg-white p-6">
        <div className="mb-6 flex items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-bark">Directory snapshot</h2>
          <span className={`rounded-full px-3 py-1 text-sm font-semibold ${current ? "bg-moss/10 text-moss" : "bg-alert/10 text-alert"}`}>
            {current ? "Current" : "Stale or unavailable"}
          </span>
        </div>

        <dl className="grid gap-5 sm:grid-cols-2">
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Source</dt><dd className="mt-1 font-medium text-charcoal">{source?.source || "Care Quality Commission"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Published by CQC</dt><dd className="mt-1 font-medium text-charcoal">{formatDate(source?.sourcePublishedAt)}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Retrieved by CareGist</dt><dd className="mt-1 font-medium text-charcoal">{formatDate(source?.sourceRetrievedAt)}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Active location units</dt><dd className="mt-1 font-mono font-bold text-charcoal">{source?.activeLocationCount?.toLocaleString("en-GB") || "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Source location units</dt><dd className="mt-1 font-mono font-bold text-charcoal">{source?.sourceLocationCount?.toLocaleString("en-GB") || "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Freshness threshold</dt><dd className="mt-1 font-medium text-charcoal">{source?.slaHours ? `${source.slaHours} hours` : "Not available"}</dd></div>
        </dl>

        <p className="mt-6 border-t border-stone pt-4 text-xs text-dusk">
          Units are CQC registered locations, not unique provider organisations or ownership groups. CQC states its directory files can lag while it changes source systems.
        </p>
      </div>

      <p className="mt-5 text-sm text-dusk">Status generated: {formatDate(status?.generated_at)}</p>
    </div>
  );
}
