import Link from "next/link";
import { PRICING_LADDER, ADD_ONS, LAUNCH_PRICING } from "@/lib/caregist-config";

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Simple, transparent pricing</h1>
        <p className="text-dusk text-lg" style={{ fontFamily: "Lora" }}>
          Access 55,818 CQC-rated care providers. Start free, upgrade when you need more.
        </p>
      </div>

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
          Benchmark: comparable directory listings range £80–£165 + VAT/mo per location
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
                  {i === PRICING_LADDER.length - 1 && (
                    <span className="font-mono text-[10px] bg-amber/15 text-amber px-2 py-0.5 rounded">
                      TOP ARPU
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
              <Link
                href={i === 0 ? "/signup" : `/signup?plan=${tier.tier.toLowerCase().replace(/\s+/g, "-")}`}
                className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
              >
                {i === 0 ? "Get Started Free" : "Get Started"}
              </Link>
              <p className="font-mono text-xs text-dusk">{tier.pricingLogic}</p>
            </div>
          </div>
        ))}
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
