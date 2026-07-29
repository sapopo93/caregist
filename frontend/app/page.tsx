import type { Metadata } from "next";
import Link from "next/link";

import DirectorySearchForm from "@/components/directory/DirectorySearchForm";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrustSignal from "@/components/TrustSignal";
import { getDirectoryFilterOptions, getDirectoryOpportunityStats } from "@/lib/directory-db";

export const metadata: Metadata = {
  title: "CQC Market Movement Intelligence | CareGist",
  description:
    "CareGist shows CQC market movement: newly registered providers, Inadequate services, Requires Improvement lists, uninspected providers, exports, monitoring, API and webhook delivery.",
};

const PRIORITY_PRODUCTS = [
  {
    rank: "1",
    title: "CQC market movement intelligence",
    buyer: "Consultants, investors, suppliers, software, policy and equipment teams",
    job: "See what changed in the CQC market and where commercial action is needed now.",
    href: "/search?opportunity=new_90",
    cta: "View movement lists",
    statKey: "totalProviders",
    statLabel: "active CQC providers tracked",
  },
  {
    rank: "2",
    title: "New provider lead lists",
    buyer: "Equipment suppliers, software companies, recruiters and policy providers",
    job: "Find newly registered services while they are buying systems, policies, tools and setup support.",
    href: "/search?opportunity=new_90",
    cta: "View new registrations",
    statKey: "newLast90Days",
    statLabel: "registered in the last 90 days",
  },
  {
    rank: "3",
    title: "At-risk provider lists",
    buyer: "Turnaround consultants, compliance specialists and quality improvement firms",
    job: "Find providers rated Inadequate or Requires Improvement that may need urgent professional support.",
    href: "/search?opportunity=inadequate",
    cta: "View at-risk providers",
    statKey: "inadequate",
    statLabel: "currently rated Inadequate",
  },
  {
    rank: "4",
    title: "Recurring monitoring and alerts",
    buyer: "Teams that need to know what changed every week, not once",
    job: "Track new registrations, rating risk, uninspected services and stale inspection signals as a workflow.",
    href: "/pricing#data-plans",
    cta: "Compare monitoring plans",
    statKey: "requiresImprovement",
    statLabel: "Requires Improvement opportunities",
  },
] as const;

const SECONDARY_PRODUCTS = [
  {
    rank: "5",
    title: "CSV exports and dataset packs",
    body: "Delivery format for buyers who need a list now. The value is the segment; CSV is how it reaches their CRM.",
    href: "/lead-list",
    cta: "Request a segment",
  },
  {
    rank: "6",
    title: "API and webhooks",
    body: "For software and data teams that want new registrations and rating movement inside their own systems.",
    href: "/api",
    cta: "Explore API",
  },
  {
    rank: "7",
    title: "Provider visibility",
    body: "Secondary product for providers who want to claim and improve their public profile.",
    href: "/pricing#provider-plans",
    cta: "See provider plans",
  },
] as const;

const OPPORTUNITY_LINKS = [
  {
    label: "New registrations",
    href: "/search?opportunity=new_90",
    valueKey: "newLast90Days",
    note: "For suppliers and setup services",
  },
  {
    label: "Inadequate",
    href: "/search?opportunity=inadequate",
    valueKey: "inadequate",
    note: "For urgent turnaround support",
  },
  {
    label: "Requires Improvement",
    href: "/search?opportunity=requires_improvement",
    valueKey: "requiresImprovement",
    note: "For quality improvement outreach",
  },
  {
    label: "Not yet inspected",
    href: "/search?opportunity=not_yet_inspected",
    valueKey: "notYetInspected",
    note: "For early-stage provider setup",
  },
] as const;

const JOURNEY = [
  {
    title: "Choose the movement",
    body: "Start with new registrations, Inadequate providers, Requires Improvement providers, or Not Yet Inspected services.",
  },
  {
    title: "Open the live list",
    body: "Filter by region, service type and rating, then inspect provider details before outreach.",
  },
  {
    title: "Export or monitor",
    body: "Request a CSV lead list for immediate sales work, or move to monitoring for recurring updates.",
  },
  {
    title: "Connect the workflow",
    body: "Use API and webhook delivery when market movement needs to land inside CRM or internal tools.",
  },
] as const;

