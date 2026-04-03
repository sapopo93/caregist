"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function PricingCTA({ tier, isFreeTier }: { tier: string; isFreeTier: boolean }) {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [apiKey, setApiKey] = useState("");
  const [currentTier, setCurrentTier] = useState("free");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    const key = localStorage.getItem("caregist_api_key") || "";
    const t = localStorage.getItem("caregist_tier") || "free";
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch {}
    }
    setApiKey(key);
    setCurrentTier(t);
  }, []);

  const tierKey = tier.toLowerCase().replace(/\s+/g, "-");
  const isCurrentTier = currentTier === tierKey;

  async function handleUpgrade() {
    if (!user || !apiKey) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ email: user.email, tier: tierKey }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Checkout failed.");
        return;
      }
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  // Current tier — show badge
  if (user && isCurrentTier) {
    return (
      <span className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm bg-moss/15 text-moss border border-moss/30">
        Current Plan
      </span>
    );
  }

  // Logged in, different tier — upgrade button
  if (user && !isFreeTier) {
    return (
      <div>
        <button
          onClick={handleUpgrade}
          disabled={loading}
          className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white disabled:opacity-50"
        >
          {loading ? "Redirecting..." : "Upgrade"}
        </button>
        {error && <p className="text-alert text-xs mt-2">{error}</p>}
      </div>
    );
  }

  // Not logged in — link to signup
  return (
    <Link
      href={isFreeTier ? "/signup" : `/signup?plan=${tierKey}`}
      className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
    >
      {isFreeTier ? "Get Started Free" : "Get Started"}
    </Link>
  );
}
