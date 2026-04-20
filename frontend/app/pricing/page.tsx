import Link from "next/link";
import type { Metadata } from "next";

import PricingCTA from "@/components/PricingCTA";
import ProviderListingCTA from "@/components/ProviderListingCTA";
import TrackedLink from "@/components/TrackedLink";
import {
  CQC_INDEPENDENCE_LINE,
  LAUNCH_PRICING,
  NEW_REGISTRATION_MONTHLY_AVG,
  NEW_REGISTRATION_MONTHLY_AVG_CAVEAT,
  NEW_REGISTRATION_SOURCE_LINE,
  PLAN_NEXT_STEP,
  PRICING_LADDER,
  PROVIDER_TIERS,
} from "@/lib/caregist-config";

export const metadata: Metadata = {
  title: "CareGist Pricing | New Provider Intelligence, Alerts, Data & Listings",
  description: "Choose CareGist plans for new-provider alerts, data exports, API workflows, and provider visibility.",
};

const PLAN_BADGES: Record<string, string> = {
  Free: "Entry",
  "Alerts Pro": "Monitoring only",
  "Data Starter": "Core intelligence",
  "Data Pro": "Recommended for teams",
  "Data Business": "CRM and operations",
};

const UPGRADE_BOX_TITLE: Record<string, string> = {
  Enterprise: "Talk to us",
};

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Pricing for new-provider intelligence and provider visibility</h1>
        <p className="text-dusk text-lg mb-6" style={{ fontFamily: "Lora" }}>
          CareGist tracked an average of {NEW_REGISTRATION_MONTHLY_AVG} newly registered CQC providers per
          month from January to March 2026. Choose plans for new-provider intelligence on the demand side,
          or provider visibility on the supply side.
        </p>
        <div className="inline-flex rounded-lg border border-stone overflow-hidden text-sm font-medium">
          <a href="#data-plans" className="px-5 py-2 bg-bark text-cream">New-provider intelligence</a>
          <a href="#provider-plans" className="px-5 py-2 bg-cream text-bark hover:bg-parchment transition-colors">Provider visibility</a>
        </div>
      </div>

      <div id="data-plans" className="scroll-mt-8" />

      <div className="mb-8">
        <h2 className="text-2xl font-extrabold text-bark mb-2">New-provider intelligence plans</h2>
        <p className="text-sm text-dusk leading-6 max-w-3xl" style={{ fontFamily: "Lora" }}>
          Use CareGist to find newly registered CQC providers, monitor registration movement, build lead
          lists, and export opportunities for sales workflows.
        </p>
      </div>

      <div className="bg-bark rounded-xl p-6 mb-10">
        <p className="text-amber font-mono text-xs uppercase tracking-wider mb-4">
          Launch pricing
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {LAUNCH_PRICING.map((tier) => (
            <div key={tier.tier} className="flex flex-col">
              <span className="font-mono text-sm font-bold" style={{ color: tier.color }}>
                {tier.tier}
              </span>
              <span className="font-mono text-sm text-cream">{tier.price}</span>
            </div>
          ))}
        </div>
        <p className="font-mono text-xs text-dusk mt-4 pt-4 border-t border-white/10">
          Free is basic provider lookup and limited evaluation. Alerts Pro is for fresh new-provider
          alerts without heavy exports. Data Starter, Data Pro, and Data Business are the core
          new-provider intelligence plans for recurring feeds, saved filters, weekly digests, CRM
          exports, API access, and webhooks.
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
                  {PLAN_BADGES[tier.tier] && (
                    <span className={`font-mono text-[10px] px-2 py-0.5 rounded ${tier.recommended ? "bg-amber text-bark font-bold" : "bg-moss/15 text-moss"}`}>
                      {PLAN_BADGES[tier.tier]}
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

            {tier.limit && (
              <p className="font-mono text-xs text-dusk italic mb-3">{tier.limit}</p>
            )}
            {tier.pricingLogic && <p className="text-sm text-dusk mb-4">{tier.pricingLogic}</p>}
            <div className="mb-4 rounded-lg bg-parchment border border-stone px-4 py-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-dusk mb-1">
                {UPGRADE_BOX_TITLE[tier.tier] || "Why upgrade next"}
              </p>
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
        <div className="mb-8">
          <h2 className="text-2xl font-extrabold text-bark mb-2">Provider visibility plans</h2>
          <p className="text-sm text-dusk leading-6 max-w-3xl" style={{ fontFamily: "Lora" }}>
            Provider visibility plans are for care providers that want to improve how they appear to
            families, partners, and local-market searches.
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

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {PROVIDER_TIERS.map((tier, i) => (
            <div
              key={tier.tier}
              className={`bg-cream border rounded-xl p-6 flex flex-col ${i === 0 ? "border-2" : "border"}`}
              style={{ borderColor: i === 0 ? tier.color : undefined }}
            >
              {i === 1 && (
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
              {tier.tier === "claimed" ? (
                <Link
                  href="/search"
                  className="block text-center py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
                  style={{ background: tier.color }}
                >
                  Claim free
                </Link>
              ) : tier.tier === "enterprise" ? (
                <Link
                  href="mailto:enterprise@caregist.co.uk?subject=Multi-location+listing"
                  className="block text-center py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
                  style={{ background: tier.color }}
                >
                  Contact sales
                </Link>
              ) : (
                <ProviderListingCTA tier={tier.tier} color={tier.color} />
              )}
            </div>
          ))}
        </div>
        <p className="text-center text-xs text-dusk mt-4">All prices exclude VAT · Provider visibility plans are separate from new-provider intelligence plans · Claim your listing first at no cost</p>
      </div>

      <div className="text-center mt-10">
        <p className="text-bark font-semibold mb-2">Need a custom plan?</p>
        <p className="text-sm text-dusk">
          Enterprise paths cover large teams, commissioners, data buyers, multi-site groups, and custom integrations.{" "}
          <TrackedLink href="mailto:enterprise@caregist.co.uk" eventType="enterprise_contact_click" eventSource="pricing_footer">
            <span className="text-clay underline">Contact sales</span>
          </TrackedLink>
        </p>
      </div>

      <div className="text-center mt-6 text-xs text-dusk space-y-1">
        <p>All prices exclude VAT. Cancel anytime.</p>
        <p>{NEW_REGISTRATION_MONTHLY_AVG_CAVEAT}</p>
        <p>{NEW_REGISTRATION_SOURCE_LINE} {CQC_INDEPENDENCE_LINE}</p>
      </div>
    </div>
  );
}
