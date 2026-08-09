"use client";

import { FormEvent, useState } from "react";

export default function FullDatasetCheckout({ enabled }: { enabled: boolean }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!enabled || loading) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/billing/dataset-checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok || !body.checkout_url) {
        throw new Error(body.detail || "Checkout is temporarily unavailable.");
      }
      window.location.assign(body.checkout_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Checkout is temporarily unavailable.");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
      <label htmlFor="dataset-email" className="block text-sm font-semibold text-bark mb-2">
        Delivery email
      </label>
      <input
        id="dataset-email"
        type="email"
        required
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        className="w-full rounded-lg border border-stone bg-white px-4 py-3 text-charcoal focus:border-clay focus:outline-none"
        placeholder="you@company.co.uk"
      />
      <button
        type="submit"
        disabled={!enabled || loading}
        className="mt-4 w-full rounded-lg bg-clay px-6 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Opening secure checkout…" : "Buy full dataset — £199"}
      </button>
      {!enabled && <p className="mt-3 text-sm text-dusk">Checkout is temporarily paused while the current export is prepared.</p>}
      {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
      <p className="mt-4 text-xs leading-5 text-dusk">
        Stripe will require your express consent to immediate digital delivery and acknowledgement
        that the cancellation right is lost once download access is provided. Review our{" "}
        <a href="/terms" className="underline">Terms</a> and <a href="/privacy" className="underline">Privacy Policy</a>.
      </p>
    </form>
  );
}
