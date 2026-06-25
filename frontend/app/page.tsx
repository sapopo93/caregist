import type { Metadata } from "next";
import Link from "next/link";

import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import SearchBar from "@/components/SearchBar";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrustSignal from "@/components/TrustSignal";

export const metadata: Metadata = {
  title: "CareGist | CQC Data Products, Lead Lists, API & Provider Listings",
  description:
    "Search active CQC providers, request gated lead-list exports, buy dataset packs, start intelligence subscriptions, explore the API, and upgrade provider listings.",
};

const CURRENT_PRODUCTS = [
  {
    tag: "Directory",
    title: "Public provider search",
    body:
      "Search active CQC providers by name, town, region, service type, and rating, then drill into provider detail pages.",
    href: "/search",
    cta: "Search providers",
  },
  {
    tag: "Lead lists",
    title: "Filtered CSV requests",
    body:
      "Capture segmented lead-list demand by region, service type, and rating, then issue a gated export token immediately.",
    href: "/lead-list",
    cta: "Request a lead list",
  },
  {
    tag: "Dataset sales",
    title: "Full dataset / regional pack",
    body:
      "Send broader buyers through the Stripe payment path for full-dataset and regional-pack purchases.",
    href: null,
    cta: "Buy dataset pack",
  },
  {
    tag: "Subscriptions",
    title: "New-provider intelligence plans",
    body:
      "Alerts Pro, Data Starter, Data Pro, and Data Business cover monitoring, recurring exports, saved filters, digests, and CRM workflows.",
    href: "/pricing#data-plans",
    cta: "See intelligence plans",
  },
  {
    tag: "API",
    title: "API, CRM, and webhooks",
    body:
      "Use CareGist through no-code exports, API integration, or Data Business webhook delivery for operational workflows.",
    href: "/api",
    cta: "Explore API delivery",
  },
  {
    tag: "Provider visibility",
    title: "Claimed, Pro, and Sponsored listings",
    body:
      "Providers can claim listings for free, then upgrade to richer profile presentation or sponsored search placement.",
    href: "/pricing#provider-plans",
    cta: "See provider plans",
  },
] as const;

const PRODUCT_TRACKS = [
  {
    title: "Demand-side buyers",
    body:
      "For operators, analysts, commissioners, and sales teams: directory search, lead lists, dataset packs, intelligence subscriptions, API access, and webhook delivery.",
    links: [
      { href: "/pricing#data-plans", label: "New-provider intelligence plans" },
      { href: "/api", label: "API and CRM workflows" },
      { href: "/lead-list", label: "Filtered lead-list requests" },
    ],
  },
  {
    title: "Supply-side providers",
    body:
      "For care providers and groups: free claiming, profile enrichment, sponsored placement, and multi-location visibility packages.",
    links: [
      { href: "/search", label: "Find your provider page" },
      { href: "/pricing#provider-plans", label: "Provider visibility plans" },
      { href: "/why-caregist", label: "Why CareGist fits" },
    ],
  },
] as const;

const PRODUCT_EXPLANATIONS = [
  {
    title: "Public provider search",
    buyer: "Families, provider researchers, sales teams, and operators",
    useCase: "Use this when you need a searchable front door into the active CQC provider universe, with provider pages and filterable browsing.",
    positioning:
      "This is the discovery layer. It proves dataset quality publicly and creates a route into lead-list requests, provider pages, and paid data products.",
    href: "/search",
    cta: "Open search",
  },
  {
    title: "Filtered lead lists",
    buyer: "Sales teams, consultants, recruiters, and growth operators",
    useCase: "Use this when a buyer wants a defined segment now: a region, service type, and rating slice that can be fulfilled as a commercial export.",
    positioning:
      "This is the demand-capture layer. It turns search intent into a monetisable lead request before full self-serve export is expanded.",
    href: "/lead-list",
    cta: "Request a lead list",
  },
  {
    title: "Dataset packs",
    buyer: "Analysts, procurement teams, and broader data buyers",
    useCase: "Use this when the buyer wants a regional pack or wider dataset purchase without a long sales cycle.",
    positioning:
      "This is the transactional data sale. It is the shortest path from high-intent buyer to payment for broader access.",
    href: null,
    cta: "Buy dataset pack",
  },
  {
    title: "New-provider intelligence plans",
    buyer: "Commercial teams that need recurring market movement, not one-off exports",
    useCase: "Use this when you want saved filters, recurring exports, monitoring, digests, and structured new-registration workflows.",
    positioning:
      "This is the recurring-value layer. It shifts CareGist from static data access into subscription intelligence.",
    href: "/pricing#data-plans",
    cta: "See intelligence plans",
  },
  {
    title: "API and webhooks",
    buyer: "Product teams, RevOps, data teams, and workflow owners",
    useCase: "Use this when dashboard and CSV workflows are no longer enough and the data needs to feed CRM, internal systems, or automated operations.",
    positioning:
      "This is the integration layer. It positions CareGist as infrastructure inside the buyer's operating stack, not just a website.",
    href: "/api",
    cta: "Explore API",
  },
  {
    title: "Provider visibility plans",
    buyer: "Care providers and groups that want stronger visibility on CareGist",
    useCase: "Use this when the provider side wants to claim, enrich, or sponsor their presence rather than buy intelligence.",
    positioning:
      "This is the supply-side monetisation layer. It complements the data products without confusing the core buyer story.",
    href: "/pricing#provider-plans",
    cta: "See provider plans",
  },
] as const;

