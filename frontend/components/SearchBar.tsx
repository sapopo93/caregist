"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function SearchBar({ defaultValue = "" }: { defaultValue?: string }) {
  const [query, setQuery] = useState(defaultValue);
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 w-full max-w-2xl">
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
    </form>
  );
}
