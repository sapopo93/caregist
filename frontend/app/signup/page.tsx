"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { trackEvent } from "@/lib/analytics";

const PLAN_COPY: Record<string, { title: string; body: string }> = {
  free: {
    title: "Start with Free",
    body: "Built for evaluation: test the dashboard, sample exports, and one provider watchlist before moving into a paid workflow.",
  },
  "alerts-pro": {
    title: "Start Alerts Pro",
    body: "Alerts Pro is for monitoring provider watchlists, rating movement, and weekly market alerts.",
  },
  "data-starter": {
    title: "Start Data Starter",
    body: "Data Starter is the first core new-provider intelligence plan for weekly feed exports and saved views.",
  },
  "data-pro": {
    title: "Start Data Pro",
    body: "Data Pro is for small teams using CareGist as a recurring new-provider sales workflow.",
  },
  "data-business": {
    title: "Start Data Business",
    body: "Data Business is for teams pushing provider intelligence into CRM, outbound, and internal systems.",
  },
};

const PROVIDER_TIER_COPY: Record<string, { title: string; body: string }> = {
  enhanced: {
    title: "Upgrade to Provider Pro Listing",
    body: "Create your account to claim your listing and unlock a Provider Pro Listing — description, photos, and virtual tour.",
  },
  sponsored: {
    title: "Upgrade to Sponsored Listing",
    body: "Create your account to claim your listing and unlock a Sponsored Listing — top placement, sponsored badge, and maximum visibility.",
  },
};

function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan") || "free";
  const providerTier = searchParams.get("provider_tier") || "";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Redirect logged-in users to pricing (for upgrades) or dashboard
  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    if (stored) {
      router.replace(plan !== "free" || providerTier ? `/pricing` : "/dashboard");
    }
  }, [plan, providerTier, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      void trackEvent("plan_selection", "signup_form", { plan, provider_tier: providerTier || undefined });

      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Registration failed.");
        return;
      }

      let next: string;
      if (providerTier) {
        next = `/login?provider_tier=${providerTier}`;
      } else if (plan !== "free") {
        next = `/login?upgrade=${plan}`;
      } else {
        next = "/login";
      }
      router.push(`/verify-email?email=${encodeURIComponent(email)}&next=${encodeURIComponent(next)}`);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold text-center mb-2">
        {providerTier
          ? (PROVIDER_TIER_COPY[providerTier]?.title ?? "Create your provider account")
          : (PLAN_COPY[plan]?.title ?? "Create your account")}
      </h1>
      <p className="text-dusk text-center mb-8">
        {providerTier
          ? (PROVIDER_TIER_COPY[providerTier]?.body ?? "Create your CareGist account.")
          : (PLAN_COPY[plan]?.body ?? "Create your CareGist account.")}
      </p>
      <p className="text-xs text-dusk text-center mb-6">
        We&apos;ll ask you to verify your email before you log in or start billing.
      </p>

      {error && (
        <div className="bg-cream border border-alert rounded-lg p-3 mb-4 text-sm text-alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-bark mb-1">Name</label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-bark mb-1">Email</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-bark mb-1">Password</label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-clay focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
        >
          {loading
            ? "Creating account..."
            : providerTier
            ? "Create account and claim listing"
            : plan === "free"
            ? "Create evaluation account"
            : `Continue to ${plan.charAt(0).toUpperCase()}${plan.slice(1)}`}
        </button>
      </form>

      <p className="text-center text-sm text-dusk mt-6">
        Already have an account? <Link href="/login" className="text-clay underline">Log in</Link>
      </p>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="max-w-md mx-auto px-6 py-16 text-center">Loading...</div>}>
      <SignupForm />
    </Suspense>
  );
}
