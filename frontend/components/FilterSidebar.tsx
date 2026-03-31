"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

const REGIONS = [
  "South East", "London", "North West", "East", "West Midlands",
  "South West", "Yorkshire & Humberside", "East Midlands", "North East",
];

const RATINGS = [
  "Outstanding", "Good", "Requires Improvement", "Inadequate", "Not Yet Inspected",
];

const FALLBACK_SERVICE_TYPES = [
  "Homecare Agencies", "Residential Homes", "Nursing Homes",
  "Doctors/Gps", "Dentist", "Supported Living",
];

const SORT_OPTIONS = [
  { value: "relevance", label: "Relevance" },
  { value: "name", label: "Name (A-Z)" },
  { value: "name_desc", label: "Name (Z-A)" },
  { value: "rating", label: "Best Rating" },
  { value: "beds", label: "Most Beds" },
  { value: "quality", label: "Data Quality" },
  { value: "newest", label: "Newest" },
];

export default function FilterSidebar() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [serviceTypes, setServiceTypes] = useState<string[]>(FALLBACK_SERVICE_TYPES);

  useEffect(() => {
    fetch("/api/v1/service-types", {
      headers: { "X-API-Key": localStorage.getItem("caregist_api_key") || "" },
    })
      .then((r) => (r.ok ? r.json() : { data: [] }))
      .then((d) => {
        const types = (d.data || []).map((t: any) => t.service_type).filter(Boolean);
        if (types.length > 0) setServiceTypes(types);
      })
      .catch(() => {});
  }, []);

  const currentRegion = searchParams.get("region") || "";
  const currentRating = searchParams.get("rating") || "";
  const currentServiceType = searchParams.get("service_type") || "";
  const currentSort = searchParams.get("sort") || "relevance";

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete("page"); // Reset to page 1
    router.push(`/search?${params.toString()}`);
  };

  const clearAll = () => {
    const q = searchParams.get("q") || "";
    router.push(q ? `/search?q=${encodeURIComponent(q)}` : "/search");
  };

  const hasFilters = currentRegion || currentRating || currentServiceType;

  return (
    <aside className="space-y-5">
      {/* Sort */}
      <div>
        <label htmlFor="sort" className="block text-sm font-semibold text-bark mb-1">Sort by</label>
        <select
          id="sort"
          value={currentSort}
          onChange={(e) => updateFilter("sort", e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Region */}
      <div>
        <label htmlFor="region" className="block text-sm font-semibold text-bark mb-1">Region</label>
        <select
          id="region"
          value={currentRegion}
          onChange={(e) => updateFilter("region", e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm"
        >
          <option value="">All regions</option>
          {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {/* Rating */}
      <div>
        <label htmlFor="rating" className="block text-sm font-semibold text-bark mb-1">CQC Rating</label>
        <select
          id="rating"
          value={currentRating}
          onChange={(e) => updateFilter("rating", e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm"
        >
          <option value="">All ratings</option>
          {RATINGS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {/* Service Type */}
      <div>
        <label htmlFor="service_type" className="block text-sm font-semibold text-bark mb-1">Service Type</label>
        <select
          id="service_type"
          value={currentServiceType}
          onChange={(e) => updateFilter("service_type", e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm"
        >
          <option value="">All types</option>
          {serviceTypes.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Clear filters */}
      {hasFilters && (
        <button
          onClick={clearAll}
          className="w-full px-3 py-2 text-sm text-clay border border-clay rounded-lg hover:bg-clay hover:text-white transition-colors"
        >
          Clear filters
        </button>
      )}
    </aside>
  );
}
