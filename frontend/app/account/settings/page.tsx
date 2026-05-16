"use client";

/**
 * Account Settings page.
 * Provides:
 *   - "Export my data" — DSAR (UK DPA Art 15)
 *   - "Delete my account" — soft-delete with confirmation modal (UK DPA Art 17)
 *
 * Coordinates with:
 *   - POST /api/v1/account/export  (Quill Phase B)
 *   - POST /api/v1/account/delete  (Quill Phase B)
 *
 * Privacy-policy language consistent with Vellum PR #10.
 */

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function useApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cg_api_key");
}

export default function AccountSettingsPage() {
  const apiKey = useApiKey();

  // Delete modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteReason, setDeleteReason] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState(false);

  // Export state
  const [exportLoading, setExportLoading] = useState(false);
  const [exportResult, setExportResult] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  async function handleExport() {
    if (!apiKey) {
      setExportError("Not signed in.");
      return;
    }
    setExportLoading(true);
    setExportError(null);
    setExportResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/account/export`, {
        method: "POST",
        headers: { "X-API-Key": apiKey },
      });
      const data = await res.json();
      if (!res.ok) {
        setExportError(data.detail ?? "Export failed.");
      } else {
        setExportResult(
          `Export queued. A download link will be emailed to you and expires on ${
            data.expires_at ? new Date(data.expires_at).toLocaleDateString("en-GB") : "7 days from now"
          }.`
        );
      }
    } catch {
      setExportError("Network error. Please try again.");
    } finally {
      setExportLoading(false);
    }
  }

  async function handleDelete(e: React.FormEvent) {
    e.preventDefault();
    if (!apiKey) {
      setDeleteError("Not signed in.");
      return;
    }
    setDeleteLoading(true);
    setDeleteError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/account/delete`, {
        method: "POST",
        headers: {
          "X-API-Key": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ password: deletePassword, reason: deleteReason || null }),
      });
      const data = await res.json();
      if (!res.ok) {
        setDeleteError(data.detail ?? "Deletion failed.");
      } else {
        setDeleteSuccess(true);
        localStorage.removeItem("cg_api_key");
        // Redirect to home after short delay
        setTimeout(() => { window.location.href = "/"; }, 3000);
      }
    } catch {
      setDeleteError("Network error. Please try again.");
    } finally {
      setDeleteLoading(false);
    }
  }

  if (deleteSuccess) {
    return (
      <main className="max-w-lg mx-auto py-16 px-4">
        <h1 className="text-2xl font-bold mb-4">Account deleted</h1>
        <p className="text-gray-600">
          Your account has been deleted. Any reviews you submitted will remain
          visible with your name shown as &ldquo;Former user&rdquo; in line with
          our{" "}
          <a href="/privacy" className="underline">retention policy</a>.
        </p>
        <p className="mt-2 text-sm text-gray-400">Redirecting to home&hellip;</p>
      </main>
    );
  }

  return (
    <main className="max-w-lg mx-auto py-16 px-4 space-y-12">
      <h1 className="text-3xl font-bold">Account settings</h1>

      {/* Data export (DSAR) */}
      <section>
        <h2 className="text-xl font-semibold mb-2">Export my data</h2>
        <p className="text-sm text-gray-600 mb-4">
          Under the UK Data Protection Act 2018 (Art&nbsp;15), you have the right
          to receive a copy of all personal data we hold about you. Your export
          will include your profile, reviews, claims, subscriptions and session
          metadata. IP addresses are hashed before export. A download link will
          be emailed to you and expires after 7&nbsp;days.
        </p>
        {exportResult && (
          <p role="status" className="text-green-700 text-sm mb-3">{exportResult}</p>
        )}
        {exportError && (
          <p role="alert" className="text-red-600 text-sm mb-3">{exportError}</p>
        )}
        <button
          onClick={handleExport}
          disabled={exportLoading}
          className="rounded bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {exportLoading ? "Requesting export\u2026" : "Export my data"}
        </button>
      </section>

      {/* Account deletion */}
      <section>
        <h2 className="text-xl font-semibold mb-2 text-red-700">Delete my account</h2>
        <p className="text-sm text-gray-600 mb-4">
          Deleting your account is permanent. Under the UK Data Protection Act
          2018 (Art&nbsp;17), your profile and personal data will be erased.
          Reviews you submitted will remain visible with your name shown as
          &ldquo;Former user&rdquo; — third-party readers rely on this content.
          This action cannot be undone.
        </p>
        <button
          onClick={() => setShowDeleteModal(true)}
          className="rounded bg-red-600 text-white px-4 py-2 text-sm font-medium hover:bg-red-700"
        >
          Delete my account
        </button>
      </section>

      {/* Confirmation modal */}
      {showDeleteModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        >
          <div className="bg-white rounded-xl shadow-xl p-8 max-w-md w-full mx-4">
            <h3 id="delete-modal-title" className="text-xl font-bold text-red-700 mb-4">
              Confirm account deletion
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              Enter your current password to confirm. This will immediately
              delete your account and revoke all access keys. Your reviews will
              remain with your name replaced by &ldquo;Former user&rdquo;.
            </p>
            <form onSubmit={handleDelete} className="space-y-4">
              <div>
                <label htmlFor="delete-password" className="block text-sm font-medium mb-1">
                  Current password
                </label>
                <input
                  id="delete-password"
                  type="password"
                  required
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </div>
              <div>
                <label htmlFor="delete-reason" className="block text-sm font-medium mb-1">
                  Reason (optional)
                </label>
                <textarea
                  id="delete-reason"
                  value={deleteReason}
                  onChange={(e) => setDeleteReason(e.target.value)}
                  rows={3}
                  maxLength={500}
                  className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                  placeholder="Tell us why you are leaving (optional)"
                />
              </div>
              {deleteError && (
                <p role="alert" className="text-red-600 text-sm">{deleteError}</p>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={deleteLoading || !deletePassword}
                  className="flex-1 rounded bg-red-600 text-white px-4 py-2 text-sm font-medium hover:bg-red-700 disabled:opacity-50"
                >
                  {deleteLoading ? "Deleting\u2026" : "Yes, delete my account"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowDeleteModal(false);
                    setDeletePassword("");
                    setDeleteReason("");
                    setDeleteError(null);
                  }}
                  className="flex-1 rounded border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
