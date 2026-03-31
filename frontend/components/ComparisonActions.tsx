"use client";

import { useState } from "react";
import LoginPromptModal from "@/components/LoginPromptModal";

export default function ComparisonActions({ slugs }: { slugs: string[] }) {
  const [showLogin, setShowLogin] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [shareToken, setShareToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    const apiKey = localStorage.getItem("caregist_api_key");
    if (!apiKey) {
      setShowLogin(true);
      return;
    }

    setSaving(true);
    setError("");
    try {
      const res = await fetch("/api/v1/comparisons", {
        method: "POST",
        headers: { "X-API-Key": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({ slug_list: slugs }),
      });
      if (res.status === 403) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Limit reached. Upgrade for more.");
        return;
      }
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        setSaved(true);
        if (data.data?.share_token) setShareToken(data.data.share_token);
      }
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleShare() {
    const url = shareToken
      ? `${window.location.origin}/compare?token=${shareToken}`
      : `${window.location.origin}/compare?providers=${slugs.join(",")}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Fallback for browsers that block clipboard API
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <button
        onClick={handleSave}
        disabled={saving || saved}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          saved
            ? "bg-moss/15 text-moss border border-moss/30"
            : "bg-clay text-white hover:bg-bark"
        } disabled:opacity-50`}
      >
        {saved ? "Saved \u2713" : saving ? "Saving..." : "Save comparison"}
      </button>

      <button
        onClick={handleShare}
        className="px-4 py-2 rounded-lg text-sm font-medium border border-clay text-clay hover:bg-clay hover:text-white transition-colors"
      >
        {copied ? "Link copied!" : "Copy share link"}
      </button>

      {error && (
        <span className="text-xs text-alert">
          {error}{" "}
          <a href="/pricing" className="underline">Upgrade</a>
        </span>
      )}

      {showLogin && (
        <LoginPromptModal
          action="save comparisons"
          onClose={() => setShowLogin(false)}
        />
      )}
    </div>
  );
}
