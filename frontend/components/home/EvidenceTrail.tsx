import Link from "next/link";

const STEPS = [
  {
    n: "01",
    title: "CQC publishes",
    body: "A registration, rating or closure appears in CQC's public record against a stable location ID.",
    tag: "Source URL kept",
  },
  {
    n: "02",
    title: "We observe it",
    body: "The change is seen, time-stamped and tied to the exact location, not a mutable provider row.",
    tag: "Observation time kept",
  },
  {
    n: "03",
    title: "It becomes an event",
    body: "Only events that pass the evidence gate ship. If an explanation cannot be evidenced, the raw event still ships and the gap is left empty.",
    tag: "No speculation",
  },
  {
    n: "04",
    title: "You check it",
    body: "Every item links back to the official CQC record, so you confirm before you act.",
    tag: "One click to source",
  },
];

export default function EvidenceTrail() {
  return (
    <div>
      <ol className="relative grid gap-4 md:grid-cols-4">
        <span aria-hidden className="absolute left-0 right-0 top-[1.15rem] hidden h-px bg-clay/40 md:block" />
        {STEPS.map((step) => (
          <li key={step.n} className="relative">
            <span className="relative z-10 inline-flex h-9 items-center rounded-full border border-clay/50 bg-parchment px-3 font-mono text-xs font-semibold text-clay">
              {step.n}
            </span>
            <h3 className="mt-4 text-xl font-bold text-bark">{step.title}</h3>
            <p className="mt-2 text-sm leading-6 text-dusk">{step.body}</p>
            <p className="mt-3 inline-block rounded bg-cream px-2 py-1 font-mono text-[0.7rem] uppercase tracking-wide text-bark ring-1 ring-stone">
              {step.tag}
            </p>
          </li>
        ))}
      </ol>

      <div className="mt-8 overflow-x-auto rounded-lg border border-stone bg-charcoal p-4 font-mono text-xs leading-6 text-stone">
        <p className="mb-1 text-[0.7rem] uppercase tracking-widest text-amber">Shape of one signal (format only, not a real record)</p>
        <p><span className="text-sage">event_type</span>: rating_change</p>
        <p><span className="text-sage">location_id</span>: &lt;CQC location ID&gt;</p>
        <p><span className="text-sage">observed_at</span>: &lt;UTC timestamp&gt;</p>
        <p><span className="text-sage">source_url</span>: &lt;link to the official CQC record&gt;</p>
      </div>

      <Link href="/data-status" className="mt-5 inline-flex text-sm font-semibold text-clay underline underline-offset-4">
        Review Data Status and the reconciled source date
      </Link>
    </div>
  );
}
