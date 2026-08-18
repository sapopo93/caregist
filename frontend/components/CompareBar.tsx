"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "caregist_compare";

interface CompareItem {
  slug: string;
  name: string;
}

function getCompareList(): CompareItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function setCompareList(list: CompareItem[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("compare-updated"));
}

export default function CompareBar() {
  const [items, setItems] = useState<CompareItem[]>([]);

  useEffect(() => {
    const sync = () => setItems(getCompareList());
    sync();
    window.addEventListener("compare-updated", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("compare-updated", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  function remove(slug: string) {
    setCompareList(items.filter((p) => p.slug !== slug));
  }

  function clearAll() {
    setCompareList([]);
  }

  if (items.length === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-bark text-cream px-4 py-3 z-[80] shadow-[0_-8px_24px_rgba(0,0,0,0.28)] border-t-2 border-clay">
      <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 overflow-x-auto">
          <span className="text-sm font-medium whitespace-nowrap">Compare ({items.length}/3):</span>
          {items.map((item) => (
            <span key={item.slug} className="inline-flex items-center gap-1 bg-cream/10 px-3 py-1 rounded-full text-sm whitespace-nowrap">
              {item.name.length > 25 ? item.name.slice(0, 25) + "..." : item.name}
              <button onClick={() => remove(item.slug)} className="text-stone hover:text-white ml-1" aria-label={`Remove ${item.name}`}>
                <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"><path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/></svg>
              </button>
            </span>
          ))}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button onClick={clearAll} className="text-xs text-stone hover:text-cream underline">Clear</button>
          {items.length >= 2 ? (
            <a
              href={`/compare?providers=${items.map((p) => p.slug).join(",")}`}
              className="px-4 py-1.5 bg-clay text-white rounded-lg text-sm font-medium hover:bg-amber transition-colors"
            >
              Compare Now
            </a>
          ) : (
            <button
              type="button"
              disabled
              className="px-4 py-1.5 bg-clay text-white rounded-lg text-sm font-medium opacity-40 cursor-not-allowed"
            >
              Compare Now
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
