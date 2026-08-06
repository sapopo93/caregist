"use client";

import * as Sentry from "@sentry/nextjs";
import Link from "next/link";
import { useEffect } from "react";

export default function ProviderError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="max-w-2xl mx-auto px-6 py-20 text-center">
      <h1 className="text-3xl font-bold text-bark mb-4">This provider didn’t load</h1>
      <p className="text-dusk mb-8">
        We hit an unexpected error loading this care provider. Please try again, or browse the directory.
      </p>
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={reset}
          className="px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
        >
          Try again
        </button>
        <Link
          href="/search"
          className="px-6 py-3 border border-clay text-clay rounded-lg font-medium hover:bg-clay hover:text-white transition-colors"
        >
          Browse providers
        </Link>
      </div>
    </div>
  );
}
