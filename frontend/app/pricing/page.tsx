import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";

import PricingCTA from "@/components/PricingCTA";
import RetainedPlanFocus from "@/components/RetainedPlanFocus";
import {
  CQC_INDEPENDENCE_LINE,
  PRICING_LADDER,
} from "@/lib/caregist-config";
import { loadCommercialCheckoutReadiness } from "@/lib/commercial-readiness";
import { pricingPlanCardId } from "@/lib/pricing-plan-path";
import { getServerApiBase } from "@/lib/server-api-config";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "CareGist Products | Territory Research and CQC Intelligence",
  description:
    "The £795 Territory Opportunity Brief, plus free CQC directory access and product availability information.",
};

const PLAN_BADGES: Record<string, string> = {
  "Free Directory": "Discovery",
  "Radar Regional": "Roadmap",
  "Radar National": "Roadmap",
  "Intelligence Feed Pilot": "Roadmap",
  "Embedded Enterprise": "Roadmap",
};

export default async function PricingPage() {
  const checkoutReady = await loadCommercialCheckoutReadiness(getServerApiBase());
  const checkoutEnabled =
    process.env.BILLING_CHECKOUT_ENABLED === "true" &&
    process.env.RADAR_CHECKOUT_ENABLED === "true" &&
    checkoutReady;
  const termsVersion = process.env.B2B_TERMS_VERSION?.trim() || "";

  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <header className="mx-auto mb-12 max-w-4xl text-center">
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-clay">
          CareGist products
        </p>
        <h1 className="mb-5 text-4xl font-bold text-bark">
          One research product is available today.
        </h1>
        <p className="text-lg leading-8 text-dusk" style={{ fontFamily: "Lora" }}>
          The Territory Opportunity Brief gives your team a buyer-specific care-market
          research pack. The Directory remains free. Other CareGist products are not
          currently available for purchase.
        </p>
      </header>

      <section className="mb-12 rounded-2xl border-2 border-clay bg-cream p-7 shadow-lg ring-2 ring-amber/20 md:p-9" aria-label="Available now">
        <div className="grid gap-7 md:grid-cols-[1.4fr_0.8fr] md:items-start">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-clay">Available now</p>
            <h2 className="mt-2 text-3xl font-bold text-bark">Territory Opportunity Brief</h2>
            <p className="mt-3 max-w-2xl text-base leading-7 text-dusk">
              A buyer-specific shortlist of 25 to 50 care organisations, a CRM-ready dataset,
              source links and observation dates, plus a three to five page executive brief.
            </p>
            <p className="mt-4 text-sm font-medium text-bark">Delivery target: three working days after scope and source-path checks are complete.</p>
          </div>
          <div className="rounded-xl border border-stone bg-parchment p-5 md:text-right">
            <p className="text-3xl font-bold text-clay">£795</p>
            <p className="mt-1 text-xs text-dusk">No VAT is charged while CareGist is not VAT-registered.</p>
            <Link href="/territory-opportunity-brief" className="mt-5 inline-block rounded-lg bg-clay px-5 py-3 text-sm font-semibold text-white transition hover:bg-bark">
              View the full offer
            </Link>
          </div>
        </div>
      </section>

      <Suspense fallback={null}>
        <RetainedPlanFocus />
      </Suspense>

      <section className="space-y-6" aria-label="Directory and roadmap products">
        <div>
          <h2 className="text-2xl font-bold text-bark">Directory and roadmap products</h2>
          <p className="mt-2 text-sm text-dusk">The Directory is free. The products marked roadmap are shown for context and cannot be bought today.</p>
        </div>
        {PRICING_LADDER.map((tier) => {
          const isFree = tier.tier === "Free Directory";
          const isIntegration =
            tier.tier === "Intelligence Feed Pilot" || tier.tier === "Embedded Enterprise";

          return (
            <article
              key={tier.tier}
              id={pricingPlanCardId(tier.tier) || undefined}
              tabIndex={-1}
              className={`scroll-mt-24 rounded-xl border bg-cream p-6 focus:outline-none focus:ring-4 focus:ring-amber/50 ${
                tier.recommended
                  ? "border-2 border-clay shadow-lg ring-2 ring-amber/20"
                  : "border-stone"
              }`}
              style={{ borderLeftWidth: 4, borderLeftColor: tier.color }}
            >
              <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="mb-2 flex flex-wrap items-center gap-3">
                    <h2 className="text-2xl font-bold text-bark">{tier.tier}</h2>
                    <span className="rounded bg-parchment px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-dusk">
                      {PLAN_BADGES[tier.tier]}
                    </span>
                  </div>
                  <p className="max-w-2xl text-sm text-dusk">{tier.forWho}</p>
                </div>
                <div className="shrink-0 md:text-right">
                  <p className="text-2xl font-bold" style={{ color: tier.color }}>
                    {tier.price}
                  </p>
                  {tier.priceNote && (
                    <p className="mt-1 max-w-sm font-mono text-xs text-dusk">{tier.priceNote}</p>
                  )}
                </div>
              </div>

              <div className="grid gap-6 md:grid-cols-[1.4fr_1fr]">
                <div>
                  <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.16em] text-dusk">
                    Included
                  </p>
                  <ul className="space-y-2">
                    {tier.includes.map((item) => (
                      <li key={item} className="text-sm text-charcoal">
                        <span className="mr-2 text-moss">✓</span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-lg border border-stone bg-parchment p-4">
                  <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.16em] text-dusk">
                    Commercial boundary
                  </p>
                  <p className="mb-3 text-sm text-bark">{tier.limit}</p>
                  {tier.pricingLogic && (
                    <p className="text-sm leading-6 text-dusk">{tier.pricingLogic}</p>
                  )}
                </div>
              </div>

              <div className="mt-6 border-t border-stone pt-5">
                <PricingCTA
                  tier={tier.tier}
                  isFreeTier={isFree}
                  checkoutEnabled={checkoutEnabled && !isIntegration}
                  termsVersion={termsVersion}
                />
              </div>
            </article>
          );
        })}
      </section>

      <section className="mt-10 rounded-xl border border-stone bg-parchment p-6">
        <h2 className="mb-2 text-xl font-bold text-bark">Product boundaries</h2>
        <p className="text-sm leading-6 text-dusk">
          CareGist does not sell paid listing rank, speculative vacancy claims or predictive
          scores. The Territory Opportunity Brief is bespoke research with a confirmed scope,
          factual selection reasons and public-source evidence. It does not claim buying intent
          or a commercial result.
        </p>
      </section>

      <footer className="mt-8 space-y-2 text-center text-xs text-dusk">
        <p>CareGist is not currently VAT registered, so VAT is not currently charged.</p>
        <p>
          CQC information is reused under the Open Government Licence v3.0. {CQC_INDEPENDENCE_LINE}
        </p>
      </footer>
    </main>
  );
}
