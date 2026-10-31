import Link from "next/link";

import type { DirectoryRegionSnapshot } from "@/lib/directory-db";

const SEGMENTS = [
  { key: "outstanding", label: "Outstanding", tone: "bg-moss" },
  { key: "good", label: "Good", tone: "bg-sage" },
  { key: "requiresImprovement", label: "Requires improvement", tone: "bg-amber" },
  { key: "inadequate", label: "Inadequate", tone: "bg-alert" },
] as const;

const fmt = (n: number) => n.toLocaleString("en-GB");

/** At-a-glance briefing for one England region, from the directory snapshot. Only published ratings are coloured. */
export default function RegionBriefing({ snapshot }: { snapshot: DirectoryRegionSnapshot }) {
  const rated = SEGMENTS.reduce((sum, s) => sum + snapshot[s.key], 0);
  const other = Math.max(0, snapshot.total - rated);
  const pct = (n: number) => (snapshot.total ? (n / snapshot.total) * 100 : 0);

  return (
    <section aria-label={`${snapshot.region} at a glance`} className="mb-8 rounded-2xl border border-stone bg-cream p-6 shadow-sm">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-clay">{snapshot.region} at a glance</p>
          <p className="mt-2 font-[family-name:var(--font-playfair-display)] text-5xl font-bold leading-none text-bark">
            {fmt(snapshot.total)}
          </p>
          <p className="mt-1 text-sm text-dusk">active CQC-registered locations</p>
        </div>
        <Link href={`/pricing/territory?region=${encodeURIComponent(snapshot.region)}`} className="cta-primary">
          Check coverage in {snapshot.region}
        </Link>
      </div>

      <div
        role="img"
        aria-label={`Rating mix: ${SEGMENTS.map((s) => `${fmt(snapshot[s.key])} ${s.label}`).join(", ")}, ${fmt(other)} not published or not yet rated`}
        className="mt-6 flex h-4 overflow-hidden rounded-full bg-stone/60"
      >
        {SEGMENTS.map((s) => (
          <span key={s.key} className={s.tone} style={{ width: `${pct(snapshot[s.key])}%` }} />
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-dusk">
        {SEGMENTS.map((s) => (
          <li key={s.key} className="inline-flex items-center gap-1.5">
            <span aria-hidden className={`h-2.5 w-2.5 rounded-sm ${s.tone}`} />
            {s.label} <span className="font-semibold text-bark">{fmt(snapshot[s.key])}</span>
          </li>
        ))}
        <li className="inline-flex items-center gap-1.5">
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-stone" />
          No published rating <span className="font-semibold text-bark">{fmt(other)}</span>
        </li>
      </ul>

      <dl className="mt-5 grid gap-px overflow-hidden rounded-xl border border-stone bg-stone sm:grid-cols-3">
        <Link href={`/search?region=${encodeURIComponent(snapshot.region)}&opportunity=new_90`} className="bg-white p-4 transition hover:bg-parchment">
          <dt className="text-xs uppercase tracking-wide text-dusk">Registered in last 90 days</dt>
          <dd className="mt-1 text-2xl font-bold text-bark">{fmt(snapshot.newLast90Days)}</dd>
        </Link>
        <Link href={`/search?region=${encodeURIComponent(snapshot.region)}&opportunity=requires_improvement`} className="bg-white p-4 transition hover:bg-parchment">
          <dt className="text-xs uppercase tracking-wide text-dusk">Requires improvement</dt>
          <dd className="mt-1 text-2xl font-bold text-bark">{fmt(snapshot.requiresImprovement)}</dd>
        </Link>
        <Link href={`/search?region=${encodeURIComponent(snapshot.region)}&opportunity=inadequate`} className="bg-white p-4 transition hover:bg-parchment">
          <dt className="text-xs uppercase tracking-wide text-dusk">Inadequate</dt>
          <dd className="mt-1 text-2xl font-bold text-bark">{fmt(snapshot.inadequate)}</dd>
        </Link>
      </dl>
    </section>
  );
}
