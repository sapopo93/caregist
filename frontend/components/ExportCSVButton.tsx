"use client";

import { useEffect, useState } from "react";
import LoginPromptModal from "@/components/LoginPromptModal";

export default function ExportCSVButton({ exportUrl }: { exportUrl: string }) {
  const [tier, setTier] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showUpgrade, setShowUpgrade] = useState(false);

  useEffect(() => {
    setTier(localStorage.getItem("caregist_tier"));
    setApiKey(localStorage.getItem("caregist_api_key"));
  }, []);

  const isLoggedIn = !!apiKey;
  const isFree = tier === "free" || !tier;

  async function handleDownload() {
    if (!isLoggedIn) {
      setShowModal(true);
      return;
    }

    setDownloading(true);
    try {
      const res = await fetch(exportUrl, {
        headers: { "X-API-Key": apiKey! },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Export failed. Please try again.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "caregist_export.csv";
      a.click();
      URL.revokeObjectURL(url);

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
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="text-sm text-clay underline hover:text-bark disabled:opacity-50"
      >
        {downloading
          ? "Downloading..."
          : isLoggedIn && isFree
            ? "Export CSV (Basic)"
            : "Export CSV"}
      </button>

      {showUpgrade && isFree && (
        <span className="text-xs text-dusk ml-2">
          Showing up to 100 rows.{" "}
          <a href="/pricing" className="text-clay underline">
            Upgrade for full export
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
