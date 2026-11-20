import Link from "next/link";

import { describeDirectoryFreshness, type SourceStatus } from "@/lib/data-freshness";
import { getServerApiBase } from "@/lib/server-api-config";

async function loadFreshness(): Promise<SourceStatus | null> {
  try {
    const response = await fetch(`${getServerApiBase()}/api/v1/health/freshness`, {
      // The endpoint answers 503 when the data is stale or partial; the body is still the status.
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(5000),
    });
    if (response.status !== 200 && response.status !== 503) return null;
    return (await response.json()) as SourceStatus;
  } catch {
    return null;
  }
}

/**
 * Says which CQC edition the directory holds and when CareGist last checked it.
 * Renders a warning when the data may be out of date or the status cannot be read,
 * and never makes a directory page fail when the API is down.
 */
export default async function DirectoryFreshnessNotice({ className = "" }: { className?: string }) {
  const { tone, text } = describeDirectoryFreshness(await loadFreshness());
  const toneClass =
    tone === "warning"
      ? "border-amber bg-amber/15 text-bark border-l-4"
      : "border-stone bg-cream text-dusk";

  return (
    <div
      role="note"
      data-testid="directory-freshness-notice"
      data-tone={tone}
      className={`rounded-lg border px-4 py-3 text-sm leading-6 ${toneClass} ${className}`.trim()}
    >
      <p>
        {text}{" "}
        <Link href="/data-status" className="font-semibold text-clay underline underline-offset-2 hover:text-bark">
          See data status
        </Link>
      </p>
    </div>
  );
}
