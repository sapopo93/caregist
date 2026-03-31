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
      limit: "50",
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
          <p className="text-sm text-dusk mb-4">
            Showing {visibleResults.length} of {total} providers within {radius} miles of {postcode.toUpperCase()}.
          </p>

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
                      {r.town} · {r.distance_miles} miles · {r.type}
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
