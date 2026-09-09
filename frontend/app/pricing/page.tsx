import type { Metadata } from "next";
import { Suspense } from "react";

import PricingCTA from "@/components/PricingCTA";
import RetainedPlanFocus from "@/components/RetainedPlanFocus";
import {
  CQC_INDEPENDENCE_LINE,
  PRICING_LADDER,
} from "@/lib/caregist-config";
import { pricingPlanCardId } from "@/lib/pricing-plan-path";

export const metadata: Metadata = {
  title: "CareGist Pricing | CQC Signal Intelligence",
  description:
    "One-off territory and market-movement intelligence for teams selling into the UK care sector.",
};

const PLAN_BADGES: Record<string, string> = {
  "Territory Opportunity Brief": "Lead product",
  "Market Movement Report": "Current edition",
  "Free Directory": "Discovery",
  "Radar Regional": "Request access · not yet available",
  "Radar National": "Request access · not yet available",
  "Strategic Territory Intelligence Assignment": "Roadmap · not yet available",
  "Founding Intelligence Membership": "Roadmap · not yet available",
  "Intelligence Feed Pilot": "Roadmap · not yet available",
  "Embedded Enterprise": "Roadmap · not yet available",
};

export default function PricingPage() {
  const checkoutEnabled =
    process.env.BILLING_CHECKOUT_ENABLED === "true" &&
    process.env.RADAR_CHECKOUT_ENABLED === "true";
  const termsVersion = process.env.B2B_TERMS_VERSION?.trim() || "";

  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <header className="mx-auto mb-12 max-w-4xl text-center">
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-clay">
          CQC signal intelligence
        </p>
        <h1 className="mb-5 text-4xl font-bold text-bark">
          Decide which care organisations are worth approaching next, and why
        </h1>
        <p className="text-lg leading-8 text-dusk" style={{ fontFamily: "Lora" }}>
          Start with a ranked shortlist, stated reasons, and observation-dated evidence
          drawn from CQC&apos;s published record. The two launch products are one-off pieces
          of work. Continuing products remain closed.
        </p>
      </header>

      <Suspense fallback={null}>
        <RetainedPlanFocus />
      </Suspense>

      <section className="space-y-6" aria-label="CareGist products">
        {PRICING_LADDER.map((tier) => {
          const isFree = tier.tier === "Free Directory";

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
                  checkoutEnabled={checkoutEnabled}
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
          CareGist does not compete on record count or sell paid listing rank, speculative
          vacancy claims, predictive scores, or unsupported movement claims. The launch
          products explain which accounts or market changes deserve review and show the
          observation-dated evidence behind them.
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
