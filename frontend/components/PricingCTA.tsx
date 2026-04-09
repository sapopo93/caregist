"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { trackEvent } from "@/lib/analytics";
import { PLAN_PRIMARY_CTA } from "@/lib/caregist-config";

const NEXT_TIER: Record<string, string | null> = {
  free: "starter",
  starter: "pro",
  pro: "business",
  business: "enterprise",
  enterprise: null,
};

const TIER_RANK: Record<string, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  business: 3,
  enterprise: 4,
};

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
  const targetTier = NEXT_TIER[tierKey];
  const ctaLabel = PLAN_PRIMARY_CTA[tierKey] || "Contact sales";
  const isCurrentTier = currentTier === tierKey;
  const currentRank = TIER_RANK[currentTier] ?? 0;
  const targetRank = targetTier ? (TIER_RANK[targetTier] ?? 0) : 99;

  async function handleUpgrade(target: string) {
    if (!user || !apiKey) return;
    setLoading(true);
    setError("");
    void trackEvent("pricing_cta_click", "pricing_card", { tier: tierKey, target_tier: target, action: "upgrade" });
    void trackEvent("plan_selection", "pricing_card", { source_tier: tierKey, target_tier: target });

    try {
      const res = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ email: user.email, tier: target }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Checkout failed.");
        return;
      }
      if (data.updated) {
        localStorage.setItem("caregist_tier", data.tier);
        window.dispatchEvent(new Event("caregist_auth_change"));
        router.push("/dashboard?billing=updated");
        router.refresh();
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

  if (!targetTier) {
    return (
      <Link
        href="mailto:enterprise@caregist.co.uk?subject=CareGist+Enterprise"
        className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
        onClick={() => void trackEvent("enterprise_contact_click", "pricing_card", { tier: tierKey })}
      >
        Contact sales
      </Link>
    );
  }

  if (user && isCurrentTier) {
    return (
      <div className="flex flex-col items-start gap-2">
        <span className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm bg-moss/15 text-moss border border-moss/30">
          Current Plan
        </span>
        <button
          onClick={() => void handleUpgrade(targetTier)}
          disabled={loading}
          className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white disabled:opacity-50"
        >
          {loading ? "Redirecting..." : ctaLabel}
        </button>
        {error && <p className="text-alert text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (user && currentRank < targetRank) {
    return (
      <div>
        <button
          onClick={() => void handleUpgrade(targetTier)}
          disabled={loading}
          className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white disabled:opacity-50"
        >
          {loading ? "Redirecting..." : ctaLabel}
        </button>
        {error && <p className="text-alert text-xs mt-2">{error}</p>}
      </div>
    );
  }

  if (user && currentRank >= targetRank) {
    return (
      <Link
        href="/dashboard"
        className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-stone text-dusk hover:bg-parchment"
      >
        Review entitlements
      </Link>
    );
  }

  return (
    <Link
      href={`/signup?plan=${targetTier}`}
      className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
      onClick={() => {
        void trackEvent("pricing_cta_click", "pricing_card", { tier: tierKey, target_tier: targetTier, action: isFreeTier ? "signup_upgrade_path" : "signup_paid" });
        void trackEvent("plan_selection", "pricing_card", { source_tier: tierKey, target_tier: targetTier });
      }}
    >
      {ctaLabel}
    </Link>
  );
}
