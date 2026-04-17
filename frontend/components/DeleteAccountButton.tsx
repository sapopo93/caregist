"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function DeleteAccountButton() {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDelete = async () => {
    setLoading(true);
    setError("");
    const stored = localStorage.getItem("caregist_user");
    const user = stored ? JSON.parse(stored) : null;
    if (!user?.email) {
      setError("Could not determine your email. Please log in again.");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch("/api/v1/auth/delete-account", {
        method: "DELETE",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: user.email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || "Deletion failed.");
        return;
      }
      await fetch("/api/v1/auth/session", { method: "DELETE", credentials: "include" }).catch(() => {});
      localStorage.removeItem("caregist_user");
      localStorage.removeItem("caregist_tier");
      router.push("/");
    } catch {
      setError("Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  if (!confirming) {
    return (
      <button
        onClick={() => setConfirming(true)}
        className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 transition-colors"
      >
        Delete My Account
      </button>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-red-600 font-medium">Are you sure? This cannot be undone.</p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <input
        type="password"
        placeholder="Enter your password to confirm"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full px-4 py-2 rounded-lg border border-stone bg-cream focus:ring-2 focus:ring-red-400 focus:outline-none text-sm"
      />
      <div className="flex gap-3">
        <button
          onClick={handleDelete}
          disabled={loading || !password}
          className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 transition-colors disabled:opacity-50"
        >
          {loading ? "Deleting..." : "Permanently Delete"}
        </button>
        <button
          onClick={() => { setConfirming(false); setPassword(""); setError(""); }}
          className="px-4 py-2 border border-stone rounded-lg text-sm hover:bg-cream transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
