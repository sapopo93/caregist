"use client";

import { useRouter, useSearchParams } from "next/navigation";

const SORT_OPTIONS = [
  { value: "relevance", label: "Relevance" },
  { value: "name", label: "Name (A-Z)" },
  { value: "rating", label: "Best Rating" },
  { value: "quality", label: "Quality Score" },
  { value: "beds", label: "Most Beds" },
  { value: "newest", label: "Newest" },
];

export default function InlineSortSelect() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const current = searchParams.get("sort") || "relevance";

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("sort", e.target.value);
    router.push(`/search?${params.toString()}`);
  }

  return (
    <select
      value={current}
      onChange={handleChange}
      className="px-2 py-1 text-xs rounded border border-stone bg-cream text-charcoal"
    >
      {SORT_OPTIONS.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}
