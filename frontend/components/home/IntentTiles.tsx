import Link from "next/link";

const INTENTS = [
  {
    kicker: "For suppliers and advisers",
    title: "Size up a territory",
    body: "See how many locations match your region and provider group. Free, no account.",
    href: "/pricing/territory",
    cta: "Check your territory",
  },
  {
    kicker: "For teams watching a region",
    title: "Follow what changes",
    body: "A weekly digest of new registrations, rating changes and closures for one England region.",
    href: "/pricing/weekly-digest/enquiry",
    cta: "Ask about the Weekly Digest",
  },
  {
    kicker: "Checking a provider",
    title: "Look one up",
    body: "Search any CQC-registered location by name, town or postcode and check the official record.",
    href: "/search",
    cta: "Search the directory",
  },
  {
    kicker: "Finding care for someone",
    title: "Find care near a postcode",
    body: "Browse CQC-rated providers within a radius of a postcode. Always confirm details with the provider.",
    href: "/find-care",
    cta: "Find care nearby",
  },
];

export default function IntentTiles() {
  return (
    <section aria-label="What do you want to do?" className="mx-auto mt-10 max-w-6xl">
      <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-clay">What would you like to do?</h2>
      <ul className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {INTENTS.map((intent) => (
          <li key={intent.href}>
            <Link
              href={intent.href}
              className="group flex h-full flex-col justify-between rounded-xl border border-stone bg-cream p-5 transition hover:-translate-y-0.5 hover:border-clay hover:shadow-md"
            >
              <span>
                <span className="block font-mono text-[0.68rem] uppercase tracking-[0.16em] text-dusk">{intent.kicker}</span>
                <span className="mt-2 block font-[family-name:var(--font-playfair-display)] text-xl font-bold leading-snug text-bark">
                  {intent.title}
                </span>
                <span className="mt-2 block text-sm leading-6 text-dusk">{intent.body}</span>
              </span>
              <span className="mt-4 text-sm font-semibold text-clay group-hover:underline">{intent.cta} →</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
