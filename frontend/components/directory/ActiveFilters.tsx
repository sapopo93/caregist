import Link from "next/link";

export interface ActiveFilter {
  param: string;
  label: string;
  value: string;
}

/** Removable chips for the filters currently applied. Each chip is a plain link, so it works without JavaScript. */
export default function ActiveFilters({ filters, params }: { filters: ActiveFilter[]; params: Record<string, string> }) {
  if (filters.length === 0) return null;

  const hrefWithout = (param: string) => {
    const next = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value && key !== param && key !== "page") next.set(key, value);
    }
    const query = next.toString();
    return query ? `/search?${query}` : "/search";
  };

  return (
    <div className="mb-5 flex flex-wrap items-center gap-2" aria-label="Active filters">
      {filters.map((filter) => (
        <Link
          key={filter.param}
          href={hrefWithout(filter.param)}
          className="group inline-flex items-center gap-2 rounded-full border border-clay/40 bg-cream px-3 py-1.5 text-sm text-bark transition hover:border-clay hover:bg-white"
          aria-label={`Remove filter ${filter.label}: ${filter.value}`}
        >
          <span className="text-dusk">{filter.label}</span>
          <span className="font-semibold">{filter.value}</span>
          <span aria-hidden className="text-clay group-hover:text-alert">×</span>
        </Link>
      ))}
      {filters.length > 1 ? (
        <Link href="/search" className="text-sm font-semibold text-clay underline underline-offset-4">
          Clear all
        </Link>
      ) : null}
    </div>
  );
}
