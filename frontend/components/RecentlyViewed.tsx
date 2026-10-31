"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ratingToneClass } from "@/lib/rating-tone";
import { RECENT_EVENT, clearRecent, readRecent, type RecentProvider } from "@/lib/recent-providers";

export default function RecentlyViewed() {
  const [items, setItems] = useState<RecentProvider[]>([]);

  useEffect(() => {
    const sync = () => setItems(readRecent());
    sync();
    window.addEventListener(RECENT_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(RECENT_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  if (items.length === 0) return null;

  return (
    <section aria-label="Recently viewed providers" className="mb-6">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-clay">Pick up where you left off</h2>
        <button type="button" onClick={clearRecent} className="text-xs text-dusk underline underline-offset-2 hover:text-bark">
          Clear
        </button>
      </div>
      <ul className="flex gap-2 overflow-x-auto pb-1">
        {items.map((item) => (
          <li key={item.href} className="shrink-0">
            <Link
              href={item.href}
              className="flex max-w-[16rem] items-center gap-2 rounded-lg border border-stone bg-cream px-3 py-2 text-left transition hover:border-clay"
            >
              <span aria-hidden className={`h-8 w-1.5 shrink-0 rounded-full ${ratingToneClass(item.rating)}`} />
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-bark">{item.name}</span>
                <span className="block truncate text-xs text-dusk">{item.place || item.rating || "Provider"}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-1 text-[0.7rem] text-dusk">Stored only in this browser.</p>
    </section>
  );
}
