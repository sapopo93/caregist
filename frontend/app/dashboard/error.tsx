"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function DashboardError({
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
      <h1 className="text-3xl font-bold text-bark mb-4">Your dashboard didn’t load</h1>
      <p className="text-dusk mb-8">
        Something went wrong loading your account data. Your data is safe — please try again.
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
