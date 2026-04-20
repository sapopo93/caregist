"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import DeleteAccountButton from "@/components/DeleteAccountButton";
import NewRegistrationFeedPanel from "@/components/NewRegistrationFeedPanel";
import { trackEvent } from "@/lib/analytics";
import { PLAN_LIMIT_SUMMARY, PLAN_NEXT_STEP, PLAN_PRIMARY_CTA } from "@/lib/caregist-config";

type CountDatum = {
  label: string;
  count: number;
};

type GrowthDatum = {
  label: string;
  recent_count: number;
  previous_count: number;
  growth_count: number;
  growth_rate: number;
};

type ProviderAnalytics = {
  provider_types: CountDatum[];
  service_types: CountDatum[];
  service_growth: GrowthDatum[];
};

const CHART_COLORS = ["#C1784F", "#4A5E45", "#D4943A", "#6B4C35", "#7E9B79", "#8C7E6A", "#2B2520", "#C44444"];

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [revealedApiKey, setRevealedApiKey] = useState("");
  const [revealPassword, setRevealPassword] = useState("");
  const [revealLoading, setRevealLoading] = useState(false);
  const [revealError, setRevealError] = useState("");
  const [tier, setTier] = useState("free");
  const [subscription, setSubscription] = useState<any>(null);
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [teamKeys, setTeamKeys] = useState<any[]>([]);
  const [providerAnalytics, setProviderAnalytics] = useState<ProviderAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");
  const [seatDraft, setSeatDraft] = useState(0);
  const [seatLoading, setSeatLoading] = useState(false);
  const [seatError, setSeatError] = useState("");
  const [loadError, setLoadError] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyEmail, setNewKeyEmail] = useState("");
  const [newKeyValue, setNewKeyValue] = useState("");
  const [keyLoading, setKeyLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleLogout = async () => {
    await fetch("/api/v1/auth/session", { method: "DELETE", credentials: "include" }).catch(() => {});
    localStorage.removeItem("caregist_user");
    localStorage.removeItem("caregist_tier");
    window.dispatchEvent(new Event("caregist_auth_change"));
    router.push("/");
  };

  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    const t = localStorage.getItem("caregist_tier") || "free";
    if (stored) setUser(JSON.parse(stored));
    setTier(t);

    fetch("/api/v1/billing/subscription", { credentials: "include" })
      .then((res) => res.json())
      .then((data) => {
        setSubscription(data);
        setSeatDraft(data?.entitlements?.extra_seats || 0);
      })
      .catch(() => setLoadError(true));
    fetch("/api/v1/auth/team-keys", { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setTeamKeys(Array.isArray(data?.keys) ? data.keys : []))
      .catch(() => { setTeamKeys([]); setLoadError(true); });
  }, []);

  useEffect(() => {
    if (tier !== "business" && tier !== "enterprise") return;
    fetch("/api/v1/webhooks", { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setWebhooks(Array.isArray(data?.webhooks) ? data.webhooks : []))
      .catch(() => { setWebhooks([]); setLoadError(true); });
  }, [tier]);

  useEffect(() => {
    if (!["starter", "pro", "business", "enterprise"].includes(tier)) {
      setProviderAnalytics(null);
      return;
    }

    setAnalyticsLoading(true);
    setAnalyticsError("");
    fetch("/api/v1/providers/analytics", { credentials: "include" })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Could not load provider analytics.");
        setProviderAnalytics({
          provider_types: Array.isArray(data.provider_types) ? data.provider_types : [],
          service_types: Array.isArray(data.service_types) ? data.service_types : [],
          service_growth: Array.isArray(data.service_growth) ? data.service_growth : [],
        });
      })
      .catch((err) => {
        setProviderAnalytics(null);
        setAnalyticsError(err instanceof Error ? err.message : "Could not load provider analytics.");
      })
      .finally(() => setAnalyticsLoading(false));
  }, [tier]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("session_id");
    const billingStatus = params.get("billing");
    if (sessionId) {
      void trackEvent("upgrade_conversion", "dashboard_checkout_return", { tier, session_id: sessionId });
    } else if (billingStatus === "updated") {
      void trackEvent("upgrade_conversion", "dashboard_subscription_update", { tier });
    }
  }, [tier]);

  const copyKey = () => {
    if (!revealedApiKey) return;
    navigator.clipboard.writeText(revealedApiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  async function handleRevealKey() {
    if (!user?.email || !revealPassword) return;
    setRevealLoading(true);
    setRevealError("");
    try {
      const res = await fetch("/api/v1/auth/reveal-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: user.email, password: revealPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        setRevealError(data.detail || "Could not reveal your key.");
        return;
      }
      setRevealedApiKey(data.api_key || "");
      setRevealPassword("");
    } catch {
      setRevealError("Could not reveal your key.");
    } finally {
      setRevealLoading(false);
    }
  }

  if (!user) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
        <p className="text-dusk mb-6">Please log in to view your dashboard.</p>
        <Link href="/login" className="px-6 py-3 bg-clay text-white rounded-lg font-medium">Log In</Link>
      </div>
    );
  }

  const tierInfo: Record<string, { limit: string; features: string; cta: string; next: string }> = {
    free: {
      limit: PLAN_LIMIT_SUMMARY.free,
      features: "Built for evaluation: browse providers, test the data, sample exports, and monitor one provider.",
      cta: PLAN_PRIMARY_CTA.free,
      next: PLAN_NEXT_STEP.free,
    },
    starter: {
      limit: PLAN_LIMIT_SUMMARY.starter,
      features: "First real workflow: new registration feed, recurring exports, saved views, weekly digest, and 15 provider watchlists.",
      cta: PLAN_PRIMARY_CTA.starter,
      next: PLAN_NEXT_STEP.starter,
    },
    pro: {
      limit: PLAN_LIMIT_SUMMARY.pro,
      features: "Small-team production use: broader feed coverage, 5,000-row exports, 100 monitors, 3 named access seats, and daily operational headroom.",
      cta: PLAN_PRIMARY_CTA.pro,
      next: PLAN_NEXT_STEP.pro,
    },
    business: {
      limit: PLAN_LIMIT_SUMMARY.business,
      features: "Operational integration: full fields, signed feed webhooks, 10,000-row exports, 500 monitors, and stronger admin support.",
      cta: PLAN_PRIMARY_CTA.business,
      next: PLAN_NEXT_STEP.business,
    },
  };

  const info = tierInfo[tier] || tierInfo.free;
  const entitlements = subscription?.entitlements;
  const seatSummary = entitlements
    ? `${entitlements.included_users} included user${entitlements.included_users === 1 ? "" : "s"}${entitlements.extra_seats ? ` + ${entitlements.extra_seats} extra seat${entitlements.extra_seats === 1 ? "" : "s"}` : ""}`
    : tier === "pro"
      ? "3 included users"
      : tier === "business"
        ? "10 included users"
        : "1 included user";
  const upgradeHref = tier === "business" ? "mailto:enterprise@caregist.co.uk?subject=CareGist+Enterprise" : "/pricing";
  const supportsSeatCheckout = tier === "pro" || tier === "business";
  const quickStartApiKey = revealedApiKey ? `${revealedApiKey.slice(0, 20)}...` : "cg_your_key";

  async function handleSeatUpdate() {
    if (!supportsSeatCheckout || !user) return;
    setSeatLoading(true);
    setSeatError("");
    void trackEvent("seat_addon_interaction", "dashboard_team_card", { tier, extra_seats: seatDraft });

    try {
      const res = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: user.email, tier, extra_seats: seatDraft }),
      });
      const data = await res.json();
      if (!res.ok) {
        setSeatError(data.detail || "Could not update seats.");
        return;
      }
      if (data.updated) {
        setSubscription((current: any) => current ? {
          ...current,
          entitlements: {
            ...current.entitlements,
            extra_seats: data.extra_seats,
            max_users: (current.entitlements?.included_users || 0) + data.extra_seats,
          },
        } : current);
        return;
      }
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch {
      setSeatError("Could not update seats.");
    } finally {
      setSeatLoading(false);
    }
  }

  async function handleCreateTeamKey() {
    if (!newKeyName.trim() || !newKeyEmail.trim()) return;
    setKeyLoading(true);
    setSeatError("");
    try {
      const res = await fetch("/api/v1/auth/team-keys", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKeyName.trim(), email: newKeyEmail.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setSeatError(data.detail || "Could not create named access key.");
        return;
      }
      setNewKeyValue(data.api_key);
      setTeamKeys((current) => [
        ...current,
        {
          id: Date.now(),
          name: data.name,
          email: data.email,
          masked_key: `${data.api_key.slice(0, 10)}…${data.api_key.slice(-4)}`,
          last_used_at: null,
        },
      ]);
      setNewKeyName("");
      setNewKeyEmail("");
    } catch {
      setSeatError("Could not create named access key.");
    } finally {
      setKeyLoading(false);
    }
  }

  async function handleRevokeTeamKey(keyId: number) {
    try {
      const res = await fetch(`/api/v1/auth/team-keys/${keyId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setSeatError(data.detail || "Could not revoke access key.");
        return;
      }
      setTeamKeys((current) => current.filter((key) => key.id !== keyId));
    } catch {
      setSeatError("Could not revoke access key.");
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      {loadError && (
        <div className="bg-amber-50 border border-amber-300 rounded-lg px-4 py-3 mb-6 text-sm text-amber-800">
          Some account data could not be loaded — please refresh the page.
        </div>
      )}
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
        Welcome back, {user.name}. This workspace is built to turn newly registered UK care providers into a recurring commercial workflow, backed by a trusted event ledger.
      </p>

      <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold">Your plan</h2>
          <span className="px-3 py-1 rounded-full bg-moss text-white text-sm font-medium capitalize">{tier}</span>
        </div>
        <p className="text-dusk text-sm mb-1">Rate limit: {info.limit}</p>
        <p className="text-dusk text-sm mb-1">Includes: {info.features}</p>
        <p className="text-dusk text-sm mb-4">Users: {seatSummary}</p>
        <div className="rounded-lg bg-parchment border border-stone p-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-dusk mb-1">Next step</p>
          <p className="text-sm text-bark mb-3">{info.next}</p>
          <Link
            href={upgradeHref}
            className="text-clay underline text-sm"
            onClick={() => void trackEvent("upgrade_click", "dashboard_plan_card", { tier, target: tier === "business" ? "enterprise" : undefined })}
          >
            {info.cta}
          </Link>
        </div>
      </div>

      <ProviderAnalyticsSection
        analytics={providerAnalytics}
        loading={analyticsLoading}
        error={analyticsError}
        tier={tier}
      />

      <NewRegistrationFeedPanel tier={tier} upgradeHref={upgradeHref} />

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Data explorer</h2>
          <p className="text-dusk text-sm mb-4">
            Search and profile the wider provider universe once the new registration feed has identified where you want to focus.
          </p>
          <div className="flex gap-4">
            <Link href="/search" className="text-sm text-clay underline">Open explorer</Link>
            <Link href="/pricing" className="text-sm text-clay underline">View plan limits</Link>
          </div>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Provider claiming</h2>
          <p className="text-dusk text-sm mb-4">
            Provider claiming remains available, but it is secondary to the recurring intelligence wedge.
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
          Use your key when you are ready to query the same event-led workflow programmatically.
        </p>
        <div className="flex items-center gap-3">
          <code className="flex-1 bg-parchment border border-stone rounded px-4 py-2 text-sm font-mono text-charcoal truncate">
            {revealedApiKey || "Password required to reveal your API key"}
          </code>
          <button
            onClick={copyKey}
            disabled={!revealedApiKey}
            className="px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
        <div className="mt-3 flex flex-col sm:flex-row gap-3">
          <input
            type="password"
            value={revealPassword}
            onChange={(e) => setRevealPassword(e.target.value)}
            placeholder="Confirm password to reveal"
            className="flex-1 px-3 py-2 rounded border border-stone bg-white text-sm"
          />
          <button
            onClick={() => void handleRevealKey()}
            disabled={revealLoading || !revealPassword}
            className="px-4 py-2 border border-stone rounded-lg text-sm text-bark hover:bg-parchment transition-colors disabled:opacity-50"
          >
            {revealLoading ? "Checking..." : "Reveal key"}
          </button>
        </div>
        {revealError && <p className="text-xs text-alert mt-2">{revealError}</p>}
        <p className="text-sm text-dusk mt-3">
          Pass this as <code className="bg-parchment px-1 rounded">X-API-Key</code> in API requests.
        </p>
        {tier === "free" && (
          <p className="text-xs text-dusk mt-3">
            Free is built for evaluation. Upgrade to Starter when you need recurring feed exports, saved views, weekly digests, or a workflow you will run more than occasionally.
          </p>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Team and attribution</h2>
          <p className="text-dusk text-sm mb-3">
            {tier === "pro" || tier === "business"
              ? `This plan includes named access seats so teams can avoid shared passwords and keep activity attributable. ${seatSummary}.`
              : "Free and Starter are single-seat tiers. Upgrade to Pro when multiple people need their own named access and clearer accountability."}
          </p>
          <p className="text-xs text-dusk mb-4">
            {tier === "pro" || tier === "business"
              ? "Additional named access seats are priced at £15 + VAT / seat / month and provisioned against your current plan entitlements."
              : "Pro includes 3 named access seats. Additional seats are £15 + VAT / seat / month."}
          </p>
          {supportsSeatCheckout && (
            <div className="rounded-lg bg-parchment border border-stone p-4 mb-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-dusk mb-2">Seat planning</p>
              <div className="flex items-center gap-3 mb-2">
                <label htmlFor="seat-count" className="text-sm text-bark">Extra seats</label>
                <input
                  id="seat-count"
                  type="number"
                  min={0}
                  max={50}
                  value={seatDraft}
                  onChange={(e) => setSeatDraft(Math.max(0, Math.min(50, Number(e.target.value) || 0)))}
                  className="w-24 px-3 py-2 rounded border border-stone bg-white text-sm"
                />
                <button
                  onClick={() => void handleSeatUpdate()}
                  disabled={seatLoading}
                  className="px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors disabled:opacity-50"
                >
                  {seatLoading ? "Updating..." : "Update seats"}
                </button>
              </div>
              <p className="text-xs text-dusk">
                Add named access seats without moving to a different plan immediately. This updates your current subscription quantity.
              </p>
              {seatError && <p className="text-xs text-alert mt-2">{seatError}</p>}
            </div>
          )}
          {(tier === "pro" || tier === "business") && (
            <div className="rounded-lg bg-parchment border border-stone p-4 mb-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-dusk mb-2">Named access keys</p>
              <p className="text-xs text-dusk mb-3">
                Issue separate API keys for each teammate or workflow owner. Each active key consumes one seat.
              </p>
              <div className="grid sm:grid-cols-[1fr_1fr_auto] gap-3 mb-3">
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="Name"
                  className="px-3 py-2 rounded border border-stone bg-white text-sm"
                />
                <input
                  type="email"
                  value={newKeyEmail}
                  onChange={(e) => setNewKeyEmail(e.target.value)}
                  placeholder="Email"
                  className="px-3 py-2 rounded border border-stone bg-white text-sm"
                />
                <button
                  onClick={() => void handleCreateTeamKey()}
                  disabled={keyLoading}
                  className="px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors disabled:opacity-50"
                >
                  {keyLoading ? "Creating..." : "Create key"}
                </button>
              </div>
              {newKeyValue && (
                <div className="mb-3 rounded border border-moss/30 bg-moss/10 p-3">
                  <p className="text-xs text-bark mb-1">Store this key securely. It is shown once.</p>
                  <code className="text-xs break-all">{newKeyValue}</code>
                </div>
              )}
              <div className="space-y-2">
                {teamKeys.map((key) => (
                  <div key={key.id} className="flex items-center justify-between gap-3 text-xs text-dusk border-b border-stone pb-2 last:border-b-0 last:pb-0">
                    <div>
                      <p className="font-medium text-bark">{key.name || "Unnamed key"} · {key.email || "No email"}</p>
                      <p>{key.masked_key} · Last used: {key.last_used_at ? new Date(key.last_used_at).toLocaleString("en-GB") : "Not used yet"}</p>
                    </div>
                    {typeof key.id === "number" && (
                      <button onClick={() => void handleRevokeTeamKey(key.id)} className="text-clay underline">
                        Revoke
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          <Link
            href={upgradeHref}
            className="text-clay underline text-sm"
            onClick={() => void trackEvent("upgrade_click", "dashboard_team_card", { tier })}
          >
            {tier === "business" ? "Contact sales" : tier === "pro" ? "Upgrade to Business" : "Upgrade to Pro"}
          </Link>
        </div>

        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Webhooks and integrations</h2>
          <p className="text-dusk text-sm mb-3">
            Business and Enterprise can register outbound webhooks for the new registration feed and provider rating changes. Starter and Pro keep the focus on dashboard, exports, digests, and direct API use.
          </p>
          <p className="text-xs text-dusk mb-4">
            Supported webhook events are <code className="bg-parchment px-1 rounded">feed.new_registration</code> and <code className="bg-parchment px-1 rounded">provider.rating_changed</code>.
          </p>
          <Link
            href={tier === "business" ? "/api" : "/pricing"}
            className="text-clay underline text-sm"
            onClick={() => void trackEvent("upgrade_click", "dashboard_webhook_card", { tier, target: "business" })}
          >
            {tier === "business" ? "Review webhook docs" : "Upgrade to Business"}
          </Link>
          {(tier === "business" || tier === "enterprise") && (
            <div className="mt-4 rounded-lg bg-parchment border border-stone p-4">
              <p className="text-[11px] uppercase tracking-[0.18em] text-dusk mb-2">Delivery status</p>
              {webhooks.length === 0 ? (
                <p className="text-xs text-dusk">No webhooks registered yet. Use the API docs to register your first endpoint.</p>
              ) : (
                <div className="space-y-3">
                  {webhooks.map((webhook) => (
                    <div key={webhook.id} className="text-xs text-dusk border-b border-stone pb-3 last:border-b-0 last:pb-0">
                      <p className="font-medium text-bark break-all">{webhook.url}</p>
                      <p>Failures: {webhook.delivery_failures} · Last delivery: {webhook.last_delivery_at ? new Date(webhook.last_delivery_at).toLocaleString("en-GB") : "No successful delivery yet"}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="bg-cream border border-stone rounded-lg p-6 mt-6">
        <h2 className="text-xl font-bold mb-3">Quick start</h2>
        <p className="text-dusk text-sm mb-4">
          Typical flow: filter newly registered providers, export the current patch, save the view, then automate recurring delivery through the API or signed webhooks when the workflow proves out.
        </p>
        <div className="bg-charcoal text-cream rounded-lg p-4 text-sm font-mono overflow-x-auto">
          <p className="text-dusk"># Query the new registration feed for London</p>
          <p>curl -H &quot;X-API-Key: {quickStartApiKey}&quot; \</p>
          <p>&nbsp; &quot;https://api.caregist.co.uk/api/v1/feed/new-registrations?region=London&quot;</p>
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

function ProviderAnalyticsSection({
  analytics,
  loading,
  error,
  tier,
}: {
  analytics: ProviderAnalytics | null;
  loading: boolean;
  error: string;
  tier: string;
}) {
  if (!["starter", "pro", "business", "enterprise"].includes(tier)) {
    return (
      <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold mb-2">Provider type analytics</h2>
        <p className="text-sm text-dusk">
          Upgrade to Starter or above to see provider mix, service-type distribution, and new-registration growth charts.
        </p>
      </div>
    );
  }

  return (
    <section className="mb-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-clay mb-1">Market analytics</p>
          <h2 className="text-2xl font-bold">Provider mix and growth</h2>
        </div>
        <p className="text-xs text-dusk max-w-md">
          Based on active provider records and the new-registration event ledger.
        </p>
      </div>
      {loading && <p className="text-sm text-dusk bg-cream border border-stone rounded-lg p-4">Loading analytics...</p>}
      {error && <p className="text-sm text-alert bg-alert/5 border border-alert/30 rounded-lg p-4">{error}</p>}
      {!loading && !error && (
        <>
          <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-6 mb-6">
            <ServiceTypeBarChart data={analytics?.service_types || []} />
            <ProviderTypePieChart data={analytics?.provider_types || []} />
          </div>
          <ServiceGrowthChart data={analytics?.service_growth || []} />
        </>
      )}
    </section>
  );
}

function ServiceTypeBarChart({ data }: { data: CountDatum[] }) {
  const rows = normaliseCountData(data);
  const max = Math.max(...rows.map((row) => row.count), 1);

  return (
    <section className="border border-stone bg-cream rounded-lg p-5">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="text-lg font-bold text-bark">Providers by service type</h3>
          <p className="text-xs text-dusk mt-1">Active providers grouped from CQC service fields.</p>
        </div>
        <span className="text-xs font-medium text-dusk">Top {rows.length || 0}</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-dusk">No service-type data available yet.</p>
      ) : (
        <div className="space-y-3">
          {rows.map((row, index) => (
            <div key={row.label}>
              <div className="flex items-center justify-between gap-3 text-xs mb-1">
                <span className="font-medium text-charcoal truncate">{row.label}</span>
                <span className="font-mono text-dusk">{row.count.toLocaleString()}</span>
              </div>
              <div className="h-3 rounded-full bg-parchment overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.max(4, (row.count / max) * 100)}%`,
                    backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ProviderTypePieChart({ data }: { data: CountDatum[] }) {
  const rows = normaliseCountData(data);
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  const background = total > 0 ? buildConicGradient(rows) : "var(--color-parchment)";

  return (
    <section className="border border-stone bg-cream rounded-lg p-5">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-bark">Provider category mix</h3>
        <p className="text-xs text-dusk mt-1">Active providers by primary provider type.</p>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-dusk">No provider category data available yet.</p>
      ) : (
        <div className="grid sm:grid-cols-[10rem_1fr] gap-5 items-center">
          <div
            className="aspect-square rounded-full border border-stone"
            style={{ background }}
            aria-label="Provider category distribution pie chart"
          />
          <div className="space-y-2">
            {rows.map((row, index) => {
              const pct = total ? Math.round((row.count / total) * 100) : 0;
              return (
                <div key={row.label} className="flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="h-3 w-3 rounded-sm shrink-0"
                      style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                    />
                    <span className="truncate text-charcoal">{row.label}</span>
                  </div>
                  <span className="font-mono text-dusk">{pct}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

function ServiceGrowthChart({ data }: { data: GrowthDatum[] }) {
  const rows = normaliseGrowthData(data);
  const maxGrowth = Math.max(...rows.map((row) => Math.max(row.growth_count, 0)), 1);
  const fastest = rows.find((row) => row.growth_count > 0) || rows[0];

  return (
    <section className="border border-stone bg-cream rounded-lg p-5">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-4">
        <div>
          <h3 className="text-lg font-bold text-bark">Fastest-growing service types</h3>
          <p className="text-xs text-dusk mt-1">Compares new-registration ledger activity in the last 90 days against the prior 90 days.</p>
        </div>
        {fastest && fastest.growth_count > 0 && (
          <div className="rounded-lg bg-parchment border border-stone px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.16em] text-dusk">Current leader</p>
            <p className="text-sm font-bold text-bark">{fastest.label}</p>
          </div>
        )}
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-dusk">No recent growth data available from the new-registration ledger.</p>
      ) : (
        <div className="space-y-3">
          {rows.map((row, index) => {
            const growth = Math.max(row.growth_count, 0);
            return (
              <div key={row.label} className="grid gap-2 md:grid-cols-[11rem_1fr_10rem] md:items-center">
                <div className="text-sm font-medium text-charcoal truncate">{row.label}</div>
                <div className="h-3 rounded-full bg-parchment overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.max(4, (growth / maxGrowth) * 100)}%`,
                      backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                    }}
                  />
                </div>
                <div className="text-xs text-dusk md:text-right">
                  <span className="font-mono text-bark">{formatSignedCount(row.growth_count)}</span>
                  {" "}vs prior 90d
                  <span className="block font-mono">{formatSignedPercent(row.growth_rate)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function normaliseCountData(data: CountDatum[]): CountDatum[] {
  return (Array.isArray(data) ? data : [])
    .map((row) => ({ label: String(row.label || "Unknown"), count: Number(row.count || 0) }))
    .filter((row) => row.count > 0);
}

function normaliseGrowthData(data: GrowthDatum[]): GrowthDatum[] {
  return (Array.isArray(data) ? data : [])
    .map((row) => ({
      label: String(row.label || "Unknown"),
      recent_count: Number(row.recent_count || 0),
      previous_count: Number(row.previous_count || 0),
      growth_count: Number(row.growth_count || 0),
      growth_rate: Number(row.growth_rate || 0),
    }))
    .filter((row) => row.recent_count > 0 || row.previous_count > 0);
}

function buildConicGradient(rows: CountDatum[]): string {
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  let cursor = 0;
  const stops = rows.map((row, index) => {
    const start = cursor;
    cursor += (row.count / total) * 100;
    const color = CHART_COLORS[index % CHART_COLORS.length];
    return `${color} ${start}% ${cursor}%`;
  });
  return `conic-gradient(${stops.join(", ")})`;
}

function formatSignedCount(value: number): string {
  if (value > 0) return `+${value.toLocaleString()}`;
  return value.toLocaleString();
}

function formatSignedPercent(value: number): string {
  if (value > 0) return `+${value.toLocaleString()}%`;
  return `${value.toLocaleString()}%`;
}