type StatKey = keyof Awaited<ReturnType<typeof getDirectoryOpportunityStats>>;

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

      <section className="border-b border-stone bg-charcoal px-6 py-10 text-cream md:py-14">
        <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber">
              CQC market movement intelligence
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-extrabold leading-[1.04] text-cream md:text-6xl">
              Find the care providers that need action now.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-stone">
              CareGist turns CQC change signals into commercial opportunity lists: newly registered
              providers, Inadequate services, Requires Improvement providers, and services not yet inspected.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href="/search?opportunity=new_90"
                className="rounded-xl bg-amber px-5 py-3 text-sm font-semibold text-charcoal transition hover:bg-cream"
              >
                View new registrations
              </Link>
              <Link
                href="/search?opportunity=inadequate"
                className="rounded-xl border border-cream/25 px-5 py-3 text-sm font-semibold text-cream transition hover:bg-white/10"
              >
                View Inadequate providers
              </Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {OPPORTUNITY_LINKS.map((item) => (
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

      <section className="border-b border-stone px-6 py-10">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Top products</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">Priority order without the noise</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              The product is intelligence first. Search, CSV, API and provider visibility are routes into that intelligence.
            </p>
          </div>

          <div className="grid gap-4 lg:grid-cols-4">
            {PRIORITY_PRODUCTS.map((product) => (
              <article key={product.rank} className="rounded-xl border border-stone bg-cream p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm font-extrabold text-clay">Priority {product.rank}</p>
                  <p className="text-right text-sm font-semibold text-bark">{getStat(product.statKey)}</p>
                </div>
                <h3 className="mt-4 text-2xl font-bold leading-tight text-bark">{product.title}</h3>
                <p className="mt-3 text-xs font-semibold uppercase tracking-[0.14em] text-moss">{product.buyer}</p>
                <p className="mt-3 text-sm leading-6 text-dusk">{product.job}</p>
                <p className="mt-4 text-xs text-dusk">{product.statLabel}</p>
                <Link href={product.href} className="mt-5 inline-flex text-sm font-semibold text-clay hover:text-bark">
                  {product.cta}
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-stone px-6 py-10">
        <div className="mx-auto max-w-6xl">
          <DirectorySearchForm
            action="/search"
            options={filterOptions}
            title="Open an opportunity list"
            description="Choose the change signal first, then narrow by region, service type, rating, or provider name."
            submitLabel="Open list"
          />
        </div>
      </section>

      <section className="border-b border-stone px-6 py-10">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[0.75fr_1.25fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Customer journey</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">From CQC change to sales workflow</h2>
            <p className="mt-4 text-sm leading-6 text-dusk">
              Visitors should know exactly where to go: pick the market signal, open the list, then export,
              monitor, or integrate it.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {JOURNEY.map((step, index) => (
              <article key={step.title} className="rounded-xl border border-stone bg-cream p-5 shadow-sm">
                <p className="text-sm font-extrabold text-clay">Step {index + 1}</p>
                <h3 className="mt-3 text-xl font-bold text-bark">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-dusk">{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-10">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Delivery products</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">How buyers receive the intelligence</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {SECONDARY_PRODUCTS.map((product) => (
              <article key={product.rank} className="rounded-xl border border-stone bg-cream p-5 shadow-sm">
                <p className="text-sm font-extrabold text-clay">Priority {product.rank}</p>
                <h3 className="mt-3 text-xl font-bold text-bark">{product.title}</h3>
                <p className="mt-3 text-sm leading-6 text-dusk">{product.body}</p>
                <Link href={product.href} className="mt-5 inline-flex text-sm font-semibold text-clay hover:text-bark">
                  {product.cta}
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-12">
        <EmailCaptureStrip
          source="homepage"
          heading="Get weekly CQC movement updates."
          subheading="Receive newly registered providers, rating-risk segments, and product updates for lead lists, monitoring, exports, and API workflows."
        />
      </section>

      <TrustSignal />
    </div>
  );
}
