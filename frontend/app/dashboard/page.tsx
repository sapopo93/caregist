"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import DeleteAccountButton from "@/components/DeleteAccountButton";

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
    free: { limit: "100 req/min", features: "Basic search + provider details" },
    starter: { limit: "1,000 req/min", features: "Full search + CSV export + nearby" },
    pro: { limit: "5,000 req/min", features: "Everything + webhooks + bulk export" },
  };

  const info = tierInfo[tier] || tierInfo.free;

  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <button
          onClick={handleLogout}
          className="px-4 py-2 text-sm text-dusk border border-stone rounded-lg hover:bg-cream transition-colors"
        >
          Log Out
        </button>
      </div>
      <p className="text-dusk mb-8">Welcome back, {user.name}.</p>

      {/* API Key */}
      <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold mb-3">Your API Key</h2>
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
          Pass this as <code className="bg-parchment px-1 rounded">X-API-Key</code> header in all API requests.
        </p>
      </div>

      {/* Plan */}
      <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold">Your Plan</h2>
          <span className="px-3 py-1 rounded-full bg-moss text-white text-sm font-medium capitalize">{tier}</span>
        </div>
        <p className="text-dusk text-sm mb-1">Rate limit: {info.limit}</p>
        <p className="text-dusk text-sm mb-4">Includes: {info.features}</p>
        {tier === "free" && (
          <Link href="/pricing" className="text-clay underline text-sm">Upgrade your plan</Link>
        )}
      </div>

      {/* Quick Start */}
      <div className="bg-cream border border-stone rounded-lg p-6">
        <h2 className="text-xl font-bold mb-3">Quick Start</h2>
        <div className="bg-charcoal text-cream rounded-lg p-4 text-sm font-mono overflow-x-auto">
          <p className="text-dusk"># Search for care homes in London</p>
          <p>curl -H &quot;X-API-Key: {apiKey.slice(0, 20)}...&quot; \</p>
          <p>&nbsp; &quot;https://api.caregist.co.uk/api/v1/providers/search?q=care+homes+london&quot;</p>
        </div>
        <div className="mt-4 flex gap-4 text-sm">
          <a href="/api/v1/docs" className="text-clay underline">API Documentation</a>
          <Link href="/search" className="text-clay underline">Browse Directory</Link>
        </div>
      </div>

      {/* Delete Account */}
      <div className="mt-8 border border-red-200 rounded-lg p-6">
        <h2 className="text-xl font-bold text-red-600 mb-2">Danger Zone</h2>
        <p className="text-dusk text-sm mb-4">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>
        <DeleteAccountButton />
      </div>
    </div>
  );
}
