"use client";

import { useState } from "react";
import RatingBadge from "@/components/RatingBadge";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";

interface Result {
  name: string;
  slug: string;
  type: string;
  overall_rating: string;
  distance_miles: number;
  town: string;
  postcode: string;
  last_inspection_date: string;
  service_types: string;
}

const TYPE_LABELS: Record<string, string> = {
  "Social Care Org": "Care Home",
  "Primary Medical Services": "GP Surgery",
  "Primary Dental Care": "Dental Practice",
  "Independent Ambulance": "Ambulance Service",
  "Independent Healthcare Org": "Private Healthcare",
  "NHS Healthcare Organisation": "NHS Service",
};

const RADII = [1, 5, 10, 20];
const RATINGS = ["All", "Outstanding", "Good"];
const TYPES = [
  { label: "All", value: "" },
  { label: "Care homes", value: "Social Care Org" },
  { label: "Home care", value: "Social Care Org" },
  { label: "Nursing", value: "Social Care Org" },
  { label: "GP", value: "Primary Medical Services" },
  { label: "Dental", value: "Primary Dental Care" },
];

export default function RadiusFinder() {
  const [postcode, setPostcode] = useState("");
  const [radius, setRadius] = useState(5);
  const [rating, setRating] = useState("All");
  const [type, setType] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [emailGated, setEmailGated] = useState(true);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!postcode.trim()) return;

    setSearching(true);
    setError("");
    setSearched(false);

    const params = new URLSearchParams({
      postcode: postcode.trim(),
      radius_miles: String(radius),
      limit: "200",
    });
    if (rating !== "All") params.set("rating", rating);
    if (type) params.set("type", type);

    try {
      const res = await fetch(`/api/v1/tools/radius-search?${params}`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Search failed");
      }
      const data = await res.json();
      setResults(data.data || []);
      setTotal(data.meta?.total || 0);
      setSearched(true);
      setEmailGated(true);
    } catch (err: any) {
      setError(err.message || "Search failed. Please try again.");
    } finally {
      setSearching(false);
    }
  }

  const visibleResults = emailGated ? results.slice(0, 3) : results;
  const hiddenCount = emailGated ? Math.max(0, results.length - 3) : 0;

  return (
    <div>
      {/* Search Form */}
      <form onSubmit={handleSearch} className="bg-cream border border-stone rounded-lg p-6 mb-8">
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-bark mb-1">Postcode</label>
            <input
              type="text"
              required
              placeholder="e.g. BH1 1AA"
              value={postcode}
              onChange={(e) => setPostcode(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-bark mb-1">Radius</label>
            <div className="flex gap-2">
              {RADII.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRadius(r)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium border transition-colors ${
                    radius === r
                      ? "bg-clay text-white border-clay"
                      : "bg-white text-dusk border-stone hover:border-clay"
                  }`}
                >
                  {r} mi
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-bark mb-1">Rating</label>
            <select
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            >
              {RATINGS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-bark mb-1">Service type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            >
              {TYPES.map((t) => (
                <option key={t.label} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={searching}
          className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
        >
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      {error && (
        <div className="bg-alert/10 border border-alert/30 rounded-lg p-4 mb-6 text-center text-alert text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {searched && results.length === 0 && (
        <p className="text-center text-dusk py-8">No providers found within {radius} miles of {postcode}.</p>
      )}

      {visibleResults.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-dusk">
              Showing {visibleResults.length} of {total} providers within {radius} miles of {postcode.toUpperCase()}.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  const header = "Name,Town,Postcode,Distance (miles),Type,Rating,Last Inspected\n";
                  const exportRows = results;
                  const rows = exportRows.map((r) =>
                    `"${r.name}","${r.town}","${r.postcode}","${Number(r.distance_miles).toFixed(2)}","${TYPE_LABELS[r.type] || r.type}","${r.overall_rating || ""}","${r.last_inspection_date || ""}"`
                  ).join("\n");
                  const footer = total > exportRows.length ? `\n"Showing ${exportRows.length} of ${total} total results. Visit caregist.co.uk for the full dataset."` : "";
                  const blob = new Blob([header + rows + footer], { type: "text/csv" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `caregist_${postcode.replace(/\s/g, "")}_${radius}mi.csv`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="px-4 py-2 text-sm font-medium bg-clay text-white rounded-lg hover:bg-bark transition-colors print:hidden"
              >
                Export CSV
              </button>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 text-sm font-medium border border-clay text-clay rounded-lg hover:bg-clay hover:text-white transition-colors print:hidden"
              >
                Print
              </button>
            </div>
          </div>

          <div className="grid gap-4 mb-6">
            {visibleResults.map((r) => (
              <a
                key={r.slug}
                href={`/provider/${r.slug}`}
                className="bg-cream border border-stone rounded-lg p-4 hover:border-clay transition-colors block"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-bark">{r.name}</h3>
                    <p className="text-xs text-dusk mt-0.5">
                      {r.town} · {Number(r.distance_miles).toFixed(2)} miles · {TYPE_LABELS[r.type] || r.type}
                    </p>
                    {r.last_inspection_date && (
                      <p className="text-xs text-dusk mt-0.5">
                        Last inspected: {new Date(r.last_inspection_date).toLocaleDateString("en-GB")}
                      </p>
                    )}
                  </div>
                  <RatingBadge rating={r.overall_rating} />
                </div>
              </a>
            ))}
          </div>

          {/* Email gate */}
          {emailGated && hiddenCount > 0 && (
            <div className="bg-bark rounded-lg p-6 text-center mb-6">
              <p className="text-cream font-semibold mb-2">
                {hiddenCount} more providers found
              </p>
              <p className="text-stone text-sm mb-4">
                Enter your email to see all {total} providers within {radius} miles.
              </p>
              <div className="max-w-md mx-auto">
                <EmailCaptureStrip
                  source="radius_finder"
                  heading=""
                  subheading=""
                  onSuccess={() => setEmailGated(false)}
                />
              </div>
              <button
                onClick={() => setEmailGated(false)}
                className="mt-3 text-xs text-stone underline hover:text-cream"
              >
                Skip and show results
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
