"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { trackEvent } from "@/lib/analytics";
import { PLAN_PRIMARY_CTA } from "@/lib/caregist-config";

const TIER_RANK: Record<string, number> = {
  free: 0,
  "alerts-pro": 1,
  "data-starter": 2,
  "data-pro": 3,
  "data-business": 4,
  enterprise: 5,
  starter: 2,
  pro: 3,
  business: 4,
};

const BILLING_TIER: Record<string, string | null> = {
  free: "free",
  "alerts-pro": null,
  "data-starter": "starter",
  "data-pro": "pro",
  "data-business": "business",
  enterprise: null,
};

export default function PricingCTA({ tier, isFreeTier }: { tier: string; isFreeTier: boolean }) {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [currentTier, setCurrentTier] = useState("free");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    const t = localStorage.getItem("caregist_tier") || "free";
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch {}
    }
    setCurrentTier(t);
  }, []);

  const tierKey = tier.toLowerCase().replace(/\s+/g, "-");
  const billingTier = BILLING_TIER[tierKey] ?? null;
  const targetTier = tierKey === "enterprise" ? null : tierKey;
  const ctaLabel = PLAN_PRIMARY_CTA[tierKey] || "Contact sales";
  const isCurrentTier = currentTier === tierKey;
  const currentRank = TIER_RANK[currentTier] ?? 0;
  const targetRank = targetTier ? (TIER_RANK[targetTier] ?? 0) : 99;

  async function handleUpgrade(target: string) {
    if (!user) return;
    setLoading(true);
    setError("");
    void trackEvent("pricing_cta_click", "pricing_card", { tier: tierKey, target_tier: target, action: "upgrade" });
    void trackEvent("plan_selection", "pricing_card", { source_tier: tierKey, target_tier: target });

    try {
      const res = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
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

  if (!targetTier || (tierKey === "alerts-pro" && user)) {
    return (
      <Link
        href={`mailto:enterprise@caregist.co.uk?subject=CareGist+${tier.replace(/\s+/g, "+")}`}
        className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
        onClick={() => void trackEvent("enterprise_contact_click", "pricing_card", { tier: tierKey })}
      >
        {ctaLabel}
      </Link>
    );
  }

  if (isFreeTier && !user) {
    return (
      <Link
        href="/signup"
        className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
        onClick={() => {
          void trackEvent("pricing_cta_click", "pricing_card", { tier: tierKey, target_tier: "free", action: "signup_free" });
          void trackEvent("plan_selection", "pricing_card", { source_tier: tierKey, target_tier: "free" });
        }}
      >
        {ctaLabel}
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
          onClick={() => billingTier && void handleUpgrade(billingTier)}
          disabled={loading}
          className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white disabled:opacity-50"
        >
          {loading ? "Redirecting..." : ctaLabel}
        </button>
        {error && <p className="text-alert text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (user && currentRank < targetRank && billingTier) {
    return (
      <div>
        <button
          onClick={() => void handleUpgrade(billingTier)}
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
      href={isFreeTier ? "/signup" : `/signup?plan=${targetTier}`}
      className="inline-block text-center py-2.5 px-6 rounded-lg font-medium text-sm transition-colors border border-clay text-clay hover:bg-clay hover:text-white"
      onClick={() => {
        void trackEvent("pricing_cta_click", "pricing_card", { tier: tierKey, target_tier: targetTier, action: isFreeTier ? "signup_free" : "signup_paid" });
        void trackEvent("plan_selection", "pricing_card", { source_tier: tierKey, target_tier: targetTier });
      }}
    >
      {ctaLabel}
    </Link>
  );
}
