"use client";

import { useEffect, useState } from "react";

const RATING_COLORS: Record<string, string> = {
  Outstanding: "bg-moss text-white",
  Good: "bg-amber text-white",
  "Requires Improvement": "bg-amber/60 text-charcoal",
  Inadequate: "bg-alert text-white",
};

interface RatingEntry {
  overall_rating: string;
  inspection_date: string;
  report_url?: string | null;
}

export default function RatingTimeline({ slug }: { slug: string }) {
  const [history, setHistory] = useState<RatingEntry[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const apiKey = localStorage.getItem("caregist_api_key") || "";
    fetch(`/api/v1/providers/${encodeURIComponent(slug)}/rating-history`, {
      headers: apiKey ? { "X-API-Key": apiKey } : {},
    })
      .then((r) => (r.ok ? r.json() : { data: [] }))
      .then((d) => setHistory(d.data || []))
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, [slug]);

  if (!loaded) return null;
  if (history.length === 0) return null;

  return (
    <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
      <h2 className="text-xl font-bold mb-4">Rating History</h2>
      <div className="space-y-3">
        {history.map((entry, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-24 font-mono text-xs text-dusk shrink-0">
              {new Date(entry.inspection_date).toLocaleDateString("en-GB", {
                month: "short",
                year: "numeric",
              })}
            </div>
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                RATING_COLORS[entry.overall_rating] || "bg-stone text-dusk"
              }`}
            >
              {entry.overall_rating}
            </span>
            {entry.report_url && (
              <a
                href={entry.report_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-clay underline"
              >
                Report
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
