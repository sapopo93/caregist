import type { Metadata } from "next";
import { Suspense } from "react";

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
  title: "CareGist Pricing | CQC Signal Intelligence",
  description:
    "Evidence-linked CQC change intelligence for regional compliance firms, national teams, and scoped integrations.",
};

const PLAN_BADGES: Record<string, string> = {
  "Free Directory": "Discovery",
  "Radar Regional": "Launch plan",
  "Radar National": "National teams",
  "Intelligence Feed Pilot": "Sales-assisted",
  "Embedded Enterprise": "Quote only",
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
          CQC signal intelligence
        </p>
        <h1 className="mb-5 text-4xl font-bold text-bark">
          Pay for decisions your team can act on—not another provider database
        </h1>
        <p className="text-lg leading-8 text-dusk" style={{ fontFamily: "Lora" }}>
          Radar records verified new registrations and rating changes, preserves the
          source evidence, and delivers each signal into a repeatable compliance and
          business-development workflow.
        </p>
      </header>

      <Suspense fallback={null}>
        <RetainedPlanFocus />
      </Suspense>

      <section className="space-y-6" aria-label="CareGist products">
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
        <h2 className="mb-2 text-xl font-bold text-bark">What we do not sell</h2>
        <p className="text-sm leading-6 text-dusk">
          CareGist does not sell static data packs, paid listing rank, speculative vacancy
          claims, or predictive scores. Radar launches with two traceable signal types:
          new registrations and rating changes. A verified raw event still ships when an
          explanation is unavailable.
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
