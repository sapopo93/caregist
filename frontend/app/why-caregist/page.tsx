import type { Metadata } from "next";
import Link from "next/link";

import { CQC_INDEPENDENCE_LINE } from "@/lib/caregist-config";

export const metadata: Metadata = {
  title: "Why CareGist | Evidence-linked CQC Signal Intelligence",
  description:
    "CareGist helps compliance and quality-improvement teams turn verified CQC changes into traceable, repeatable work.",
};

const DIFFERENCES = [
  {
    title: "Changes, not another provider database",
    body: "Radar starts with two decision-relevant events: a new CQC registration and a published rating change. The free directory remains available for discovery and checking.",
  },
  {
    title: "Evidence stays attached",
    body: "Stable CQC location IDs, source URLs, observation timestamps, entity level, and snapshot checksums make each event traceable to the approved source.",
  },
  {
    title: "Safe when interpretation is unavailable",
    body: "A verified raw event can still be delivered when an explanation does not pass the evidence gate. CareGist does not fill missing facts with a prediction.",
  },
  {
    title: "A workflow your team can repeat",
    body: "Regional and National Radar combine saved views, explicit provider lists, team actions, outcome feedback, and bounded event history without bundling an API into human-workflow plans.",
  },
];

const BOUNDARIES = [
  "No predictive provider score, vacancy claim, or guaranteed opportunity label",
  "No paid listing rank or sponsored provider placement",
  "No static dataset or commodity regional data pack",
  "No provider-group conclusion from a location-level event",
  "No automatic narrative unless the factual evidence gate passes",
  "No claim that CareGist can detect a change before CQC publishes it",
];

export default function WhyCareGistPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <header className="mb-12 max-w-4xl">
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-clay">
          Proof before promise
        </p>
        <h1 className="mb-5 text-4xl font-extrabold leading-tight text-bark md:text-5xl">
          CQC signal intelligence built for a decision—not for selling rows
        </h1>
        <p className="max-w-3xl text-lg leading-8 text-dusk" style={{ fontFamily: "Lora" }}>
          Compliance and quality-improvement teams already have access to public CQC
          records. CareGist&apos;s job is to preserve what changed, show the evidence, and
          make the next human action easier to prioritise and audit.
        </p>
      </header>

      <section className="mb-12 grid gap-5 md:grid-cols-2" aria-label="CareGist differences">
        {DIFFERENCES.map((item) => (
          <article key={item.title} className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
            <h2 className="text-xl font-bold text-bark">{item.title}</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">{item.body}</p>
          </article>
        ))}
      </section>

      <section className="mb-12 rounded-xl border border-stone bg-parchment p-7">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-clay">Commercial focus</p>
        <h2 className="mt-3 text-2xl font-bold text-bark">Why the first customer is a compliance firm</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-dusk">
          A rating change or registration can create immediate review, remediation, or
          business-development work. One qualified engagement can repay a Radar subscription,
          while the linked evidence lets a consultant explain exactly why the signal deserved
          attention. This is a narrower and more defensible promise than generic lead generation.
        </p>
      </section>

      <section className="mb-12 grid gap-7 md:grid-cols-[1.15fr_0.85fr]">
        <div>
          <h2 className="text-2xl font-bold text-bark">What CareGist deliberately does not claim</h2>
          <ul className="mt-5 space-y-3">
            {BOUNDARIES.map((boundary) => (
              <li key={boundary} className="flex gap-3 text-sm leading-6 text-charcoal">
                <span aria-hidden="true" className="text-moss">✓</span>
                <span>{boundary}</span>
              </li>
            ))}
          </ul>
        </div>
        <aside className="rounded-xl bg-charcoal p-6 text-cream">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-amber">Source boundary</p>
          <p className="mt-4 text-sm leading-6 text-stone">
            CQC controls publication and may delay, correct, remove, or republish information.
            CareGist publishes separate source and observation timestamps and exposes its current
            source status before a customer relies on a delivery target.
          </p>
          <Link href="/data-status" className="mt-5 inline-flex text-sm font-semibold text-amber underline">
            Review current data status
          </Link>
        </aside>
      </section>

      <section className="rounded-xl border border-moss/30 bg-moss/10 p-7">
        <h2 className="text-2xl font-bold text-bark">Independent and traceable</h2>
        <p className="mt-3 text-sm leading-6 text-charcoal">
          Contains public sector information licensed under the Open Government Licence
          v3.0. {CQC_INDEPENDENCE_LINE}
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/pricing" className="rounded-lg bg-clay px-5 py-3 text-sm font-semibold text-white hover:bg-bark">
            Compare Radar plans
          </Link>
          <Link href="/search" className="rounded-lg border border-clay px-5 py-3 text-sm font-semibold text-clay hover:bg-cream">
            Search the free directory
          </Link>
        </div>
      </section>
    </main>
  );
}
