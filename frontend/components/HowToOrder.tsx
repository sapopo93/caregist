import Link from "next/link";

const STEPS = [
  {
    n: "1",
    title: "Choose your scope",
    body: "For the Brief, run the free coverage check for your region and provider group. For the Weekly Digest, pick your England region.",
    link: { href: "/pricing/territory", label: "Run a free coverage check" },
  },
  {
    n: "2",
    title: "Email your enquiry",
    body: "We prepare the message for you. You send it from your own email, so nothing is submitted until you press send.",
  },
  {
    n: "3",
    title: "We confirm in writing",
    body: "CareGist checks source availability, then confirms scope and delivery dates in writing before any payment is requested.",
  },
];

export default function HowToOrder() {
  return (
    <section aria-label="How to order" className="mb-8 rounded-xl border border-stone bg-parchment p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-bold text-bark">How to order</h2>
        <p className="text-xs text-dusk">Online ordering is not available. Neither route places an order or takes payment by itself.</p>
      </div>
      <ol className="mt-4 grid gap-4 md:grid-cols-3">
        {STEPS.map((step, i) => (
          <li key={step.n} className="relative rounded-lg bg-cream p-4 ring-1 ring-stone">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-bark font-mono text-xs font-bold text-cream">
              {step.n}
            </span>
            <p className="mt-3 font-bold text-bark">{step.title}</p>
            <p className="mt-1 text-sm leading-6 text-dusk">{step.body}</p>
            {step.link ? (
              <Link href={step.link.href} className="mt-2 inline-block text-sm font-semibold text-clay underline underline-offset-4">
                {step.link.label} →
              </Link>
            ) : null}
            {i < STEPS.length - 1 ? (
              <span aria-hidden className="absolute -right-3 top-1/2 hidden -translate-y-1/2 text-xl text-clay md:block">›</span>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
