"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import RatingBadge from "@/components/RatingBadge";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import { getProviderHref, getProviderPathKey } from "@/lib/provider-path";

interface Result {
  id: string;
  name: string;
  slug: string | null;
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
const RATINGS = ["All", "Outstanding", "Good", "Requires Improvement"];
const SERVICE_TYPES = [
  { label: "All", value: "" },
  { label: "Care Homes", value: "Residential Homes" },
  { label: "Home Care", value: "Homecare Agencies" },
  { label: "Nursing Homes", value: "Nursing Homes" },
  { label: "Supported Living", value: "Supported Living" },
  { label: "GP Surgeries", value: "Doctors/Gps" },
  { label: "Dental", value: "Dentist" },
  { label: "Hospitals", value: "Hospital" },
  { label: "Hospice", value: "Hospice" },
  { label: "Community Healthcare", value: "Community Services - Healthcare" },
  { label: "Mental Health", value: "Community Services - Mental Health" },
];

export default function RadiusFinder() {
  const searchParams = useSearchParams();
  const [postcode, setPostcode] = useState("");
  const [radius, setRadius] = useState(5);
  const [rating, setRating] = useState("All");
  const [serviceType, setServiceType] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [emailGated, setEmailGated] = useState(true);
  const [sortBy, setSortBy] = useState<"distance" | "rating" | "name">("distance");
  const autoSearched = useRef(false);

  // Pre-populate form from URL params and auto-run search on first mount
  useEffect(() => {
    if (autoSearched.current) return;
    const urlPostcode = searchParams.get("postcode") || searchParams.get("q") || "";
    const urlRadius = parseFloat(searchParams.get("radius_miles") || "");
    const urlRating = searchParams.get("rating") || "";
    const urlServiceType = searchParams.get("service_type") || "";
    if (urlPostcode) setPostcode(urlPostcode);
    if (!isNaN(urlRadius) && RADII.includes(urlRadius)) setRadius(urlRadius);
    if (urlRating && RATINGS.includes(urlRating)) setRating(urlRating);
    if (urlServiceType) setServiceType(urlServiceType);
    if (urlPostcode) {
      autoSearched.current = true;
      const params = new URLSearchParams({ postcode: urlPostcode, radius_miles: String(!isNaN(urlRadius) ? urlRadius : 5), limit: "200" });
      if (urlRating && urlRating !== "All") params.set("rating", urlRating);
      if (urlServiceType) params.set("service_type", urlServiceType);
      setSearching(true);
      fetch(`/api/v1/tools/radius-search?${params}`)
        .then((res) => res.ok ? res.json() : res.json().then((d) => Promise.reject(new Error(d.detail || "Search failed"))))
        .then((data) => { setResults(data.data || []); setTotal(data.meta?.total || 0); setSearched(true); setEmailGated(true); })
        .catch((err) => setError(typeof err?.message === "string" ? err.message : "Search failed. Please try again."))
        .finally(() => setSearching(false));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    if (serviceType) params.set("service_type", serviceType);

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
      const msg = typeof err?.message === "string" ? err.message : "Search failed. Please try again.";
      setError(msg);
    } finally {
      setSearching(false);
    }
  }

  const RATING_ORDER: Record<string, number> = { Outstanding: 1, Good: 2, "Requires Improvement": 3, Inadequate: 4 };
  const sortedResults = [...results].sort((a, b) => {
    if (sortBy === "rating") return (RATING_ORDER[a.overall_rating] || 5) - (RATING_ORDER[b.overall_rating] || 5);
    if (sortBy === "name") return a.name.localeCompare(b.name);
    return (a.distance_miles || 0) - (b.distance_miles || 0);
  });
  const visibleResults = emailGated ? sortedResults.slice(0, 3) : sortedResults;
  const hiddenCount = emailGated ? Math.max(0, sortedResults.length - 3) : 0;

  return (
    <div>
      {/* Search Form */}
      <form onSubmit={handleSearch} className="bg-cream border border-stone rounded-lg p-6 mb-8">
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-bark mb-1">Postcode</label>
            <input
              type="text"
              name="postcode"
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
              name="rating"
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
              name="service_type"
              value={serviceType}
              onChange={(e) => setServiceType(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-stone bg-white text-sm"
            >
              {SERVICE_TYPES.map((t) => (
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
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <p className="text-sm text-dusk">
              Showing {visibleResults.length} of {total} providers within {radius} miles of {postcode.toUpperCase()}.
            </p>
            <div className="flex gap-3 items-center">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-2 py-1 text-xs rounded border border-stone bg-white text-charcoal print:hidden"
              >
                <option value="distance">Nearest first</option>
                <option value="rating">Best rated</option>
                <option value="name">Name (A-Z)</option>
              </select>
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
                key={getProviderPathKey(r) || r.name}
                href={getProviderHref(r)}
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