const ABOUT_POINTS = [
  "CareGist is the operational layer on top of CQC data, not just a public directory.",
  "We package one underlying data asset into search, lead generation, subscriptions, API workflows, and provider visibility products.",
  "The positioning is two-sided: demand-side buyers purchase intelligence and data workflows; supply-side providers purchase visibility and profile upgrades.",
] as const;

export default async function HomePage() {
  const stripePaymentLink = process.env.STRIPE_PAYMENT_LINK_URL?.trim() || null;

  return (
    <div className="bg-parchment">
      <TrackEventOnMount eventType="homepage_view" eventSource="homepage" />

      <section className="border-b border-stone bg-[radial-gradient(circle_at_top_left,_rgba(212,148,58,0.22),_transparent_30%),linear-gradient(135deg,#2b2520_0%,#4f3b2d_55%,#6b4c35_100%)] px-6 py-16 text-cream">
        <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1fr_0.95fr] lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber">
              CQC data products and provider visibility
            </p>
            <h1 className="mt-4 max-w-3xl text-5xl font-extrabold leading-[1.02] text-cream md:text-6xl">
              Search, lead lists, dataset packs, intelligence plans, API workflows, and provider listings.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-stone">
              CareGist is not just a public directory. The live product stack now spans public provider
              search, gated lead-list exports, dataset-pack checkout, recurring new-provider intelligence
              subscriptions, API and webhook delivery, plus provider visibility upgrades for claimed
              listings.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/pricing"
                className="rounded-full bg-amber px-5 py-3 text-sm font-semibold text-charcoal transition hover:bg-cream"
              >
                See pricing
              </Link>
              <Link
                href="/api"
                className="rounded-full border border-cream/20 px-5 py-3 text-sm font-semibold text-cream transition hover:bg-white/10"
              >
                Explore API
              </Link>
              <Link
                href="/search"
                className="rounded-full border border-cream/20 px-5 py-3 text-sm font-semibold text-cream transition hover:bg-white/10"
              >
                Search the directory
              </Link>
              <a
                href={stripePaymentLink ?? "/lead-list"}
                target={stripePaymentLink ? "_blank" : undefined}
                rel={stripePaymentLink ? "noreferrer noopener" : undefined}
                className="rounded-full border border-cream/20 px-5 py-3 text-sm font-semibold text-cream transition hover:bg-white/10"
              >
                Buy full dataset / regional pack
              </a>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              <div className="border-l border-amber/60 pl-4">
                <p className="text-3xl font-extrabold text-amber">56,742</p>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-stone">Active providers</p>
              </div>
              <div className="border-l border-amber/60 pl-4">
                <p className="text-3xl font-extrabold text-amber">11</p>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-stone">Regions covered</p>
              </div>
              <div className="border-l border-amber/60 pl-4">
                <p className="text-3xl font-extrabold text-amber">24</p>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-stone">Results per page</p>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-white/15 bg-cream p-6 text-charcoal shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">CQC directory</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">Search by name, town, or postcode</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              Start with the public directory, then move into lead lists, intelligence plans, or the API
              when the workflow becomes recurring.
            </p>
            <div className="mt-5">
              <SearchBar showAdvancedToggle={true} fetchServiceTypes={true} />
            </div>
          </div>
        </div>
      </section>

      <section id="products" className="px-6 py-14 scroll-mt-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-8">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Current offer stack</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">What CareGist currently sells and supports</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-dusk">
              The website should reflect the live products, not just one motion. These are the commercial
              paths and product surfaces currently active in CareGist.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {CURRENT_PRODUCTS.map((product) => (
              <div key={product.title} className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">{product.tag}</p>
                <h3 className="mt-3 text-2xl font-bold text-bark">{product.title}</h3>
                <p className="mt-3 text-sm leading-6 text-dusk">{product.body}</p>
                {product.href ? (
                  <Link href={product.href} className="mt-5 inline-flex text-sm font-semibold text-clay hover:text-bark">
                    {product.cta}
                  </Link>
                ) : (
                  <a
                    href={stripePaymentLink ?? "/lead-list"}
                    target={stripePaymentLink ? "_blank" : undefined}
                    rel={stripePaymentLink ? "noreferrer noopener" : undefined}
                    className="mt-5 inline-flex text-sm font-semibold text-clay hover:text-bark"
                  >
                    {product.cta}
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-stone px-6 py-14">
        <div className="mx-auto max-w-6xl">
          <div className="mb-8">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Product explanation</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">What each product is for</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-dusk">
              Buyers should not have to infer the commercial model from scattered CTAs. Each offer has a
              defined buyer, job, and place in the CareGist stack.
            </p>
          </div>

          <div className="space-y-4">
            {PRODUCT_EXPLANATIONS.map((product) => (
              <div
                key={product.title}
                className="grid gap-5 rounded-3xl border border-stone bg-cream p-6 shadow-sm lg:grid-cols-[0.9fr_1.1fr_0.95fr]"
              >
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Product</p>
                  <h3 className="mt-2 text-2xl font-bold text-bark">{product.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-dusk">{product.buyer}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">When to use it</p>
                  <p className="mt-2 text-sm leading-6 text-dusk">{product.useCase}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Positioning</p>
                  <p className="mt-2 text-sm leading-6 text-dusk">{product.positioning}</p>
                  {product.href ? (
                    <Link href={product.href} className="mt-4 inline-flex text-sm font-semibold text-clay hover:text-bark">
                      {product.cta}
                    </Link>
                  ) : (
                    <a
                      href={stripePaymentLink ?? "/lead-list"}
                      target={stripePaymentLink ? "_blank" : undefined}
                      rel={stripePaymentLink ? "noreferrer noopener" : undefined}
                      className="mt-4 inline-flex text-sm font-semibold text-clay hover:text-bark"
                    >
                      {product.cta}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="positioning" className="border-t border-stone px-6 py-14 scroll-mt-24">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-2">
          {PRODUCT_TRACKS.map((track) => (
            <div key={track.title} className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
              <h2 className="text-2xl font-bold text-bark">{track.title}</h2>
              <p className="mt-3 text-sm leading-6 text-dusk">{track.body}</p>
              <div className="mt-5 flex flex-wrap gap-3">
                {track.links.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-full border border-clay px-4 py-2 text-sm font-semibold text-clay hover:bg-parchment"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-stone px-6 py-14">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">About CareGist</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">What the company actually is</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              CareGist should explain itself as a data business with multiple commercial surfaces, not as a
              single-page directory with a few add-on buttons.
            </p>
            <Link
              href="/why-caregist"
              className="mt-5 inline-flex rounded-full border border-clay px-4 py-2 text-sm font-semibold text-clay hover:bg-parchment"
            >
              Read the full CareGist explanation
            </Link>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {ABOUT_POINTS.map((point) => (
              <div key={point} className="rounded-3xl border border-stone bg-cream p-5 shadow-sm">
                <p className="text-sm leading-6 text-dusk">{point}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-12 pt-4">
        <EmailCaptureStrip
          source="homepage"
          heading="Get weekly CareGist product and market updates."
          subheading="Receive new-provider movement, rating changes, and product updates for lead lists, dataset packs, and intelligence workflows."
        />
      </section>

      <TrustSignal />
    </div>
  );
}
