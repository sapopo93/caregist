/**
 * Pure helpers for describing how recent CareGist's copy of the CQC directory is.
 * Shared by the /data-status page and the notice shown on directory pages.
 * No imports, so these run under the plain Node test runner.
 */

export type FreshnessState = "fresh" | "stale" | "partial" | "unknown";

export type SourceStatus = {
  status?: FreshnessState;
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
  quarantinedLocationCount?: number | null;
  countsReconciled?: boolean;
  checksumSha256?: string | null;
  message?: string | null;
};

export type DirectoryFreshness = {
  tone: "ok" | "warning";
  text: string;
};

/** Long UK date, or "Not available". Used by the /data-status page. */
export function formatDate(value?: string | null) {
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

/**
 * Long UK date with no time, or null when the value is missing or not a date.
 * A bare YYYY-MM-DD is a calendar date; a timestamp is shown as the UK calendar day.
 */
export function formatFreshnessDay(value?: string | null): string | null {
  if (!value) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    if (Number.isNaN(date.getTime())) return null;
    return new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeZone: "UTC" }).format(date);
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeZone: "Europe/London" }).format(date);
}

/**
 * What a directory page says about the age of its CQC data. Never claims the
 * data is current or live; it only states the two dates CareGist holds.
 * `null` means the freshness endpoint could not be reached.
 */
export function describeDirectoryFreshness(status: SourceStatus | null): DirectoryFreshness {
  if (!status) {
    return { tone: "warning", text: "CareGist could not confirm how recent this directory is." };
  }

  const published = formatFreshnessDay(status.sourcePublishedAt);
  const checked = formatFreshnessDay(status.sourceRetrievedAt);

  if (status.status === "fresh") {
    if (published && checked) {
      return {
        tone: "ok",
        text: `CareGist last checked CQC's directory on ${checked}. The edition it holds was published on ${published}.`,
      };
    }
    if (checked) {
      return { tone: "ok", text: `CareGist last checked CQC's directory on ${checked}.` };
    }
    if (published) {
      return { tone: "ok", text: `The CQC edition CareGist holds was published on ${published}.` };
    }
    // A "fresh" status with no dates cannot be shown to a reader as evidence.
    return { tone: "warning", text: "CareGist could not confirm how recent this directory is." };
  }

  // stale, partial, unknown, or any status this version does not recognise
  const lead = "This directory may be out of date.";
  if (published && checked) {
    return { tone: "warning", text: `${lead} It is based on CQC's ${published} edition, last checked by CareGist on ${checked}.` };
  }
  if (published) {
    return { tone: "warning", text: `${lead} It is based on CQC's ${published} edition.` };
  }
  if (checked) {
    return { tone: "warning", text: `${lead} CareGist last checked CQC's directory on ${checked}.` };
  }
  return { tone: "warning", text: lead };
}
