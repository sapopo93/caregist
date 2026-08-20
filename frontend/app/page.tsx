import type { Metadata } from "next";
import Link from "next/link";

import DirectorySearchForm from "@/components/directory/DirectorySearchForm";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrustSignal from "@/components/TrustSignal";
import { getDirectoryFilterOptions, getDirectoryOpportunityStats } from "@/lib/directory-db";

export const metadata: Metadata = {
  title: "CareGist | Evidence-linked CQC Signal Intelligence",
  description:
    "Discover CQC-registered services for free, or use CareGist Radar to turn verified new registrations and rating changes into traceable team workflows.",
};

type StatKey = keyof Awaited<ReturnType<typeof getDirectoryOpportunityStats>>;

const FACT_LINKS: Array<{
  label: string;
  href: string;
  valueKey: StatKey;
  note: string;
}> = [
  {
    label: "New registrations",
    href: "/search?opportunity=new_90",
    valueKey: "newLast90Days",
    note: "Locations first registered in the last 90 days",
  },
  {
    label: "Inadequate",
    href: "/search?opportunity=inadequate",
    valueKey: "inadequate",
    note: "Locations currently carrying this overall CQC rating",
  },
  {
    label: "Requires Improvement",
    href: "/search?opportunity=requires_improvement",
    valueKey: "requiresImprovement",
    note: "Locations currently carrying this overall CQC rating",
  },
  {
    label: "No published rating",
    href: "/search?rating=No%20published%20rating",
    valueKey: "noPublishedRating",
    note: "Locations currently carrying this exact overall CQC rating",
  },
];

const DIFFERENCE = [
  {
    title: "Change, not catalogue churn",
    body: "Radar is built around canonical events with stable CQC location IDs, rather than repeated exports of mutable provider rows.",
  },
  {
    title: "Evidence travels with the signal",
    body: "Source URL, observation times, and entity level support traceability. Reconciled snapshot metadata, including a checksum when available, is reported on Data Status.",
    href: "/data-status",
  },
  {
    title: "Safe when intelligence is incomplete",
    body: "A verified raw event still ships if an explanation cannot meet the evidence gate. CareGist does not fill gaps with speculation.",
  },
];

function formatCount(value: number) {
  return value.toLocaleString("en-GB");
}

export default async function HomePage() {
  const [filterOptions, stats] = await Promise.all([
    getDirectoryFilterOptions().catch(() => null),
    getDirectoryOpportunityStats(),
  ]);

  const getStat = (key: StatKey) => formatCount(Number(stats[key] ?? 0));

  return (
    <div className="bg-parchment">
      <TrackEventOnMount eventType="homepage_view" eventSource="homepage" />

      <section className="border-b border-stone bg-charcoal px-6 py-12 text-cream md:py-16">
        <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber">
              CQC signal intelligence
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-extrabold leading-[1.04] md:text-6xl">
              Know what changed. See the evidence. Decide what to do next.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-stone">
              CareGist turns verified CQC new registrations and rating changes into a
              traceable workflow for compliance and quality-improvement teams. The
              directory remains free for discovery and source checking.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href="/pricing"
                className="rounded-xl bg-amber px-5 py-3 text-sm font-semibold text-charcoal transition hover:bg-cream"
              >
                Compare Radar plans
              </Link>
              <Link
                href="/search"
                className="rounded-xl border border-cream/25 px-5 py-3 text-sm font-semibold transition hover:bg-white/10"
              >
                Search the free directory
              </Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {FACT_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-xl border border-white/12 bg-cream p-5 text-charcoal shadow-sm transition hover:border-amber"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-clay">{item.label}</p>
                <p className="mt-3 text-4xl font-extrabold text-bark">{getStat(item.valueKey)}</p>
                <p className="mt-2 text-sm leading-6 text-dusk">{item.note}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-stone px-6 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="mb-7 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Why CareGist</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">Built to support a decision, not to sell rows</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {DIFFERENCE.map((item) => (
              <article key={item.title} className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
                <h3 className="text-xl font-bold text-bark">{item.title}</h3>
                <p className="mt-3 text-sm leading-6 text-dusk">{item.body}</p>
                {"href" in item && item.href ? (
                  <Link href={item.href} className="mt-4 inline-flex text-sm font-semibold text-clay underline">
                    Review Data Status
                  </Link>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-stone px-6 py-12">
        <div className="mx-auto max-w-6xl">
          <DirectorySearchForm
            action="/search"
            options={filterOptions}
            title="Search the free CQC directory"
            description="Filter factual CQC location records by geography, service type, rating, registration recency, or provider name. Always confirm operational decisions against the linked official source."
            submitLabel="Search providers"
          />
        </div>
      </section>

      <section className="px-6 py-12">
        <div className="mx-auto grid max-w-6xl gap-4 md:grid-cols-3">
          <article className="rounded-xl border border-stone bg-cream p-6">
            <p className="font-mono text-xs uppercase tracking-wider text-clay">Radar</p>
            <h2 className="mt-3 text-2xl font-bold text-bark">Regional or National</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              Evidence-linked new registrations and rating changes for human teams. No API is bundled.
            </p>
            <Link href="/pricing" className="mt-5 inline-flex text-sm font-semibold text-clay">View Radar pricing</Link>
          </article>
          <article className="rounded-xl border border-stone bg-cream p-6">
            <p className="font-mono text-xs uppercase tracking-wider text-clay">Integration</p>
            <h2 className="mt-3 text-2xl font-bold text-bark">Intelligence Feed Pilot</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              A narrowly scoped API and signed-webhook pilot with replay, cursors, and delivery health.
            </p>
            <Link href="/intelligence-feed" className="mt-5 inline-flex text-sm font-semibold text-clay">Explore the Feed pilot</Link>
          </article>
          <article className="rounded-xl border border-stone bg-cream p-6">
            <p className="font-mono text-xs uppercase tracking-wider text-clay">Enterprise</p>
            <h2 className="mt-3 text-2xl font-bold text-bark">Embedded Enterprise</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              White-label and regulated use under a qualified scope, security review, and contracted SLA.
            </p>
            <a href="mailto:enterprise@caregist.co.uk?subject=Embedded+Enterprise" className="mt-5 inline-flex text-sm font-semibold text-clay">Discuss a qualified scope</a>
          </article>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-12">
        <EmailCaptureStrip
          source="homepage"
          heading="Follow CareGist product readiness."
          subheading="Receive evidence-linked CQC signal updates and availability notices. No predictive scores or unsupported opportunity claims."
        />
      </section>

      <TrustSignal />
    </div>
  );
}
