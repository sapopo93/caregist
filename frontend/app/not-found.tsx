import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20 text-center">
      <h1 className="text-4xl font-bold text-bark">Page not found</h1>
      <p className="mt-4 text-dusk">
        The page you requested is not available. Go back to the directory search or request a filtered lead list.
      </p>
      <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <Link
          href="/search"
          className="rounded-full bg-clay px-6 py-3 text-sm font-semibold text-white hover:bg-bark"
        >
          Search providers
        </Link>
        <Link
          href="/lead-list"
          className="rounded-full border border-stone px-6 py-3 text-sm font-semibold text-bark hover:bg-cream"
        >
          Get a lead list
        </Link>
      </div>
    </div>
  );
}
