import type { Metadata } from "next";
import { getServerApiBase } from "@/lib/server-api-config";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "CQC Data Status | CareGist",
  description: "Current CareGist CQC source watermark, location count, and freshness status.",
  robots: { index: false, follow: true },
};

type SourceStatus = {
  status?: "fresh" | "stale" | "partial" | "unknown";
  source?: string | null;
  sourcePublishedAt?: string | null;
  sourceRetrievedAt?: string | null;
  reconciledAt?: string | null;
  totalSourceLocations?: number | null;
  checkedLocations?: number | null;
  successfullyCheckedLocations?: number | null;
  coveragePercentage?: number | null;
  successCount?: number | null;
  failureCount?: number | null;
  countsReconciled?: boolean;
  checksumSha256?: string | null;
  reason?: string | null;
  message?: string | null;
};

async function loadStatus(): Promise<SourceStatus | null> {
  try {
    const response = await fetch(`${getServerApiBase()}/api/v1/health/freshness`, {
      next: { revalidate: 3600 },
    });
    if (response.status !== 200 && response.status !== 503) return null;
    return await response.json();
  } catch {
    return null;
  }
}

function formatDate(value?: string | null) {
  if (!value) return "Not available";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Intl.DateTimeFormat("en-GB", {
      dateStyle: "long",
      timeZone: "UTC",
    }).format(new Date(Date.UTC(year, month - 1, day)));
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", { dateStyle: "long", timeStyle: "short", timeZone: "UTC" });
}

export default async function DataStatusPage() {
  const status = await loadStatus();
  const current = status?.status === "fresh";

  return (
    <div className="mx-auto max-w-3xl px-6 py-14">
      <div className="mb-8">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-clay">Data operations</p>
        <h1 className="text-4xl font-bold text-bark">CQC data status</h1>
        <p className="mt-3 text-dusk">
          This page reports the source watermark CareGist has actually reconciled. It does not describe live CQC data.
        </p>
      </div>

      <div className="rounded-xl border border-stone bg-white p-6">
        <div className="mb-6 flex items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-bark">Directory snapshot</h2>
          <span className={`rounded-full px-3 py-1 text-sm font-semibold ${current ? "bg-moss/10 text-moss" : "bg-alert/10 text-alert"}`}>
            {status?.status || "unknown"}
          </span>
        </div>

        <dl className="grid gap-5 sm:grid-cols-2">
          <div className="sm:col-span-2"><dt className="text-xs uppercase tracking-wide text-dusk">Exact CQC source</dt><dd className="mt-1 break-all font-medium text-charcoal">{status?.source || "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Published by CQC</dt><dd className="mt-1 font-medium text-charcoal">{formatDate(status?.sourcePublishedAt)}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Retrieved by CareGist</dt><dd className="mt-1 font-medium text-charcoal">{formatDate(status?.sourceRetrievedAt)}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Reconciled by CareGist</dt><dd className="mt-1 font-medium text-charcoal">{formatDate(status?.reconciledAt)}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Coverage</dt><dd className="mt-1 font-mono font-bold text-charcoal">{status?.coveragePercentage != null ? `${status.coveragePercentage}%` : "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Source locations</dt><dd className="mt-1 font-mono font-bold text-charcoal">{status?.totalSourceLocations?.toLocaleString("en-GB") ?? "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Checked locations</dt><dd className="mt-1 font-mono font-bold text-charcoal">{status?.checkedLocations?.toLocaleString("en-GB") ?? "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Successful checks</dt><dd className="mt-1 font-mono font-bold text-charcoal">{status?.successCount?.toLocaleString("en-GB") ?? "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Failed checks</dt><dd className="mt-1 font-mono font-bold text-charcoal">{status?.failureCount?.toLocaleString("en-GB") ?? "Not available"}</dd></div>
          <div><dt className="text-xs uppercase tracking-wide text-dusk">Counts reconcile</dt><dd className="mt-1 font-medium text-charcoal">{status?.countsReconciled ? "Yes" : "No or unconfirmed"}</dd></div>
          <div className="sm:col-span-2"><dt className="text-xs uppercase tracking-wide text-dusk">Source checksum (SHA-256)</dt><dd className="mt-1 break-all font-mono text-sm text-charcoal">{status?.checksumSha256 || "Not available"}</dd></div>
        </dl>

        <p className="mt-6 border-t border-stone pt-4 text-sm text-charcoal">
          {status?.message || "Freshness cannot currently be confirmed."}
        </p>
        {status?.reason && <p className="mt-2 text-xs text-dusk">Reason: {status.reason}</p>}

        <p className="mt-4 text-xs text-dusk">
          Units are CQC registered locations, not unique provider organisations or ownership groups. CQC states its directory files can lag while it changes source systems.
        </p>
      </div>
    </div>
  );
}
