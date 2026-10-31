import Link from "next/link";

import { regionSlug } from "@/components/Breadcrumbs";
import { DEFAULT_REGION_OPTIONS } from "@/lib/directory-constants";

interface Props {
  town: string | null;
  region: string | null;
  rating: string | null;
}

const RATINGS_WITH_FILTER = new Set(["Outstanding", "Good", "Requires improvement", "Inadequate"]);

/** Next steps from a provider page, using only filters the directory search supports. */
export default function RelatedLinks({ town, region, rating }: Props) {
  const knownRegion = region && DEFAULT_REGION_OPTIONS.includes(region) ? region : null;
  const links: Array<{ href: string; label: string }> = [];

  if (town) {
    links.push({
      href: `/search?q=${encodeURIComponent(town)}${knownRegion ? `&region=${encodeURIComponent(knownRegion)}` : ""}`,
      label: `Other providers in ${town}`,
    });
  }
  if (knownRegion && rating && RATINGS_WITH_FILTER.has(rating)) {
    links.push({
      href: `/search?region=${encodeURIComponent(knownRegion)}&rating=${encodeURIComponent(rating)}`,
      label: `Other ${rating} providers in ${knownRegion}`,
    });
  }
  if (knownRegion) {
    links.push({ href: `/region/${regionSlug(knownRegion)}`, label: `${knownRegion} at a glance` });
  }
  if (links.length === 0) return null;

  return (
    <section aria-label="Keep exploring" className="mt-6 rounded-3xl border border-stone bg-cream p-6 shadow-sm">
      <h2 className="text-2xl font-bold text-bark">Keep exploring</h2>
      <ul className="mt-4 flex flex-wrap gap-2">
        {links.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="inline-flex rounded-full border border-stone bg-white px-4 py-2 text-sm font-medium text-bark transition hover:border-clay hover:text-clay"
            >
              {link.label} →
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
