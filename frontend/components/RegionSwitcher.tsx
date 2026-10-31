import Link from "next/link";

import { regionSlug } from "@/components/Breadcrumbs";
import { DEFAULT_REGION_OPTIONS } from "@/lib/directory-constants";

/** One-click hop between the nine England region pages; the current region is marked. */
export default function RegionSwitcher({ current }: { current?: string }) {
  return (
    <nav aria-label="Switch region" className="mb-6">
      <ul className="flex gap-2 overflow-x-auto pb-1">
        {DEFAULT_REGION_OPTIONS.map((region) => {
          const active = region === current;
          return (
            <li key={region} className="shrink-0">
              <Link
                href={`/region/${regionSlug(region)}`}
                aria-current={active ? "page" : undefined}
                className={`inline-flex rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
                  active
                    ? "border-bark bg-bark text-cream"
                    : "border-stone bg-cream text-bark hover:border-clay hover:text-clay"
                }`}
              >
                {region}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
