import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Lead Lists | CareGist",
  description:
    "Request a filtered CareGist lead list by region, service type, and rating, then move into dataset packs or recurring intelligence plans when the workflow scales.",
};

const EXAMPLES = [
  "Homecare agencies in London rated Good or Outstanding",
  "Care homes in the North West with Requires Improvement ratings",
  "Providers in one local authority for outreach, benchmarking, or CRM upload",
] as const;

const NEXT_STEPS = [
  {
    title: "Start with search",
    body:
      "Use the public directory to refine the segment you want before deciding whether a one-off lead list or a recurring plan is the right fit.",
    href: "/search",
    cta: "Open search",
  },
  {
    title: "Compare pricing",
    body:
      "If you need more than a one-off list, move into the subscription and dataset products that support recurring monitoring and larger exports.",
    href: "/pricing",
    cta: "See pricing",
  },
  {
    title: "Need workflow automation?",
    body:
      "If this segment needs to flow into CRM or internal operations, the API and webhook stack is the better long-term route than manual list fulfilment.",
    href: "/api",
    cta: "Explore API",
  },
] as const;

export default function LeadListPage() {
  return (
    <div className="bg-parchment px-6 py-14">
      <div className="mx-auto max-w-5xl">
        <section className="rounded-[2rem] border border-stone bg-[linear-gradient(135deg,#2b2520_0%,#4f3b2d_55%,#6b4c35_100%)] px-8 py-10 text-cream shadow-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber">Lead lists</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-extrabold leading-tight md:text-5xl">
            Request a filtered provider list without buying the full dataset.
          </h1>
          <p className="mt-5 max-w-3xl text-base leading-7 text-stone">
            CareGist lead lists are for buyers who know the segment they want now: region, service type,
            and rating slices that can be used for outreach, research, market mapping, or CRM upload.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="mailto:hello@caregist.co.uk?subject=CareGist%20lead%20list%20request"
              className="rounded-full bg-amber px-5 py-3 text-sm font-semibold text-charcoal transition hover:bg-cream"
            >
              Request by email
            </a>
            <Link
              href="/pricing"
              className="rounded-full border border-cream/20 px-5 py-3 text-sm font-semibold text-cream transition hover:bg-white/10"
            >
              Compare plans
            </Link>
          </div>
        </section>

        <section className="mt-10 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">What to request</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">Examples of good lead-list briefs</h2>
            <ul className="mt-5 space-y-3 text-sm leading-6 text-dusk">
              {EXAMPLES.map((example) => (
                <li key={example} className="rounded-2xl border border-stone bg-parchment px-4 py-3">
                  {example}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Best fit</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">When this product makes sense</h2>
            <p className="mt-4 text-sm leading-6 text-dusk">
              Choose a lead list when the job is immediate and scoped. If you need repeated monitoring,
              scheduled exports, or integrations, move up to the subscription or API products instead.
            </p>
          </div>
        </section>

        <section className="mt-10">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Next step options</p>
          <div className="mt-4 grid gap-6 md:grid-cols-3">
            {NEXT_STEPS.map((step) => (
              <div key={step.title} className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
                <h3 className="text-2xl font-bold text-bark">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-dusk">{step.body}</p>
                <Link href={step.href} className="mt-5 inline-flex text-sm font-semibold text-clay hover:text-bark">
                  {step.cta}
                </Link>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
