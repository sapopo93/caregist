import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Territory Opportunity Brief | CareGist",
  description:
    "A buyer-specific shortlist of 25 to 50 care organisations, a CRM-ready dataset and a concise executive brief for £795.",
};

const deliverables = [
  "A buyer-specific shortlist of 25 to 50 care organisations in an agreed England territory.",
  "A CRM-ready CSV or Excel dataset covering the agreed shortlist and the fields available from the checked public sources.",
  "A three to five page executive brief explaining the agreed selection criteria and the factual reasons each organisation was included.",
  "Source links and observation dates for the public CQC information used in the brief.",
];

const boundaries = [
  "This is research support for organisations that sell to, advise or invest in UK care. It is not a list of providers to contact for care.",
  "The brief does not claim buying intent, vacancies, budget, contract timing or a commercial outcome.",
  "CareGist is independent of CQC. Customers should check the linked official sources before making a regulated, clinical, employment, credit or other high-impact decision.",
];

export default function TerritoryOpportunityBriefPage() {
  return (
    <div className="bg-parchment text-charcoal">
      <section className="border-b border-stone bg-bark px-6 py-16 text-cream md:py-24">
        <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div>
            <p className="mb-5 text-xs font-semibold uppercase tracking-[0.22em] text-amber">
              One-off research product
            </p>
            <h1 className="max-w-3xl font-[family-name:var(--font-playfair-display)] text-5xl font-bold leading-[1.05] tracking-tight md:text-6xl">
              Know which care organisations to research first.
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-stone">
              CareGist turns an agreed territory and buyer brief into a focused, evidence-linked starting list for your sales, advisory or investment research.
            </p>
          </div>
          <div className="rounded-2xl border border-amber/35 bg-white/5 p-7">
            <p className="text-sm text-stone">Territory Opportunity Brief</p>
            <p className="mt-2 font-[family-name:var(--font-playfair-display)] text-5xl font-bold text-amber">£795</p>
            <p className="mt-2 text-sm text-stone">CareGist is not currently VAT-registered. No VAT is charged.</p>
            <a
              href="mailto:enterprise@caregist.co.uk?subject=CareGist%20Territory%20Opportunity%20Brief"
              className="mt-7 inline-flex w-full items-center justify-center rounded-xl bg-amber px-5 py-3 text-sm font-semibold text-charcoal transition hover:bg-cream focus:outline-none focus:ring-2 focus:ring-cream focus:ring-offset-2 focus:ring-offset-bark"
            >
              Start a scope conversation
            </a>
            <p className="mt-3 text-xs leading-5 text-stone">We confirm your territory, buyer criteria and source readiness before accepting payment.</p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16 md:py-20">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-clay">Who it is for</p>
            <h2 className="mt-3 font-[family-name:var(--font-playfair-display)] text-4xl font-bold leading-tight text-bark">
              Teams selling into, advising or investing in UK care.
            </h2>
          </div>
          <p className="max-w-2xl text-lg leading-8 text-dusk">
            It is designed for compliance advisers, recruitment and staffing firms, software, insurance and other suppliers. It gives your team a defined list to research, rather than a broad directory to work through.
          </p>
        </div>
      </section>

      <section className="border-y border-stone bg-cream px-6 py-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-clay">What you receive</p>
          <div className="mt-8 grid gap-5 md:grid-cols-2">
            {deliverables.map((item, index) => (
              <article key={item} className="rounded-2xl border border-stone bg-white p-7 shadow-sm">
                <p className="text-sm font-semibold text-clay">0{index + 1}</p>
                <p className="mt-5 text-lg leading-7 text-charcoal">{item}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16 md:py-20">
        <div className="grid gap-10 lg:grid-cols-[1fr_1fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-clay">Delivery</p>
            <h2 className="mt-3 font-[family-name:var(--font-playfair-display)] text-4xl font-bold leading-tight text-bark">
              A clear scope before a useful shortlist.
            </h2>
            <ol className="mt-7 space-y-5 border-l border-stone pl-6 text-dusk">
              <li><strong className="text-charcoal">1. Agree the brief.</strong> You confirm the territory, buyer type and the criteria your team will use.</li>
              <li><strong className="text-charcoal">2. Confirm the source check.</strong> We confirm the relevant public-source path is available for the agreed scope.</li>
              <li><strong className="text-charcoal">3. Receive the pack.</strong> The delivery target is three working days after both checks are complete.</li>
            </ol>
          </div>
          <aside className="rounded-2xl bg-bark p-8 text-cream">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber">Dated example</p>
            <p className="mt-5 text-xl leading-8">
              A Birmingham and Solihull example contains 353 locations, 329 provider organisations and a 25-organisation shortlist.
            </p>
            <p className="mt-5 text-sm leading-6 text-stone">
              It shows the format and evidence structure. Its dated source material is not a claim about live conditions in another territory.
            </p>
          </aside>
        </div>
      </section>

      <section className="border-t border-stone bg-cream px-6 py-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-clay">What the brief does not say</p>
          <ul className="mt-7 grid gap-4 md:grid-cols-3">
            {boundaries.map((item) => (
              <li key={item} className="rounded-xl border border-stone bg-parchment p-6 leading-7 text-dusk">{item}</li>
            ))}
          </ul>
          <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
            <Link href="/terms" className="font-semibold text-clay underline underline-offset-4 hover:text-bark">Business terms</Link>
            <Link href="/privacy" className="font-semibold text-clay underline underline-offset-4 hover:text-bark">Privacy policy</Link>
            <a href="mailto:enterprise@caregist.co.uk?subject=CareGist%20Territory%20Opportunity%20Brief" className="font-semibold text-clay underline underline-offset-4 hover:text-bark">Ask about your territory</a>
          </div>
        </div>
      </section>
    </div>
  );
}
