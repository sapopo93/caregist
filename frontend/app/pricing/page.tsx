import Link from "next/link";
import type { Metadata } from "next";

import PricingCTA from "@/components/PricingCTA";
import TrackedLink from "@/components/TrackedLink";
import { LAUNCH_PRICING, PLAN_NEXT_STEP, PRICING_LADDER, PROVIDER_TIERS } from "@/lib/caregist-config";

export const metadata: Metadata = {
  title: "Pricing — CareGist",
  description: "Launch pricing for CareGist's new registration feed: Starter £39, Pro £99, Business £399, and Enterprise contact sales.",
};

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Pricing for operational care-provider data</h1>
        <p className="text-dusk text-lg mb-6" style={{ fontFamily: "Lora" }}>
          CareGist launch v1 is newly registered UK care providers delivered as a filtered recurring intelligence feed. Provider claiming remains a secondary product line.
        </p>
        <div className="inline-flex rounded-lg border border-stone overflow-hidden text-sm font-medium">
          <a href="#data-plans" className="px-5 py-2 bg-bark text-cream">Data intelligence plans</a>
          <a href="#provider-plans" className="px-5 py-2 bg-cream text-bark hover:bg-parchment transition-colors">Provider listings</a>
        </div>
      </div>

      <div id="data-plans" className="scroll-mt-8" />

      <div className="bg-bark rounded-xl p-6 mb-10">
        <p className="text-amber font-mono text-xs uppercase tracking-wider mb-4">
          Launch pricing
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {LAUNCH_PRICING.filter((tier) => tier.tier !== "Free").map((tier) => (
            <div key={tier.tier} className="flex flex-col">
              <span className="font-mono text-sm font-bold" style={{ color: tier.color }}>
                {tier.tier}
              </span>
              <span className="font-mono text-sm text-cream">{tier.price}</span>
            </div>
          ))}
        </div>
        <p className="font-mono text-xs text-dusk mt-4 pt-4 border-t border-white/10">
          CQC provides the raw regulatory feed. CareGist makes it usable through a trusted event ledger, dashboard feed, exports, weekly digest, and API delivery.
        </p>
      </div>

      <div className="space-y-6">
        {PRICING_LADDER.map((tier, i) => (
          <div
            key={tier.tier}
            className={`bg-cream border rounded-xl p-6 ${tier.recommended ? "border-2 border-clay shadow-lg ring-2 ring-amber/20" : "border-stone"}`}
            style={{ borderLeftWidth: 4, borderLeftColor: tier.color }}
          >
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h2 className="text-xl font-bold text-bark">{tier.tier}</h2>
                  {i === 0 && (
                    <span className="font-mono text-[10px] bg-moss/15 text-moss px-2 py-0.5 rounded">
                      ENTRY
                    </span>
                  )}
                  {tier.recommended && (
                    <span className="font-mono text-[10px] bg-amber text-bark px-2 py-0.5 rounded font-bold">
                      RECOMMENDED FOR SMALL-TEAM PRODUCTION
                    </span>
                  )}
                </div>
                <p className="font-mono text-xs text-dusk">{tier.forWho}</p>
              </div>
              <div className="md:text-right">
                <p className="text-2xl font-bold" style={{ color: tier.color }}>
                  {tier.price}
                </p>
                <p className="font-mono text-xs text-dusk mt-1">{tier.priceNote}</p>
              </div>
            </div>

            <ul className="space-y-1.5 mb-4">
              {tier.includes.map((inc) => (
                <li key={inc} className="font-mono text-sm text-charcoal">
                  <span className="text-moss">&#10003;</span> {inc}
                </li>
              ))}
            </ul>

            <p className="font-mono text-xs text-dusk italic mb-3">{tier.limit}</p>
            <p className="text-sm text-dusk mb-4">{tier.pricingLogic}</p>
            <div className="mb-4 rounded-lg bg-parchment border border-stone px-4 py-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-dusk mb-1">Why upgrade next</p>
              <p className="text-sm text-bark">{PLAN_NEXT_STEP[tier.tier.toLowerCase()]}</p>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center gap-4 pt-4 border-t border-stone">
              {tier.tier === "Enterprise" ? (
                <TrackedLink
                  href="mailto:enterprise@caregist.co.uk?subject=Enterprise+enquiry"
                  eventType="enterprise_contact_click"
                  eventSource="pricing_enterprise_card"
                  className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
                >
                  Contact sales
                </TrackedLink>
              ) : (
                <PricingCTA tier={tier.tier} isFreeTier={i === 0} />
              )}
            </div>
          </div>
        ))}
      </div>

      <div id="provider-plans" className="scroll-mt-8 mt-16">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-2">Provider listings</h2>
          <p className="text-dusk" style={{ fontFamily: "Lora" }}>
            Secondary product line for providers that want to enrich public profiles after claiming.
          </p>
          <p className="text-sm text-dusk mt-2">
            First,{" "}
            <Link href="/search" className="text-clay underline">find your provider page</Link>
            {" "}and claim it free.
          </p>
        </div>

        <div className="bg-moss/10 border border-moss/30 rounded-xl p-5 mb-6 flex items-start gap-4">
          <span className="text-2xl mt-0.5">&#10003;</span>
          <div>
            <p className="font-bold text-moss mb-1">Claiming your listing is always free</p>
            <p className="text-sm text-dusk">
              Every claimed provider gets a verified badge and can publish an inspection response at no cost.
              Upgrade below for photos, descriptions, virtual tours, and sponsored placement.
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {PROVIDER_TIERS.filter((tier) => tier.tier !== "claimed").map((tier, i) => (
            <div
              key={tier.tier}
              className={`bg-cream border rounded-xl p-6 flex flex-col ${i === 0 ? "border-2" : "border"}`}
              style={{ borderColor: i === 0 ? tier.color : undefined }}
            >
              {i === 0 && (
                <span className="text-xs font-mono font-bold uppercase mb-3 self-start px-2 py-0.5 rounded" style={{ background: tier.color + "22", color: tier.color }}>
                  Most popular
                </span>
              )}
              <h3 className="text-lg font-bold text-bark mb-1">{tier.label}</h3>
              <p className="text-2xl font-bold mb-1" style={{ color: tier.color }}>{tier.price}</p>
              {tier.priceAnnual && (
                <p className="text-xs text-dusk mb-4">or £{tier.priceAnnual}/yr (save {Math.round((1 - tier.priceAnnual / (tier.priceMonthly * 12)) * 100)}%)</p>
              )}
              <ul className="space-y-1.5 mb-6 flex-1">
                {tier.includes.map((inc) => (
                  <li key={inc} className="text-sm text-charcoal">
                    <span className="text-moss mr-1">&#10003;</span>{inc}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-dusk italic mb-4">{tier.limit}</p>
              <Link
                href="/search?intent=claim"
                className="block text-center py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
                style={{ background: tier.color }}
              >
                Get started
              </Link>
            </div>
          ))}
        </div>
        <p className="text-center text-xs text-dusk mt-4">All prices exclude VAT · Cancel anytime · Claim your listing first at no cost</p>
      </div>

      <div className="text-center mt-10">
        <p className="text-bark font-semibold mb-2">Need a custom plan?</p>
        <p className="text-sm text-dusk">
          Enterprise paths cover procurement, commissioner packaging, custom limits, and large-group support.{" "}
          <TrackedLink href="mailto:enterprise@caregist.co.uk" eventType="enterprise_contact_click" eventSource="pricing_footer">
            <span className="text-clay underline">Contact sales</span>
          </TrackedLink>
        </p>
      </div>

      <div className="text-center mt-6 text-xs text-dusk">
        All prices exclude VAT. CQC data attribution included. Data refreshed daily. Cancel anytime.
      </div>
    </div>
  );
}
