"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function Error({
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
    <div className="mx-auto max-w-2xl px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-clay">Something went wrong</p>
      <h1 className="mt-3 text-4xl font-extrabold leading-tight text-bark">We could not load this page.</h1>
      <p className="mt-4 text-dusk">
        This is usually temporary. Your searches and comparisons are not affected, and nothing was submitted or charged.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-lg bg-clay px-6 py-3 font-medium text-white transition-colors hover:bg-bark"
        >
          Try again
        </button>
        <a href="/" className="rounded-lg border border-clay px-6 py-3 font-medium text-clay transition-colors hover:bg-clay hover:text-white">
          Go to the homepage
        </a>
        <a href="/data-status" className="px-2 py-3 text-sm font-semibold text-clay underline underline-offset-4">
          Check data status
        </a>
      </div>
      <p className="mt-8 text-sm text-dusk">
        Still stuck? Email <a className="font-semibold text-clay underline" href="mailto:support@caregist.co.uk">support@caregist.co.uk</a>
        {error.digest ? (
          <>
            {" "}and quote reference <code className="rounded bg-parchment px-1.5 py-0.5 font-mono text-xs text-bark">{error.digest}</code>
          </>
        ) : null}
        .
      </p>
    </div>
  );
}
