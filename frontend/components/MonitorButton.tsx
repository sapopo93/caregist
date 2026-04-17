"use client";

import { useEffect, useState } from "react";
import LoginPromptModal from "@/components/LoginPromptModal";
import { trackEvent } from "@/lib/analytics";

export default function MonitorButton({ slug }: { slug: string }) {
  const [monitoring, setMonitoring] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const loggedIn = !!localStorage.getItem("caregist_user");
    if (!loggedIn) {
      setChecked(true);
      return;
    }
    fetch(`/api/v1/providers/${encodeURIComponent(slug)}/monitor-status`, {
      credentials: "include",
    })
      .then((r) => r.json())
      .then((data) => setMonitoring(!!data.monitoring))
      .catch(() => {})
      .finally(() => setChecked(true));
  }, [slug]);

  async function handleToggle() {
    const loggedIn = !!localStorage.getItem("caregist_user");
    if (!loggedIn) {
      setShowLogin(true);
      return;
    }

    setLoading(true);
    try {
      if (monitoring) {
        await fetch(`/api/v1/providers/${encodeURIComponent(slug)}/monitor`, {
          method: "DELETE",
          credentials: "include",
        });
        setMonitoring(false);
      } else {
        const res = await fetch(`/api/v1/providers/${encodeURIComponent(slug)}/monitor`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        if (res.status === 403) {
          const data = await res.json().catch(() => ({}));
          void trackEvent("upgrade_click", "watchlist_limit_prompt", { slug, target_tier: "starter" });
          alert(data.detail || "Monitor limit reached. Upgrade to Starter for more watchlists.");
          return;
        }
        if (res.ok) {
          setMonitoring(true);
          void trackEvent("watchlist_created", "provider_monitor_button", { slug });
        }
      }
    } catch {
      setError("Could not update monitor. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (!checked) return null;

  return (
    <>
      <button
        onClick={() => { setError(""); void handleToggle(); }}
        disabled={loading}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          monitoring
            ? "bg-moss/15 text-moss border border-moss/30"
            : "bg-clay text-white hover:bg-bark"
        } disabled:opacity-50`}
      >
        {loading ? "..." : monitoring ? "Monitoring \u2713" : "Monitor"}
      </button>
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}

      {showLogin && (
        <LoginPromptModal
          action="monitor this provider"
          onClose={() => setShowLogin(false)}
        />
      )}
    </>
  );
}
