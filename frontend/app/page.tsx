import type { Metadata } from "next";
import { TERRITORY_BRIEF_PRICE_GBP, WEEKLY_DIGEST_PILOT_PRICE_GBP } from "@/lib/caregist-config";
import Link from "next/link";

import DirectorySearchForm from "@/components/directory/DirectorySearchForm";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrustSignal from "@/components/TrustSignal";
import PricingGlance from "@/components/PricingGlance";
import RecentlyViewed from "@/components/RecentlyViewed";
import EvidenceTrail from "@/components/home/EvidenceTrail";
import EnglandBoard from "@/components/home/EnglandBoard";
import { getDirectoryFilterOptions, getDirectoryOpportunityStats, getDirectoryRegionSnapshot } from "@/lib/directory-db";

export const metadata: Metadata = {
  title: "CareGist | Evidence-linked CQC Signal Intelligence",
  description:
    "Discover CQC-registered services for free, buy the Weekly Digest for one England region, or commission a Territory Opportunity Brief on which organisations to investigate next.",
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
    note: "Locations carrying this overall CQC rating: CQC's published ratings file, updated where CQC's website shows a newer report",
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

function formatCount(value: number) {
  return value.toLocaleString("en-GB");
}

export default async function HomePage() {
  const [filterOptions, stats, regionSnapshot] = await Promise.all([
    getDirectoryFilterOptions().catch(() => null),
    getDirectoryOpportunityStats(),
    getDirectoryRegionSnapshot().catch(() => []),
  ]);

  const getStat = (key: StatKey) => formatCount(Number(stats[key] ?? 0));

  return (
    <div className="bg-parchment">
      <TrackEventOnMount eventType="homepage_view" eventSource="homepage" />

      <section className="border-b border-stone px-6 pb-10 pt-12 md:pt-16">
        <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-clay">
              CQC signal intelligence
            </p>
            <h1 className="mt-4 max-w-3xl text-5xl font-extrabold leading-[0.98] tracking-tight text-charcoal md:text-7xl">
              Know what changed. <span className="text-clay">See the evidence.</span> Decide what next.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-dusk">
              CareGist follows verified CQC new registrations, rating changes, and
              closures for one England region at a time, with the published record behind
              every item. The directory remains free for discovery and source checking.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link href="/pricing/territory" className="cta-primary">
                Check your territory
              </Link>
              <Link href="/pricing" className="cta-secondary">
                See the two products
              </Link>
              <Link
                href="/search"
                className="inline-flex min-h-12 items-center px-2 py-3 text-sm font-semibold text-dusk underline underline-offset-4 transition hover:text-bark"
              >
                Search the free directory
              </Link>
            </div>
          </div>
          <EnglandBoard regions={regionSnapshot} />
        </div>

        <div className="mx-auto mt-10 max-w-6xl"><RecentlyViewed /></div>

        <dl className="mx-auto grid max-w-6xl gap-px overflow-hidden rounded-xl border border-stone bg-stone sm:grid-cols-2 lg:grid-cols-4">
          {FACT_LINKS.map((item) => (
            <Link key={item.href} href={item.href} className="group bg-cream p-4 transition hover:bg-white">
              <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">{item.label}</dt>
              <dd className="mt-1 text-3xl font-extrabold text-bark group-hover:text-clay">{getStat(item.valueKey)}</dd>
              <p className="mt-1 text-xs leading-5 text-dusk">{item.note}</p>
              {item.valueKey === "inadequate" && Number(stats.inadequateInCqcFile) > Number(stats.inadequate) ? (
                <p className="mt-2 text-xs leading-5 text-dusk">
                  CQC&apos;s public API currently returns a rating for this many. CQC&apos;s own published ratings file
                  lists {formatCount(Number(stats.inadequateInCqcFile))} active locations as Inadequate; the API
                  omits the rest, so this figure understates CQC&apos;s.
                </p>
              ) : null}
            </Link>
          ))}
        </dl>
      </section>

      <section className="border-b border-stone px-6 py-14">
        <div className="mx-auto max-w-6xl">
          <div className="mb-9 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Why CareGist</p>
            <h2 className="mt-3 text-3xl font-bold text-bark md:text-4xl">
              Built to support a decision, not to sell rows
            </h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              Change, not catalogue churn: every signal carries its evidence from the CQC record to your inbox. Reconciled snapshot metadata, including a checksum when available, is reported on Data Status.
            </p>
          </div>
          <EvidenceTrail />
        </div>
      </section>

      <section id="products" className="border-b border-stone px-6 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="mb-7 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Products</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">Two products, both built on the published record</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              CareGist sells two products: a Weekly Digest of movement in one England region
              (&pound;{WEEKLY_DIGEST_PILOT_PRICE_GBP} for four weekly issues), and a one-off Territory
              Opportunity Brief on the organisations to investigate (&pound;{TERRITORY_BRIEF_PRICE_GBP}).
            </p>
          </div>
          <PricingGlance />
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
