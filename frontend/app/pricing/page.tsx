import Link from "next/link";
import { PRICING_LADDER, ADD_ONS, LAUNCH_PRICING, PROVIDER_TIERS } from "@/lib/caregist-config";
import PricingCTA from "@/components/PricingCTA";

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Simple, transparent pricing</h1>
        <p className="text-dusk text-lg mb-6" style={{ fontFamily: "Lora" }}>
          Two product lines — data access for professionals, and enhanced listings for providers.
        </p>
        <div className="inline-flex rounded-lg border border-stone overflow-hidden text-sm font-medium">
          <a href="#data-plans" className="px-5 py-2 bg-bark text-cream">Data &amp; API Plans</a>
          <a href="#provider-plans" className="px-5 py-2 bg-cream text-bark hover:bg-parchment transition-colors">Provider Listings</a>
        </div>
      </div>

      {/* Data Plans anchor */}
      <div id="data-plans" className="scroll-mt-8" />

      {/* Launch pricing summary */}
      <div className="bg-bark rounded-xl p-6 mb-10">
        <p className="text-amber font-mono text-xs uppercase tracking-wider mb-4">
          Launch pricing — start here
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {LAUNCH_PRICING.map((t) => (
            <div key={t.tier} className="flex flex-col">
              <span className="font-mono text-sm font-bold" style={{ color: t.color }}>
                {t.tier}
              </span>
              <span className="font-mono text-sm text-cream">{t.price}</span>
            </div>
          ))}
        </div>
        <p className="font-mono text-xs text-dusk mt-4 pt-4 border-t border-white/10">
          Benchmark: comparable provider directory listings £34–£69 + VAT/mo · market intelligence reports £950–£3,895/report
        </p>
      </div>

      {/* Pricing tiers */}
      <div className="space-y-6">
        {PRICING_LADDER.map((tier, i) => (
          <div
            key={tier.tier}
            className="bg-cream border border-stone rounded-xl p-6"
            style={{ borderLeftWidth: 4, borderLeftColor: tier.color }}
          >
            {/* Tier header */}
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
                    <span className="font-mono text-[10px] bg-amber/20 text-amber px-2 py-0.5 rounded">
                      RECOMMENDED
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

            {/* Variants */}
            {tier.variants && (
              <div
                className="rounded-lg p-4 mb-4"
                style={{ background: tier.color + "0a", border: `1px solid ${tier.color}22` }}
              >
                <div className="space-y-2">
                  {tier.variants.map((v) => (
                    <div key={v.name} className="flex justify-between items-start gap-4">
                      <div>
                        <span className="font-mono text-sm font-bold" style={{ color: tier.color }}>
                          {v.name}{" "}
                        </span>
                        <span className="font-mono text-xs text-dusk">{v.features}</span>
                      </div>
                      <span className="font-mono text-sm font-semibold text-charcoal whitespace-nowrap">
                        {v.price}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Includes */}
            <ul className="space-y-1.5 mb-4">
              {tier.includes.map((inc) => (
                <li key={inc} className="font-mono text-sm text-charcoal">
                  <span className="text-moss">&#10003;</span> {inc}
                </li>
              ))}
            </ul>

            {/* Limit */}
            <p className="font-mono text-xs text-dusk italic mb-4">{tier.limit}</p>

            {/* CTA */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-4 pt-4 border-t border-stone">
              {tier.tier === "Enterprise" ? (
                <a
                  href="mailto:enterprise@caregist.co.uk?subject=Enterprise+enquiry"
                  className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
                >
                  Contact us
                </a>
              ) : (
                <PricingCTA tier={tier.tier} isFreeTier={i === 0} />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Provider Listing Plans */}
      <div id="provider-plans" className="scroll-mt-8 mt-16">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-2">Provider Listings</h2>
          <p className="text-dusk" style={{ fontFamily: "Lora" }}>
            Claim your listing for free. Upgrade for photos, descriptions, and sponsored visibility.
          </p>
          <p className="text-sm text-dusk mt-2">
            First,{" "}
            <Link href="/search" className="text-clay underline">find your provider page</Link>
            {" "}and claim it free — then choose a plan below.
          </p>
        </div>

        {/* Free claim callout */}
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
          {PROVIDER_TIERS.filter((t) => t.tier !== "claimed").map((t, i) => (
            <div
              key={t.tier}
              className={`bg-cream border rounded-xl p-6 flex flex-col ${i === 0 ? "border-2" : "border"}`}
              style={{ borderColor: i === 0 ? t.color : undefined }}
            >
              {i === 0 && (
                <span className="text-xs font-mono font-bold uppercase mb-3 self-start px-2 py-0.5 rounded" style={{ background: t.color + "22", color: t.color }}>
                  Most popular
                </span>
              )}
              <h3 className="text-lg font-bold text-bark mb-1">{t.label}</h3>
              <p className="text-2xl font-bold mb-1" style={{ color: t.color }}>{t.price}</p>
              {t.priceAnnual && (
                <p className="text-xs text-dusk mb-4">or £{t.priceAnnual}/yr (save {Math.round((1 - t.priceAnnual / (t.priceMonthly * 12)) * 100)}%)</p>
              )}
              <ul className="space-y-1.5 mb-6 flex-1">
                {t.includes.map((inc) => (
                  <li key={inc} className="text-sm text-charcoal">
                    <span className="text-moss mr-1">&#10003;</span>{inc}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-dusk italic mb-4">{t.limit}</p>
              <a
                href="mailto:hello@caregist.co.uk?subject=Enhanced+listing+enquiry"
                className="block text-center py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
                style={{ background: t.color }}
              >
                Get started
              </a>
            </div>
          ))}
        </div>
        <p className="text-center text-xs text-dusk mt-4">All prices exclude VAT · Cancel anytime · Claim your listing first at no cost</p>
      </div>

      {/* Add-ons */}
      <div className="bg-bark rounded-xl p-6 mt-10 opacity-80">
        <div className="flex items-center gap-3 mb-4">
          <p className="text-amber font-mono text-xs uppercase tracking-wider">Add-ons</p>
          <span className="font-mono text-[10px] bg-amber/20 text-amber px-2 py-0.5 rounded">
            Coming soon
          </span>
        </div>
        <div className="space-y-3">
          {ADD_ONS.map((a) => (
            <div key={a.name} className="flex justify-between items-start gap-4">
              <div>
                <p className="font-mono text-sm font-semibold text-cream/60">{a.name}</p>
                <p className="font-mono text-xs text-white/25">{a.note}</p>
              </div>
              <span className="font-mono text-sm text-amber/60 font-bold whitespace-nowrap">
                {a.price}
              </span>
            </div>
          ))}
        </div>
        <p className="font-mono text-xs text-white/30 mt-4 pt-3 border-t border-white/10">
          These add-ons are coming soon. Register interest at{" "}
          <a href="mailto:hello@caregist.co.uk" className="text-amber/60 underline">
            hello@caregist.co.uk
          </a>
        </p>
      </div>

      {/* Footer */}
      <div className="text-center mt-10">
        <p className="text-bark font-semibold mb-2">Need a custom plan?</p>
        <p className="text-sm text-dusk">
          Enterprise API, white-label reports, and custom data feeds available.{" "}
          <a href="mailto:enterprise@caregist.co.uk" className="text-clay underline">
            Contact us
          </a>
        </p>
      </div>

      <div className="text-center mt-6 text-xs text-dusk">
        All prices exclude VAT. CQC data attribution included. Data refreshed daily. Cancel
        anytime.
      </div>
    </div>
  );
}
