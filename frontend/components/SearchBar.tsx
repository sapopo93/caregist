"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import Link from "next/link";

const REGIONS = [
  "South East", "London", "North West", "East", "West Midlands",
  "South West", "Yorkshire & Humberside", "East Midlands", "North East",
];

const RATINGS = [
  "Outstanding", "Good", "Requires Improvement", "Inadequate", "Not Yet Inspected",
];

// UK postcode pattern
const POSTCODE_RE = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d?[A-Z]{0,2}$/i;

export default function SearchBar({
  defaultValue = "",
  defaultRegion = "",
  defaultRating = "",
  defaultServiceType = "",
  defaultPostcode = "",
  showAdvancedToggle = true,
  fetchServiceTypes = true,
}: {
  defaultValue?: string;
  defaultRegion?: string;
  defaultRating?: string;
  defaultServiceType?: string;
  defaultPostcode?: string;
  showAdvancedToggle?: boolean;
  fetchServiceTypes?: boolean;
}) {
  const [query, setQuery] = useState(defaultValue);
  const [advanced, setAdvanced] = useState(
    !!(defaultRegion || defaultRating || defaultServiceType || defaultPostcode)
  );
  const [region, setRegion] = useState(defaultRegion);
  const [rating, setRating] = useState(defaultRating);
  const [serviceType, setServiceType] = useState(defaultServiceType);
  const [postcode, setPostcode] = useState(defaultPostcode);
  const [serviceTypes, setServiceTypes] = useState<string[]>([]);
  const [postcodeDetected, setPostcodeDetected] = useState(false);
  const router = useRouter();

  // Load service types dynamically from API
  useEffect(() => {
    if (!fetchServiceTypes) return;

    fetch("/api/v1/service-types")
      .then((r) => (r.ok ? r.json() : { data: [] }))
      .then((d) => {
        const types = (d.data || []).map((t: any) => t.service_type).filter(Boolean);
        if (types.length > 0) setServiceTypes(types);
      })
      .catch(() => {});
  }, [fetchServiceTypes]);

  // Detect postcode in main query
  useEffect(() => {
    setPostcodeDetected(POSTCODE_RE.test(query.trim()));
  }, [query]);

  const filterCount = [region, rating, serviceType, postcode].filter(Boolean).length;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    params.set("q", query.trim());
    if (advanced) {
      if (region) params.set("region", region);
      if (rating) params.set("rating", rating);
      if (serviceType) params.set("service_type", serviceType);
      if (postcode.trim()) params.set("postcode", postcode.trim());
    }
    router.push(`/search?${params.toString()}`);
  };

  // Fallback service types if API call fails
  const displayTypes = serviceTypes.length > 0
    ? serviceTypes
    : ["Homecare Agencies", "Residential Homes", "Nursing Homes", "Doctors/Gps", "Dentist", "Supported Living"];

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      {/* Main search row */}
      <div className="flex gap-2">
        <label htmlFor="provider-search" className="sr-only">Search care providers</label>
        <input
          id="provider-search"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name, postcode, town, or service type..."
          aria-label="Search care providers by name, postcode, town, or service type"
          className="flex-1 px-4 py-3 rounded-lg border border-stone bg-cream text-charcoal placeholder-dusk focus:outline-none focus:ring-2 focus:ring-clay"
        />
        <button
          type="submit"
          className="px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
        >
          Search
        </button>
      </div>

      {/* Postcode detection hint */}
      {postcodeDetected && (
        <div className="mt-2 bg-amber/10 border border-amber/30 rounded-lg px-3 py-2 text-xs text-charcoal flex items-center gap-2">
          <span>Looks like a postcode.</span>
          <Link
            href={`/find-care?postcode=${encodeURIComponent(query.trim())}&radius_miles=5`}
            className="text-clay underline font-medium"
          >
            Find care near {query.trim().toUpperCase()} instead?
          </Link>
        </div>
      )}

      {/* Toggle */}
      {showAdvancedToggle && (
        <div className="mt-2 flex items-center gap-2">
          <button
            type="button"
            onClick={() => setAdvanced(!advanced)}
            className="text-xs text-dusk hover:text-clay transition-colors flex items-center gap-1"
          >
            <span className="inline-block transition-transform" style={{ transform: advanced ? "rotate(90deg)" : "rotate(0deg)" }}>
              &#9654;
            </span>
            {advanced ? "Simple search" : "Advanced search"}
            {filterCount > 0 && (
              <span className="ml-1 bg-clay text-white text-[10px] font-bold w-4 h-4 rounded-full inline-flex items-center justify-center">
                {filterCount}
              </span>
            )}
          </button>
          {advanced && filterCount > 0 && (
            <button
              type="button"
              onClick={() => { setRegion(""); setRating(""); setServiceType(""); setPostcode(""); }}
              className="text-xs text-clay underline hover:text-bark"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Advanced filters */}
      {showAdvancedToggle && advanced && (
        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label htmlFor="adv-region" className="block text-xs font-medium text-dusk mb-1">Region</label>
            <select
              id="adv-region"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm"
            >
              <option value="">All regions</option>
              {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="adv-rating" className="block text-xs font-medium text-dusk mb-1">CQC Rating</label>
            <select
              id="adv-rating"
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm"
            >
              <option value="">All ratings</option>
              {RATINGS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="adv-service" className="block text-xs font-medium text-dusk mb-1">Service Type</label>
            <select
              id="adv-service"
              value={serviceType}
              onChange={(e) => setServiceType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm"
            >
              <option value="">All types</option>
              {displayTypes.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="adv-postcode" className="block text-xs font-medium text-dusk mb-1">Postcode area</label>
            <input
              id="adv-postcode"
              type="text"
              value={postcode}
              onChange={(e) => setPostcode(e.target.value)}
              placeholder="e.g. BH1"
              className="w-full px-3 py-2 rounded-lg border border-stone bg-cream text-charcoal text-sm placeholder-dusk"
            />
          </div>
        </div>
      )}
    </form>
  );
}
