"use client";

import { useState } from "react";

/** Copy link, print, and report-a-data-issue for one provider. The report opens the visitor's own email app; nothing is sent from here. */
export default function ProviderActions({ locationId, name, pageUrl }: { locationId: string; name: string; pageUrl: string }) {
  const [copied, setCopied] = useState(false);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.origin + window.location.pathname);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  const subject = encodeURIComponent(`Data issue: ${name} (${locationId})`);
  const body = encodeURIComponent(
    `Provider: ${name}\nCQC location ID: ${locationId}\nPage: ${pageUrl}\n\nWhat looks wrong, and where did you check it?\n`,
  );

  const base =
    "inline-flex items-center rounded-full border border-stone bg-white px-3 py-1.5 text-xs font-semibold text-bark transition hover:border-clay hover:text-clay";

  return (
    <div className="mt-4 flex flex-wrap gap-2 print:hidden" role="group" aria-label="Provider actions">
      <button type="button" onClick={() => void copyLink()} className={base}>
        {copied ? "Link copied" : "Copy link"}
      </button>
      <button type="button" onClick={() => window.print()} className={base}>
        Print
      </button>
      <a href={`mailto:support@caregist.co.uk?subject=${subject}&body=${body}`} className={base}>
        Report a data issue
      </a>
    </div>
  );
}
