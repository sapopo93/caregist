"use client";

import { useState } from "react";

export default function EmailCaptureStrip({
  source = "homepage",
  heading = "Get weekly CQC rating changes in your area \u2014 free.",
  subheading = "Weekly digest of rating upgrades and downgrades. No spam. Unsubscribe anytime.",
  onSuccess,
}: {
  source?: string;
  heading?: string;
  subheading?: string;
  onSuccess?: () => void;
}) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setStatus("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/v1/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), source }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Something went wrong");
      }
      setStatus("success");
      onSuccess?.();
    } catch (err: any) {
      setErrorMsg(err.message || "Something went wrong. Please try again.");
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div className="bg-moss/10 border border-moss/30 rounded-lg p-6 text-center">
        <p className="text-moss font-semibold">You&apos;re subscribed!</p>
        <p className="text-sm text-dusk mt-1">
          You&apos;ll receive weekly CQC rating changes in your inbox.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-cream border border-stone rounded-lg p-6 text-center">
      <p className="font-semibold text-bark mb-2">{heading}</p>
      <form onSubmit={handleSubmit} className="flex gap-2 max-w-md mx-auto">
        <input
          type="email"
          required
          placeholder="your@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="flex-1 px-4 py-2.5 rounded-lg border border-stone text-sm bg-white focus:outline-none focus:border-clay"
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="px-5 py-2.5 bg-clay text-white rounded-lg text-sm font-medium hover:bg-bark transition-colors disabled:opacity-50"
        >
          {status === "loading" ? "..." : "Subscribe \u2192"}
        </button>
      </form>
      {status === "error" && (
        <p className="text-alert text-xs mt-2">{errorMsg}</p>
      )}
      <p className="text-xs text-dusk mt-3">{subheading}</p>
    </div>
  );
}
