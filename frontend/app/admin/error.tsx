"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function AdminError({
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
      <h1 className="text-3xl font-bold text-bark mb-4">Admin panel error</h1>
      <p className="text-dusk mb-8">
        The admin view failed to render. The error has been logged — please try again.
      </p>
      <button
        onClick={reset}
        className="px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
