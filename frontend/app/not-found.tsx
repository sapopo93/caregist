import Link from "next/link";

import { DEFAULT_REGION_OPTIONS } from "@/lib/directory-constants";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-clay">Error 404</p>
      <h1 className="mt-3 text-5xl font-extrabold leading-tight text-bark md:text-6xl">
        That page is not on the register.
      </h1>
      <p className="mt-4 max-w-xl text-dusk">
        The address may be out of date. Look a provider up directly, or start from your region.
      </p>

      <form action="/search" method="get" role="search" className="mt-8 flex flex-col gap-3 sm:flex-row">
        <label htmlFor="nf-search" className="sr-only">Search care providers by name, town or postcode</label>
        <input
          id="nf-search"
          name="q"
          type="search"
          placeholder="Provider name, town or postcode"
          className="h-12 flex-1 rounded-xl border-2 border-stone bg-cream px-4 text-base text-charcoal focus:border-clay focus:outline-none"
        />
        <button type="submit" className="h-12 rounded-xl bg-clay px-6 text-sm font-semibold text-white hover:bg-bark">
          Search providers
        </button>
      </form>

      <p className="mt-10 font-mono text-xs uppercase tracking-[0.18em] text-dusk">Or start from a region</p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {DEFAULT_REGION_OPTIONS.map((region) => (
          <li key={region}>
            <Link
              href={`/search?region=${encodeURIComponent(region)}`}
              className="inline-flex rounded-full border border-stone bg-cream px-4 py-2 text-sm font-medium text-bark transition hover:border-clay hover:text-clay"
            >
              {region}
            </Link>
          </li>
        ))}
      </ul>

      <p className="mt-10 text-sm text-dusk">
        Looking for the products? <Link href="/pricing" className="font-semibold text-clay underline">See pricing</Link>.
      </p>
    </div>
  );
}
