import { PRICING_LADDER } from "@/lib/caregist-config";
import { pricingPlanCardId } from "@/lib/pricing-plan-path";

/** One-line "choose this if" per product. Prices are read from config, never typed here. */
const CHOOSE_IF: Record<string, { cadence: string; question: string }> = {
  "Weekly Digest": {
    cadence: "four weekly issues, one-off",
    question: "I want to see what moves in one region, week by week.",
  },
  "Territory Opportunity Brief": {
    cadence: "one brief, one-off",
    question: "I need to decide where to focus next, and which organisations to look at first.",
  },
  "Free Directory": {
    cadence: "always free",
    question: "I only need to look a provider up and check the official record.",
  },
};

export default function PricingGlance() {
  const tiers = [...PRICING_LADDER].sort((a, b) => {
    const rank = (t: string) => (t === "Weekly Digest" ? 0 : t === "Territory Opportunity Brief" ? 1 : 2);
    return rank(a.tier) - rank(b.tier);
  });

  return (
    <nav aria-label="Choose a product" className="mb-10 grid gap-px overflow-hidden rounded-2xl border border-stone bg-stone md:grid-cols-3">
      {tiers.map((tier) => {
        const copy = CHOOSE_IF[tier.tier];
        const id = pricingPlanCardId(tier.tier);
        return (
          <a
            key={tier.tier}
            href={id ? `/pricing#${id}` : "/pricing"}
            className={`group flex flex-col justify-between gap-6 p-6 transition ${
              tier.recommended ? "bg-bark text-cream" : "bg-cream hover:bg-white"
            }`}
          >
            <div>
              <p className={`font-mono text-[11px] uppercase tracking-[0.18em] ${tier.recommended ? "text-amber" : "text-clay"}`}>
                {tier.tier}
              </p>
              <p
                className={`mt-3 font-[family-name:var(--font-playfair-display)] text-5xl font-bold leading-none ${
                  tier.recommended ? "text-cream" : "text-bark"
                }`}
              >
                {tier.price}
              </p>
              {copy ? (
                <p className={`mt-2 text-xs ${tier.recommended ? "text-stone" : "text-dusk"}`}>{copy.cadence}</p>
              ) : null}
            </div>
            {copy ? (
              <p className={`text-sm leading-6 ${tier.recommended ? "text-cream" : "text-charcoal"}`}>
                <span className={tier.recommended ? "text-amber" : "text-clay"}>Choose this if: </span>
                {copy.question}
              </p>
            ) : null}
            <span className={`text-sm font-semibold underline underline-offset-4 ${tier.recommended ? "text-amber" : "text-clay"}`}>
              See what is included
            </span>
          </a>
        );
      })}
    </nav>
  );
}
