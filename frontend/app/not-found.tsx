import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-20 text-center">
      <h1 className="text-4xl font-bold text-bark mb-4">Page not found</h1>
      <p className="text-dusk mb-8">
        The page you&apos;re looking for doesn&apos;t exist or has moved. The fastest way back into CareGist is usually the
        data explorer, pricing, or the homepage.
      </p>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <Link
          href="/"
          className="inline-block px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
        >
          Back to homepage
        </Link>
        <Link
          href="/search"
          className="inline-block px-6 py-3 border border-stone text-dusk rounded-lg font-medium hover:bg-cream transition-colors"
        >
          Open data explorer
        </Link>
        <Link
          href="/pricing"
          className="inline-block px-6 py-3 border border-stone text-dusk rounded-lg font-medium hover:bg-cream transition-colors"
        >
          See pricing
        </Link>
      </div>
    </div>
  );
}
