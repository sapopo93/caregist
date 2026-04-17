"use client";

import { useEffect, useState } from "react";
import LoginPromptModal from "@/components/LoginPromptModal";
import { trackEvent } from "@/lib/analytics";

export default function ExportCSVButton({ exportUrl }: { exportUrl: string }) {
  const [tier, setTier] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [format, setFormat] = useState<"csv" | "xlsx">("csv");

  useEffect(() => {
    setTier(localStorage.getItem("caregist_tier"));
    setIsLoggedIn(!!localStorage.getItem("caregist_user"));
  }, []);
  const isFree = tier === "free" || !tier;

  async function handleDownload() {
    if (!isLoggedIn) {
      setShowModal(true);
      return;
    }

    setDownloading(true);
    try {
      const base = exportUrl.replace(/\/export\.(csv|xlsx)$/, "");
      const url = `${base}/export.${format}`;
      const res = await fetch(url, { credentials: "include" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Export failed. Please try again.");
        return;
      }
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = `caregist_export.${format}`;
      a.click();
      URL.revokeObjectURL(objectUrl);
      void trackEvent("export_cta_click", "export_button", { tier: tier || "free", format });

      if (isFree) {
        setShowUpgrade(true);
      }
    } catch {
      alert("Export failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <>
      <div className="flex items-center gap-2">
        {!isFree && (
          <div className="inline-flex rounded border border-stone overflow-hidden text-xs">
            <button
              onClick={() => setFormat("csv")}
              className={`px-2 py-1 ${format === "csv" ? "bg-bark text-cream" : "bg-cream text-dusk hover:bg-parchment"}`}
            >
              CSV
            </button>
            <button
              onClick={() => setFormat("xlsx")}
              className={`px-2 py-1 ${format === "xlsx" ? "bg-bark text-cream" : "bg-cream text-dusk hover:bg-parchment"}`}
            >
              Excel
            </button>
          </div>
        )}
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="text-sm text-clay underline hover:text-bark disabled:opacity-50"
        >
          {downloading
            ? "Downloading..."
            : isLoggedIn && isFree
              ? "Export CSV (Basic)"
              : `Export ${format.toUpperCase()}`}
        </button>
      </div>

      {showUpgrade && isFree && (
        <span className="text-xs text-dusk ml-2">
          Showing up to 25 rows. Starter unlocks workflow-sized exports, nearby search, and recurring use.{" "}
          <a
            href="/pricing"
            className="text-clay underline"
            onClick={() => void trackEvent("upgrade_click", "export_limit_prompt", { tier: "free", target_tier: "starter" })}
          >
            Upgrade to Starter
          </a>
        </span>
      )}

      {showModal && (
        <LoginPromptModal
          action="download this list"
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}
