"use client";

import { useEffect, useState } from "react";

/**
 * Renders open (so it works without JavaScript and on desktop) and folds itself
 * shut on phone-width screens after hydration.
 */
export default function CollapsibleOnMobile({
  summary,
  activeCount,
  children,
}: {
  summary: string;
  activeCount: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (window.matchMedia("(max-width: 1023px)").matches) setOpen(false);
  }, []);

  return (
    <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)} className="group min-w-0">
      <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-stone bg-cream px-5 py-3 text-sm font-semibold text-bark shadow-sm lg:hidden [&::-webkit-details-marker]:hidden">
        <span>
          {summary}
          {activeCount > 0 ? (
            <span className="ml-2 rounded-full bg-clay px-2 py-0.5 text-xs text-white">{activeCount} active</span>
          ) : null}
        </span>
        <span aria-hidden className="text-clay transition group-open:rotate-180">⌄</span>
      </summary>
      <div className="lg:!block">{children}</div>
    </details>
  );
}
