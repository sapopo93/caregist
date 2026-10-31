import Link from "next/link";

import type { DirectoryRegionSnapshot } from "@/lib/directory-db";

/** Rough north-to-south cartogram of the nine England regions on a 3-column board. */
const BOARD_LAYOUT: Array<{ region: string; col: number; row: number }> = [
  { region: "North East", col: 3, row: 1 },
  { region: "North West", col: 2, row: 1 },
  { region: "Yorkshire & Humberside", col: 3, row: 2 },
  { region: "West Midlands", col: 1, row: 3 },
  { region: "East Midlands", col: 2, row: 2 },
  { region: "East", col: 3, row: 3 },
  { region: "South West", col: 1, row: 4 },
  { region: "London", col: 2, row: 4 },
  { region: "South East", col: 3, row: 4 },
];

const fmt = (n: number) => n.toLocaleString("en-GB");

export default function EnglandBoard({ regions }: { regions: DirectoryRegionSnapshot[] }) {
  const byName = new Map(regions.map((r) => [r.region, r]));
  const maxTotal = Math.max(1, ...regions.map((r) => r.total));

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-clay">
        Pick your patch &middot; live from the CQC record
      </p>
      <ol className="mt-4 grid grid-cols-3 gap-2" aria-label="England regions">
        {BOARD_LAYOUT.map(({ region, col, row }) => {
          const data = byName.get(region);
          const concern = data ? ((data.inadequate + data.requiresImprovement) / Math.max(1, data.total)) * 100 : 0;
          return (
            <li key={region} style={{ gridColumn: col, gridRow: row }} className="min-w-0">
              <Link
                href={`/pricing/territory?region=${encodeURIComponent(region)}`}
                className="group relative flex h-full min-h-[7.25rem] flex-col justify-between overflow-hidden rounded-lg border border-stone bg-cream p-3 transition hover:-translate-y-0.5 hover:border-clay hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber"
              >
                <span
                  aria-hidden
                  className="absolute inset-x-0 bottom-0 bg-amber/25 transition-all group-hover:bg-amber/40"
                  style={{ height: `${data ? Math.max(8, (data.total / maxTotal) * 70) : 0}%` }}
                />
                <span className="relative text-[0.7rem] font-semibold uppercase leading-tight tracking-wide text-dusk">
                  {region}
                </span>
                <span className="relative">
                  <span className="block font-[family-name:var(--font-playfair-display)] text-2xl font-bold leading-none text-bark">
                    {data ? fmt(data.total) : "—"}
                  </span>
                  <span className="mt-1 block text-[0.7rem] leading-4 text-dusk">
                    {data ? `${concern.toFixed(0)}% rated RI or Inadequate` : "locations"}
                  </span>
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-xs leading-5 text-dusk">
        Active CQC locations per region. Height shows relative size. Choose a region to check
        coverage for your territory.
      </p>
    </div>
  );
}
