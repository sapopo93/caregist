"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import DeleteAccountButton from "@/components/DeleteAccountButton";
import { trackEvent } from "@/lib/analytics";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [apiKey, setApiKey] = useState("");
  const [tier, setTier] = useState("free");
  const [copied, setCopied] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem("caregist_api_key");
    localStorage.removeItem("caregist_user");
    localStorage.removeItem("caregist_tier");
    window.dispatchEvent(new Event("caregist_auth_change"));
    router.push("/");
  };

  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    const key = localStorage.getItem("caregist_api_key") || "";
    const t = localStorage.getItem("caregist_tier") || "free";
    if (stored) setUser(JSON.parse(stored));
    setApiKey(key);
    setTier(t);
  }, []);

  const copyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!user) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
        <p className="text-dusk mb-6">Please log in to view your dashboard.</p>
        <Link href="/login" className="px-6 py-3 bg-clay text-white rounded-lg font-medium">Log In</Link>
      </div>
    );
  }

  const tierInfo: Record<string, { limit: string; features: string }> = {
    free: { limit: "5 req/min · 100/day", features: "Evaluate search, sample exports, and one provider monitor" },
    starter: { limit: "30 req/min · 500/day", features: "Nearby search, 500-row export, compare, and 15 monitors" },
    pro: { limit: "60 req/min · 2,000/day", features: "5,000-row export, 100 monitors, and heavier recurring analysis" },
    business: { limit: "200 req/min · 10,000/day", features: "Full field access, 10,000-row export, webhooks, and high-volume integration workflows" },
  };

  const info = tierInfo[tier] || tierInfo.free;

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <button
          onClick={handleLogout}
          className="px-4 py-2 text-sm text-dusk border border-stone rounded-lg hover:bg-cream transition-colors"
        >
          Log Out
        </button>
      </div>
      <p className="text-dusk mb-8">
        Welcome back, {user.name}. This workspace is built to turn daily-refreshed regulatory data into monitoring, export, and integration workflows.
      </p>

      <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold">Your plan</h2>
          <span className="px-3 py-1 rounded-full bg-moss text-white text-sm font-medium capitalize">{tier}</span>
        </div>
        <p className="text-dusk text-sm mb-1">Rate limit: {info.limit}</p>
        <p className="text-dusk text-sm mb-4">Includes: {info.features}</p>
        {tier === "free" && (
          <Link
            href="/pricing"
            className="text-clay underline text-sm"
            onClick={() => void trackEvent("pricing_cta_click", "dashboard_plan_card", { tier: "free", action: "upgrade" })}
          >
            Upgrade your plan
          </Link>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Data explorer</h2>
          <p className="text-dusk text-sm mb-4">
            Search, filter, compare, and export cleaned provider data before you wire up any downstream integration.
          </p>
          <div className="flex gap-4">
            <Link href="/search" className="text-sm text-clay underline">Open explorer</Link>
            <Link href="/pricing" className="text-sm text-clay underline">View plan limits</Link>
          </div>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Provider claiming</h2>
          <p className="text-dusk text-sm mb-4">
            Provider claiming remains available, but it is a secondary workflow to the data and monitoring layer.
          </p>
          <div className="flex gap-4">
            <Link href="/find-care" className="text-sm text-clay underline">Find a provider to claim</Link>
            <Link href="/search" className="text-sm text-clay underline">Browse providers</Link>
          </div>
        </div>
      </div>

      <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold mb-3">API access</h2>
        <p className="text-dusk text-sm mb-4">
          Use your key when you are ready to embed CareGist data into product or operational workflows.
        </p>
        <div className="flex items-center gap-3">
          <code className="flex-1 bg-parchment border border-stone rounded px-4 py-2 text-sm font-mono text-charcoal truncate">
            {apiKey}
          </code>
          <button
            onClick={copyKey}
            className="px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
        <p className="text-sm text-dusk mt-3">
          Pass this as <code className="bg-parchment px-1 rounded">X-API-Key</code> in API requests.
        </p>
      </div>

      <div className="bg-cream border border-stone rounded-lg p-6">
        <h2 className="text-xl font-bold mb-3">Quick start</h2>
        <p className="text-dusk text-sm mb-4">
          Typical flow: search in the dashboard, export a shortlist, then automate recurring checks through the API when the workflow proves out.
        </p>
        <div className="bg-charcoal text-cream rounded-lg p-4 text-sm font-mono overflow-x-auto">
          <p className="text-dusk"># Search for monitored providers in London</p>
          <p>curl -H &quot;X-API-Key: {apiKey.slice(0, 20)}...&quot; \</p>
          <p>&nbsp; &quot;https://api.caregist.co.uk/api/v1/providers/search?region=London&amp;rating=Good&quot;</p>
        </div>
        <div className="mt-4 flex gap-4 text-sm">
          <Link href="/api" className="text-clay underline">API documentation</Link>
          <Link href="/pricing" className="text-clay underline">Pricing and entitlements</Link>
        </div>
      </div>

      <div className="mt-8 border border-red-200 rounded-lg p-6">
        <h2 className="text-xl font-bold text-red-600 mb-2">Danger zone</h2>
        <p className="text-dusk text-sm mb-4">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>
        <DeleteAccountButton />
      </div>
    </div>
  );
}
